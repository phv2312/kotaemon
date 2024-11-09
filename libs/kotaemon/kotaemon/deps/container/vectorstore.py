from typing import Final

import flowsettings
from kotaemon.storages.vectorstores import BaseVectorStore, ChromaVectorStore


class VectorStore:
    DEFAULT_COLLECTION_NAME: Final[str] = "default"

    @staticmethod
    def chroma(
        storage_path: str | None = None, collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> BaseVectorStore:
        storage_path = storage_path or flowsettings.KH_VECTORSTORE.get("path")
        assert storage_path is not None, "Invalid vectorstore path"

        return ChromaVectorStore(storage_path, collection_name=collection_name)
