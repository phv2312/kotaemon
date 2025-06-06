import glob
import logging
import os
from pathlib import Path
from typing import Generator

from ktem.db.models import engine
from ktem.embeddings.manager import embedding_models_manager as embeddings
from ktem.index.file.graph.pipelines import GraphRAGIndexingPipeline, GraphRAGRetrieverPipeline
from ktem.llms.manager import llms
from ktem.index.file.graph.visualize import create_knowledge_graph, visualize_graph
from sqlalchemy.orm import Session
from theflow.settings import settings
from kotaemon.base import Document, Param, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import ChatLLM

from .adapters import FastGraphRAGEmbeddingAdapter, FastGraphRAGLLMAdapter

try:
    from fast_graphrag import BaseStateManagerService, GraphRAG, QueryParam
    from fast_graphrag._storage._base import BaseGraphStorage, BaseIndexedKeyValueStorage, BaseVectorStorage
    from fast_graphrag._policies._base import BaseEdgeUpsertPolicy, BaseNodeUpsertPolicy
    from fast_graphrag._types import GTChunk, GTEdge, GTEmbedding, GTHash, GTId, GTNode, TQueryResponse, TContext
except ImportError:
    print(
        (
            "Fast-GraphRAG dependencies not installed. "
            "Try `pip install fast-graphrag` to install. "
            "Fast-GraphRAG retriever pipeline will not work properly."
        )
    )

logging.getLogger("fast-graphrag").setLevel(logging.INFO)
filestorage_path = Path(settings.KH_FILESTORAGE_PATH) / "nano_graphrag"
filestorage_path.mkdir(parents=True, exist_ok=True)
INDEX_BATCHSIZE = 4


def prepare_graph_index_path(graph_id: str):
    root_path = Path(filestorage_path) / graph_id
    input_path = root_path / "input"
    input_path.mkdir(parents=True, exist_ok=True)

    return root_path, input_path


def build_graphrag(
    input_path: str,
    llm: ChatLLM,
    embedding: BaseEmbeddings,
):
    graphrag = GraphRAG(
        working_dir=input_path,
        domain="Analyze this content and identify the atomic ideas. Focus on the interlink between them and how thm combine together to create a big picture.",
        example_queries="",
        entity_types=["Ideas", "Concepts", "Facts", "People", "Things", "Contributions"],
        config=GraphRAG.Config(
            llm_service = FastGraphRAGLLMAdapter(llm),
            embedding_service = FastGraphRAGEmbeddingAdapter(embedding),
        )
    )
    return graphrag


