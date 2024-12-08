from pathlib import Path

from kotaemon_workflows.components import Components

from kotaemon.schemas.crud import FileCRUD

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
DEFAULT_CFG_PATH = ROOT / "cfgs/default.yaml"


class SimpleWorkflow:
    def __init__(
        self,
        cfg_path: str | Path = DEFAULT_CFG_PATH,
        components: Components | None = None,
    ):
        if components is not None:
            self.components = components
        else:
            self.components = Components.from_yaml(cfg_path)

    def save_yaml(self, path: str) -> None:
        self.components.save_yaml(path)

    @property
    def source(self):
        if not hasattr(self, "_source"):
            self._source = self.components.get("source")
        return self._source

    @property
    def indexer(self):
        if not hasattr(self, "_indexer"):
            self._indexer = self.components.get("indexer")
        return self._indexer

    @property
    def retriever(self):
        if not hasattr(self, "_retriever"):
            self._retriever = self.components.get("retriever")
        return self._retriever

    # TODO: Replace stream -> index directly
    def index(self, file_paths: str | list[str], reindex: bool = True):
        """Index documents from file paths."""
        file_paths = [file_paths] if isinstance(file_paths, str | Path) else file_paths
        file_ids, errors, docs = self.indexer.run(
            file_paths=file_paths, reindex=reindex
        )
        return file_ids, errors, docs

    def retrieve(self, text: str, file_ids: list[str] | None = None):
        """Retrieve documents from the index."""
        if file_ids is None:
            filecrud = FileCRUD(self.source)
            file_ids = filecrud.list_docids()
        retrieved_docs = self.retriever.run(text=text, doc_ids=file_ids)
        return retrieved_docs
