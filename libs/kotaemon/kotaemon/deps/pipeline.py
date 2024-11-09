import logging
from typing import Any, TypeAlias

import yaml
from pydantic import BaseModel, Field
from typing_extensions import Self

logger = logging.getLogger(__name__)

Primitive: TypeAlias = str | int | bool | float


class Prototype(BaseModel):
    name: str
    container: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    root: dict[str, Prototype]

    @classmethod
    def from_yaml(cls, path: str) -> Self:
        with open(path, "r") as file:
            config: dict[str, Any] = yaml.safe_load(file)

        prototypes: dict[str, Prototype] = {}
        for component in config.get("components", []):
            prototype = Prototype.model_validate(component)

            is_duplicate = prototype.name in prototypes
            assert not is_duplicate, f"Duplicate component name {prototype.name}"
            prototypes[prototype.name] = prototype

        return cls(root=prototypes)

    def is_leaf(self, node: Primitive) -> bool:
        # A node is considered not a leaf if it is a string and exists in the root.
        not_leaf = isinstance(node, str) and node in self.root
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
        assert node in self.root, f"Node: {node} not found"

        prototype: Prototype = self.root[node]

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
