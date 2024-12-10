from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Final

from kotaemon.base.schema import Document, RetrievedDocument
from kotaemon.schemas.crud import FileCRUD
from kotaemon.schemas.file.source import Source
from ktem.index.file.base import BaseFileIndexIndexing, BaseFileIndexRetriever

from ..components import Components


def gen_default_config() -> Path:
    root: Path = Path(__file__).resolve().parents[1]
    return root / "cfgs/default.yaml"


@dataclass
class SimpleWorkflowConfig:
    source_key: str = "source"
    indexer_key: str = "indexer"
    retriever_key: str = "retriever"


class SimpleWorkflow:
    DEFAULT_CONFIG_PATH: Final[str] = gen_default_config()
    
    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG_PATH,
        config: SimpleWorkflowConfig | None = None
    ):
        assert config_path.exists(), f"Config {config_path} does not exist"
        self.components = Components.from_yaml(config_path)
        self.config = config or SimpleWorkflowConfig()
    
    def save_yaml(self, path: str) -> None:
        self.components.save_yaml(path)
    
    @cached_property
    def source(self) -> type[Source]:
        return self.components.get(self.config.source_key)

    @cached_property
    def indexer(self) -> BaseFileIndexIndexing:
        return self.components.get(self.config.indexer_key)

    @cached_property
    def retriever(self) -> BaseFileIndexRetriever:
        return self.components.get(self.config.retriever_key)

    def index(
        self, 
        file_paths: list[str], 
        reindex: bool = True
    ) -> tuple[list[str], list[str], list[Document]]:
        """Index documents from file paths."""
        file_ids, errors, docs = self.indexer.run(
            file_paths=file_paths, 
            reindex=reindex
        )
        return file_ids, errors, docs

    def retrieve(
        self, 
        text: str, 
        file_ids: list[str] | None = None
    ) -> list[RetrievedDocument]:
        """Retrieve documents from the index."""
        if file_ids is None:
            filecrud = FileCRUD(self.source)
            file_ids = filecrud.list_docids()
        retrieved_docs = self.retriever.run(text=text, doc_ids=file_ids)
        return retrieved_docs
