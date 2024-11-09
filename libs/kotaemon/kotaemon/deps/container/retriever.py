from enum import Enum
from pathlib import Path
from typing import Any

# TODO: change to ktem
from ktem.index.file.base import BaseFileIndexRetriever
from ktem.index.file.graph.pipelines import GraphRAGRetrieverPipeline
from ktem.index.file.pipelines import DocumentRetrievalPipeline
from pydantic import BaseModel, ConfigDict, Field

import flowsettings
from kotaemon.schemas.file.index import Index
from kotaemon.schemas.file.source import Source
from kotaemon.storages.docstores import BaseDocumentStore
from kotaemon.storages.vectorstores import BaseVectorStore


class RetrivalMode(str, Enum):
    HYBRID = "hybrid"


class GraphRAGSearchType(str, Enum):
    LOCAL = "local"
    GLOBAL = "global"


class UserGraphRAGRetrieverSettings(BaseModel):
    """
    Reference:
    """

    model_config = ConfigDict(use_enum_values=True)
    search_type: GraphRAGSearchType = Field(
        default=GraphRAGSearchType.LOCAL, validate_default=True
    )


class UserFileRetrieverSettings(BaseModel):
    """
    Reference: ktem.index.file.pipelines.DocumentRetrievalPipeline
    """

    model_config = ConfigDict(use_enum_values=True)

    use_reranking: bool = False

    # IF True, for each retrieved document, the pipeline will look
    # for surrounding tables (e.g. within the page)
    prioritize_table: bool = False

    # Number of documents to retrieve
    num_retrieval: int = 5

    mmr: bool = False

    retrieval_mode: str = Field(default=RetrivalMode.HYBRID, validate_default=True)


class UserFileIndexerSettings(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    embedding: str = "azure"


class Retriever:
    DEFAULT_SELECTED: list[Any] = ["all", [], 1]

    @staticmethod
    def graphrag(
        # source: Source,
        # index: Index,
        # vectorstore: BaseVectorStore,
        # documentstore: BaseDocumentStore,
        # user_settings: UserGraphRAGRetrieverSettings | dict[str | Any],
        collection_idx: int = 1,
        user_id: int = 1,
        selected: list[Any] = DEFAULT_SELECTED,
    ) -> BaseFileIndexRetriever:
        # match user_settings:
        #     case dict():
        #         user_settings = (
        # UserGraphRAGRetrieverSettings.model_validate(user_settings)
        # )

        # index_settings: dict[str, Any] = {}

        return GraphRAGRetrieverPipeline(file_ids=selected[1], Index=Index)

        # obj = GraphRAGRetrieverPipeline.get_pipeline(
        #     user_settings.model_dump(),
        #     index_settings,
        #     selected
        # )

        # filestorage = (
        #     Path(flowsettings.KH_FILESTORAGE_PATH) / f"index_{collection_idx}"
        # )

        # obj.Source = source
        # obj.Index = index
        # obj.VS = vectorstore
        # obj.DS = documentstore
        # obj.FSPath = filestorage
        # obj.user_id = user_id

        # return obj

    @staticmethod
    def default(
        source: Source,
        index: Index,
        vectorstore: BaseVectorStore,
        documentstore: BaseDocumentStore,
        user_settings: UserFileRetrieverSettings | dict[str, Any],
        index_settings: UserFileIndexerSettings | dict[str, Any],
        collection_idx: int = 1,
        user_id: int = 1,
        selected: list[Any] = DEFAULT_SELECTED,
    ) -> BaseFileIndexRetriever:
        match user_settings:
            case dict():
                user_settings = UserFileRetrieverSettings.model_validate(user_settings)

        match index_settings:
            case dict():
                index_settings = UserFileIndexerSettings.model_validate(index_settings)

        obj = DocumentRetrievalPipeline.get_pipeline(
            user_settings.model_dump(), index_settings.model_dump(), selected
        )

        filestorage = Path(flowsettings.KH_FILESTORAGE_PATH) / f"index_{collection_idx}"
        filestorage.mkdir(parents=True, exist_ok=True)

        obj.Source = source
        obj.Index = index
        obj.VS = vectorstore
        obj.DS = documentstore
        obj.FSPath = filestorage
        obj.user_id = user_id

        return obj
