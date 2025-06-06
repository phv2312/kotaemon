import asyncio
import glob
import logging
import os
import re
from pathlib import Path
from typing import Generator, Optional

import pandas as pd
from ktem.db.models import engine
from ktem.embeddings.manager import embedding_models_manager as embeddings
from ktem.index.file.graph.pipelines import GraphRAGIndexingPipeline
from ktem.index.file.graph.visualize import create_knowledge_graph, visualize_graph
from ktem.index.file.pipelines import DocumentRetrievalPipeline
from ktem.llms.manager import llms
from sqlalchemy.orm import Session
from theflow.settings import settings

from kotaemon.base import Document, Param, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import ChatLLM
from kotaemon.storages import BaseVectorStore

from .adapters import wrap_embedding_func, wrap_llm_func, wrap_vector_store_cls

try:
    from nano_graphrag import GraphRAG, QueryParam
    from nano_graphrag._op import (
        _find_most_related_community_from_entities,
        _find_most_related_edges_from_entities,
        _find_most_related_text_unit_from_entities,
    )
except ImportError:
    print(
        (
            "Nano-GraphRAG dependencies not installed. "
            "Try `pip install nano-graphrag` to install. "
            "Nano-GraphRAG retriever pipeline will not work properly."
        )
    )


logger = logging.getLogger("__name__")
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
    embedding: BaseEmbeddings,
    llm: ChatLLM,
    vector_store: BaseVectorStore,
):
    nano_graphrag_llm_func = wrap_llm_func(llm)
    nano_graphrag_embedding_func = wrap_embedding_func(embedding)
    nano_graphrag_vector_store_cls = wrap_vector_store_cls(vector_store)

    graphrag = GraphRAG(
        working_dir=input_path,
        best_model_func=nano_graphrag_llm_func,
        cheap_model_func=nano_graphrag_llm_func,
        embedding_func=nano_graphrag_embedding_func,
        vector_db_storage_cls=nano_graphrag_vector_store_cls,
    )

    return graphrag


def list_of_list_to_df(data: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(data[1:], columns=data[0])
    return df


def clean_quote(input: str) -> str:
    return re.sub(r"[\"']", "", input)


async def nano_graph_rag_build_local_query_context(
    graphrag,
    query,
    query_param,
):
    knowledge_graph_inst = graphrag.chunk_entity_relation_graph
    entities_vdb = graphrag.entities_vdb
    community_reports = graphrag.community_reports
    text_chunks_db = graphrag.text_chunks

    results = await entities_vdb.query(query, top_k=query_param.top_k)
    if not len(results):
        raise ValueError("No results found")

    node_datas = await asyncio.gather(
        *[knowledge_graph_inst.get_node(r["entity_name"]) for r in results]
    )
    node_degrees = await asyncio.gather(
        *[knowledge_graph_inst.node_degree(r["entity_name"]) for r in results]
    )
    node_datas = [
        {**n, "entity_name": k["entity_name"], "rank": d}
        for k, n, d in zip(results, node_datas, node_degrees)
        if n is not None
    ]
    use_communities = await _find_most_related_community_from_entities(
        node_datas, query_param, community_reports
    )
    use_text_units = await _find_most_related_text_unit_from_entities(
        node_datas, query_param, text_chunks_db, knowledge_graph_inst
    )
    use_relations = await _find_most_related_edges_from_entities(
        node_datas, query_param, knowledge_graph_inst
    )
    entites_section_list = [["id", "entity", "type", "description", "rank"]]
    for i, n in enumerate(node_datas):
        entites_section_list.append(
            [
                str(i),
                clean_quote(n["entity_name"]),
                n.get("entity_type", "UNKNOWN"),
                clean_quote(n.get("description", "UNKNOWN")),
                n["rank"],
            ]
        )
    entities_df = list_of_list_to_df(entites_section_list)

    relations_section_list = [
        ["id", "source", "target", "description", "weight", "rank"]
    ]
    for i, e in enumerate(use_relations):
        relations_section_list.append(
            [
                str(i),
                clean_quote(e["src_tgt"][0]),
                clean_quote(e["src_tgt"][1]),
                clean_quote(e["description"]),
                e["weight"],
                e["rank"],
            ]
        )
    relations_df = list_of_list_to_df(relations_section_list)

    communities_section_list = [["id", "content"]]
    for i, c in enumerate(use_communities):
        communities_section_list.append([str(i), c["report_string"]])
    communities_df = list_of_list_to_df(communities_section_list)

    text_units_section_list = [["id", "content"]]
    for i, t in enumerate(use_text_units):
        text_units_section_list.append([str(i), t["content"]])
    sources_df = list_of_list_to_df(text_units_section_list)

    return entities_df, relations_df, communities_df, sources_df


class NanoGraphRAGIndexingPipeline(GraphRAGIndexingPipeline):
    """GraphRAG specific indexing pipeline"""

    embedding: BaseEmbeddings = Param(help="The embedding model")
    llm: ChatLLM = Param(help="The LLM model")

    @classmethod
    def get_pipeline(cls, user_settings, index_settings) -> GraphRAGIndexingPipeline:
        obj = cls(
            embedding=embeddings[
                index_settings.get("embedding", embeddings.get_default_name())
            ],
            llm=llms[index_settings.get("llm", llms.get_default_name())],
        )
        return obj

    def call_graphrag_index(self, graph_id: str, docs: list[Document]):
        _, input_path = prepare_graph_index_path(graph_id)

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
            input_path,
            self.embedding,
            self.llm,
            self.VS,
        )

        # output must be contain: Loaded graph from
        # ..input/graph_chunk_entity_relation.graphml with xxx nodes, xxx edges
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

    def run(
        self,
        file_paths: str | Path | list[str | Path],
        reindex: bool = False,
        *args,
        **kwargs,
    ) -> tuple[list[str | None], list[str | None], list[Document]]:
        try:
            streaming = self.stream(file_paths, reindex, *args, **kwargs)
            while True:
                value = next(streaming)
                logger.info("Yielded: %s" % value)
        except StopIteration as exc:
            indexed_result: tuple[
                list[str | None], list[str | None], list[Document]
            ] = exc.value
            return indexed_result
        except Exception as general_exc:
            raise RuntimeError("Indexing does not run properly") from general_exc