class FastGraphRAGIndexingPipeline(GraphRAGIndexingPipeline):
    llm: ChatLLM = Param(help="The LLM model")
    embedding: BaseEmbeddings = Param(help="The embedding model")

    def call_graphrag_index(self, graph_id: str, docs: list[Document]):
        _, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)

        self.llm = llms.get_default()
        self.embedding = embeddings.get_default()
        print(
            f"Indexing GraphRAG with LLM {self.llm} "
            f"and Embedding {self.embedding}..."
        )

        all_docs = [
            doc.text
            for doc in docs
            if doc.metadata.get("type", "text") == "text" and len(doc.text.strip()) > 0
        ]

        yield Document(
            channel="debug",
            text="[GraphRAG] Creating index... This can take a long time.",
        )

        # Remove all .json files in the input_path directory (previous cache)
        json_files = glob.glob(f"{input_path}/*.json")
        for json_file in json_files:
            os.remove(json_file)

        # Create GraphRAG instance
        graphrag = build_graphrag(
            input_path=input_path,
            llm=self.llm,
            embedding=self.embedding,
        )

        # output must be contain: Loaded graph from
        total_docs = len(all_docs)
        process_doc_count = 0
        yield Document(
            channel="debug",
            text=f"[GraphRAG] Indexed {process_doc_count} / {total_docs} documents.",
        )
        for doc_id in range(0, len(all_docs), INDEX_BATCHSIZE):
            cur_docs = all_docs[doc_id : doc_id + INDEX_BATCHSIZE]
            graphrag.insert(cur_docs)
            process_doc_count += len(cur_docs)
            yield Document(
                channel="debug",
                text=(
                    f"[GraphRAG] Indexed {process_doc_count} "
                    f"/ {total_docs} documents."
                ),
            )

        yield Document(
            channel="debug",
            text="[GraphRAG] Indexing finished.",
        )

    def stream(
        self, file_paths: str | Path | list[str | Path], reindex: bool = False, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        file_ids, errors, all_docs = yield from super().stream(
            file_paths, reindex=reindex, **kwargs
        )

        return file_ids, errors, all_docs


class FastGraphRAGRetrieverPipeline(GraphRAGRetrieverPipeline):
    """GraphRAG specific retriever pipeline"""

    Index = Param(help="The SQLAlchemy Index table")
    file_ids: list[str] = []
    llm: ChatLLM = Param(help="The LLM model")
    embedding: BaseEmbeddings = Param(help="The embedding model")

    @classmethod
    def get_user_settings(cls) -> dict:
        return {}
    
    def _build_graph_search(self):
        assert (
            len(self.file_ids)
            <= 1
            # len(self.file_ids) <= 1
        ), "GraphRAG retriever only supports one file_id at a time"
        file_id = self.file_ids[0]

        # retrieve the graph_id from the index
        with Session(engine) as session:
            graph_id = (
                session.query(self.Index.target_id)
                .filter(self.Index.source_id == file_id)
                .filter(self.Index.relation_type == "graph")
                .first()
            )
            graph_id = graph_id[0] if graph_id else None
            assert graph_id, f"GraphRAG index not found for file_id: {file_id}"

        _, input_path = prepare_graph_index_path(graph_id)

        self.llm = llms.get_default()
        self.embedding = embeddings.get_default()
        graphrag = build_graphrag(
            input_path=input_path,
            llm=self.llm,
            embedding=self.embedding,
        )
        query_params = QueryParam(only_context=True)

        return graphrag, query_params

    def format_context_records(
        self, context, # entities, relationships, sources
    ) -> list[RetrievedDocument]:
        # docs = []
        # context: str = ""

        # # entities current parsing error
        # header = "<b>Entities</b>\n"
        # context = entities[["entity", "description"]].to_markdown(index=False)
        # docs.append(self._to_document(header, context))

        # header = "\n<b>Relationships</b>\n"
        # context = relationships[["source", "target", "description"]].to_markdown(
        #     index=False
        # )
        # docs.append(self._to_document(header, context))

        # header = "\n<b>Sources</b>\n"
        # context = ""
        # for _, row in sources.iterrows():
        #     title, content = row["id"], row["content"]
        #     context += f"\n\n<h5>Source <b>#{title}</b></h5>\n"
        #     context += content
        # docs.append(self._to_document(header, context))
        docs = [
            self._to_document("<b>Context</b>\n", context.truncate(output_context_str=True)),
        ]

        return docs

    def plot_graph(self, relationships):
        G = create_knowledge_graph(relationships)
        plot = visualize_graph(G)
        return plot

    def run(self, text: str) -> list[RetrievedDocument]:
        if not self.file_ids:
            return []

        graphrag, query_params = self._build_graph_search()
        query_response: TQueryResponse = graphrag.query(text, query_params).to_dict()
        context: TContext = query_response.context
        entities, relationships, sources = context.entities, context.relationships, context.chunks

        documents = self.format_context_records(context) # entities, relationships, sources)
        plot = "" # self.plot_graph(relationships)

        return documents + [
            RetrievedDocument(
                text="",    
                metadata={
                    "file_name": "GraphRAG",
                    "type": "plot",
                    "data": plot,
                },
            ),
        ]