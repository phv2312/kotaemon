from pathlib import Path
from typing import Protocol


class IWorkflow(Protocol):
    def from_yaml(self, cfg_path: str | Path):
        ...

    def save_yaml(self, path: str) -> None:
        ...

    def index(self, file_paths: str | list[str], reindex: bool = True):
        ...

    def retrieve(self, text: str, file_ids: list[str] | None = None):
        ...
