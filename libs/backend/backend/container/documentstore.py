from typing import Final

import flowsettings
from kotaemon.storages.docstores import BaseDocumentStore, LanceDBDocumentStore


class DocumentStore:
    DEFAULT_COLLECTION_NAME: Final[str] = "default"

    @staticmethod
    def lancedb(
        storage_path: str | None = None, collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> BaseDocumentStore:
        storage_path = storage_path or flowsettings.KH_DOCSTORE.get("path")
        assert storage_path is not None

        return LanceDBDocumentStore(storage_path, collection_name=collection_name)
