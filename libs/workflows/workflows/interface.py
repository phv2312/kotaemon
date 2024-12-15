from pathlib import Path
from typing import Protocol

from workflows.components import Components


class IWorkflow(Protocol):
    def from_yaml(self, cfg_path: str) -> Components:
        ...

    def save_yaml(self, path: str) -> None:
        ...

    def index(self, file_paths: str | Path | list[str | Path], reindex: bool = True):
        ...

    def retrieve(self, text: str, file_ids: list[str] | None = None):
        ...