class NanoGraphRAGRetrieverPipeline(DocumentRetrievalPipeline):
    """GraphRAG specific retriever pipeline"""

    Index = Param(help="The SQLAlchemy Index table")
    file_ids: list[str] = []
    embedding: BaseEmbeddings = Param(help="The embedding model")
    llm: ChatLLM = Param(help="The LLM model")

    @classmethod
    def get_pipeline(cls, user_settings, index_settings, selected):
        """Get retriever objects associated with the index

        Args:
            settings: the settings of the app
            kwargs: other arguments
        """
        _, file_ids, _ = selected  # TODO: Workaround for the default file_ids
        obj = cls(
            file_ids=file_ids,
            embedding=embeddings[
                index_settings.get("embedding", embeddings.get_default_name())
            ],
            llm=llms[index_settings.get("llm", llms.get_default_name())],
        )
        return obj

    def _build_graph_search(self, file_ids: list[str]):
        file_id = file_ids[0]

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
            input_path,
            self.embedding,
            self.llm,
            self.VS,
        )
        query_params = QueryParam(mode="local", only_need_context=True)

        return graphrag, query_params

    def _to_document(self, header: str, context_text: str) -> RetrievedDocument:
        return RetrievedDocument(
            text=context_text,
            metadata={
                "file_name": header,
                "type": "table",
                "llm_trulens_score": 1.0,
            },
            score=1.0,
        )

    def format_context_records(
        self, entities, relationships, reports, sources
    ) -> list[RetrievedDocument]:
        docs = []
        context: str = ""

        # entities current parsing error
        header = "<b>Entities</b>\n"
        context = entities[["entity", "description"]].to_markdown(index=False)
        docs.append(self._to_document(header, context))

        header = "\n<b>Relationships</b>\n"
        context = relationships[["source", "target", "description"]].to_markdown(
            index=False
        )
        docs.append(self._to_document(header, context))

        header = "\n<b>Reports</b>\n"
        context = ""
        for _, row in reports.iterrows():
            title, content = row["id"], row["content"]  # not contain title
            context += f"\n\n<h5>Report <b>{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        header = "\n<b>Sources</b>\n"
        context = ""
        for _, row in sources.iterrows():
            title, content = row["id"], row["content"]
            context += f"\n\n<h5>Source <b>#{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        return docs

    def plot_graph(self, relationships):
        G = create_knowledge_graph(relationships)
        plot = visualize_graph(G)
        return plot

    def run(
        self,
        text: str,
        doc_ids: Optional[list[str]] = None,
    ) -> list[RetrievedDocument]:
        doc_ids = doc_ids or self.file_ids
        if not doc_ids:
            logger.info(f"Skip retrieval because of no selected files: {self}")
            return []

        graphrag, query_params = self._build_graph_search(file_ids=doc_ids)
        entities, relationships, reports, sources = asyncio.run(
            nano_graph_rag_build_local_query_context(graphrag, text, query_params)
        )

        documents = self.format_context_records(
            entities, relationships, reports, sources
        )
        plot = self.plot_graph(relationships)

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
