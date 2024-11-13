import logging
from pathlib import Path
from typing import Any, TypeAlias

import yaml
from pydantic import BaseModel, Field
from typing_extensions import Self

# This import is important for the yaml to access to
# the container
from kotaemon.schemas.crud import FileCRUD

from .container import *  # noqa

logger = logging.getLogger(__name__)

Primitive: TypeAlias = str | int | bool | float


class Prototype(BaseModel):
    name: str
    container: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class Pipeline:
    components: dict[str, Prototype]

    def __init__(self, components: dict[str, Prototype]) -> None:
        self.components = components

    @classmethod
    def from_yaml(cls, path: str) -> Self:
        with open(path, "r") as file:
            config: dict[str, Any] = yaml.safe_load(file)

        components: dict[str, Prototype] = {}
        for prototype in config.get("components", []):
            prototype = Prototype.model_validate(prototype)

            is_duplicate = prototype.name in components
            assert not is_duplicate, f"Duplicate component name {prototype.name}"
            components[prototype.name] = prototype
        return cls(components=components)

    def save_yaml(self, path: str) -> None:
        pipeline_yaml = {k: v.model_dump() for k, v in self.components.items()}
        with open(path, "w") as file:
            yaml.dump(pipeline_yaml, file)

    def is_leaf(self, node: Primitive) -> bool:
        # A node is considered not leaf if it is a string and exists in the components.
        not_leaf = isinstance(node, str) and node in self.components
        return not not_leaf

    def get_many(
        self, nodes: list[str], registered_nodes: dict[str, Any] = {}
    ) -> list[Any]:
        """Retrieve multiple nodes, handling dependencies.

        Args:
            nodes (List[str]): A list of node names to retrieve.
            registered_nodes (Dict[str, Any]): Dictionary of already instantiated nodes.

        Returns:
            List[Any]: A list of instantiated nodes.

        Raises:
            ValueError: If nodes contain nested lists or dictionaries.
        """
        results: list[Any] = []
        for node in nodes:
            is_leaf = self.is_leaf(node)
            if not is_leaf:
                results.append(self.get(node, registered_nodes))
            match node:
                # TODO: exclude list(), it can be supported in the future
                case list() | dict():
                    raise ValueError("Does not support nested dict() or list().")
                case _:
                    results.append(node)
        return results

    def get(self, node: str, registered_nodes: dict[str, Any] = {}) -> Any:
        """Retrieve a single node, instantiating it if necessary.

        Args:
            node (str): The node name to retrieve.
            registered_nodes (Dict[str, Any]): Dictionary of already instantiated nodes.

        Returns:
            Any: The instantiated node.

        Raises:
            ValueError: If an unsupported value type is encountered in parameters.
        """
        assert node in self.components, f"Node: {node} not found"

        prototype: Prototype = self.components[node]

        # Resolve dependencies
        resolved_params: dict[str, Any] = prototype.params
        for key, value in prototype.params.items():
            if self.is_leaf(value):
                resolved_params[key] = value
                continue

            match value:
                case str():
                    resolved_params[key] = self.get(value, registered_nodes)
                case list():
                    resolved_params[key] = self.get_many(value, registered_nodes)
                case _:
                    raise ValueError(
                        f"Invalid value type {type(value)} for param {key}"
                    )

        component_cls = eval(f"{prototype.container}.{prototype.type}")
        component_instance = component_cls(**resolved_params)

        registered_nodes[prototype.name] = component_instance

        return component_instance

    @property
    def source(self):
        if not hasattr(self, "_source"):
            self._source = self.get("source")
        return self._source

    @property
    def indexer(self):
        if not hasattr(self, "_indexer"):
            self._indexer = self.get("indexer")
        return self._indexer

    @property
    def retriever(self):
        if not hasattr(self, "_retriever"):
            self._retriever = self.get("retriever")
        return self._retriever

    # TODO: Replace stream -> index directly
    def index(self, file_paths: str | list[str], reindex: bool = True):
        """Index documents from file paths."""
        file_paths = [file_paths] if isinstance(file_paths, str | Path) else file_paths
        streamed_docs = self.indexer.stream(file_paths=file_paths, reindex=reindex)

        # Streaming results
        docs = []
        for docs in streamed_docs:
            docs.append(docs)
        return docs

    def retrieve(self, text: str, file_ids: list[str] | None = None):
        """Retrieve documents from the index."""
        if file_ids is None:
            filecrud = FileCRUD(self.source)
            file_ids = filecrud.list_docids()

        retrieved_docs = self.retriever.run(text=text, doc_ids=file_ids)
        return retrieved_docs
