
import uuid
import logging

from kotaemon.base import BaseComponent, BaseIndexing, Document
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.storages import BaseDocumentStore, BaseVectorStore, BaseGraphStorage

logger = logging.getLogger(__name__)


class NanoGraphRAGIndexing(BaseIndexing):
    """Ingest the document, run through the embedding, and store the embedding in a
    vector store.

    This pipeline supports the following set of inputs:
        - List of documents
        - List of texts
    """

    # cache_dir: Optional[str] = getattr(flowsettings, "KH_CHUNKS_OUTPUT_DIR", None)
    chunks_vector_store: BaseVectorStore
    entities_vector_store: BaseVectorStore
    graph_store: BaseGraphStorage = None
    doc_store: BaseDocumentStore | None = None
    embedding: BaseEmbeddings
    entity_extraction_func: callable = extract_entities
    count_: int = 0

    def add_to_docstore(self, docs: list[Document]):
        if self.doc_store:
            logger.info("Adding documents to doc store")
            self.doc_store.add(docs)

    def add_to_vectorstore(self, docs: list[Document]):
        # in case we want to skip embedding
        if self.chunks_vector_store:
            logger.info(f"Getting embeddings for {len(docs)} nodes")
            embeddings = self.embedding(docs)
            logger.info("Adding embeddings to vector store")
            self.vector_store.add(
                embeddings=embeddings,
                ids=[t.doc_id for t in docs],
            )

    def build_entities_graph(self, docs: list[Document]):
        logger.info("Extract Entities")
        self.entities_vector_store
        entities_data = self.entity_extraction_func(docs)

        # TODO
        entities_data = self.graph_store.add_entities(entities_data)

        if not len(entities_data):
            logger.warning("Didn't extract any entities, maybe your LLM is not working")
            return

        # Add entities to vector store
        if self.entities_vector_store is not None:
            data_for_vector_store = [
                Document(
                    text=ed["entity_name"] + ed["description"], id_=str(uuid.uuid4())
                )
                for ed in entities_data
            ]
            entities_embeddings = self.embedding(data_for_vector_store)
            self.entities_vector_store.add(
                embeddings=entities_embeddings,
                ids=[t.doc_id for t in data_for_vector_store],
            )

    def run(self, texts: str | list[str] | Document | list[Document]):
        input_: list[Document] = []
        if not isinstance(texts, list):
            texts = [texts]

        for item in texts:
            if isinstance(item, str):
                input_.append(Document(text=item, id_=str(uuid.uuid4())))
            elif isinstance(item, Document):
                input_.append(item)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )
        
        # Chunking
        self.add_to_vectorstore(input_)
        self.add_to_docstore(input_)

        # Extract/summary entity and upsert to graph
        self.build_entities_graph(input_)

        # TODO: Update graph clustering
        # self.graph_store.clustering(
        #     self.graph_cluster_algorithm
        # )
        # generate_community_report(
        #     self.community_reports, self.graph_store, asdict(self)
        # )
