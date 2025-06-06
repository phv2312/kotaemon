from pathlib import Path
from typing import Any

from ktem.index.file.base import BaseFileIndexIndexing
from ktem.index.file.graph.nano_graphrag.pipelines import NanoGraphRAGIndexingPipeline

# TODO: change to ktem later
from ktem.index.file.pipelines import IndexDocumentPipeline
from pydantic import BaseModel, ConfigDict

import flowsettings
from kotaemon.schemas.file.index import Index
from kotaemon.schemas.file.source import Source
from kotaemon.storages.docstores import BaseDocumentStore
from kotaemon.storages.vectorstores import BaseVectorStore


class UserFileIndexerSettings(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    embedding: str = "azure"


class Indexer:
    @staticmethod
    def default(
        source: Source,
        index: Index,
        vectorstore: BaseVectorStore,
        documentstore: BaseDocumentStore,
        collection_idx: int = 1,
        user_id: int = 1,
        private: bool = False,
        index_settings: UserFileIndexerSettings | dict[str, Any] = {},
    ) -> BaseFileIndexIndexing:
        match index_settings:
            case dict():
                index_settings = UserFileIndexerSettings.model_validate(index_settings)

        user_settings: dict[str, Any] = {}

        obj = IndexDocumentPipeline.get_pipeline(
            user_settings, index_settings.model_dump()
        )

        filestorage = Path(flowsettings.KH_FILESTORAGE_PATH) / f"index_{collection_idx}"
        filestorage.mkdir(parents=True, exist_ok=True)

        obj.Source = source
        obj.Index = index
        obj.VS = vectorstore
        obj.DS = documentstore
        obj.FSPath = filestorage
        obj.user_id = user_id
        obj.private = private

        return obj

    @staticmethod
    def nano_graphrag(
        source: Source,
        index: Index,
        vectorstore: BaseVectorStore,
        documentstore: BaseDocumentStore,
        collection_idx: int = 1,
        user_id: int = 1,
        private: bool = False,
        index_settings: UserFileIndexerSettings | dict[str, Any] = {},
    ) -> BaseFileIndexIndexing:
        user_settings: dict[str, Any] = {}

        obj = NanoGraphRAGIndexingPipeline.get_pipeline(user_settings, index_settings)

        filestorage = Path(flowsettings.KH_FILESTORAGE_PATH) / f"index_{collection_idx}"
        filestorage.mkdir(parents=True, exist_ok=True)

        obj.Source = source
        obj.Index = index
        obj.VS = vectorstore
        obj.DS = documentstore
        obj.FSPath = filestorage
        obj.user_id = user_id
        obj.private = private

        return obj
