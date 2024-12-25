from dataclasses import field
from typing import Callable

import numpy as np
from nano_graphrag._utils import EmbeddingFunc, compute_args_hash
from nano_graphrag.base import BaseVectorStorage

from kotaemon.base import DocumentWithEmbedding
from kotaemon.base.schema import AIMessage, HumanMessage, SystemMessage
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import ChatLLM
from kotaemon.storages import BaseVectorStore


def wrap_llm_func(model: ChatLLM) -> Callable:
    async def llm_func(
        prompt, system_prompt=None, history_messages=[], **kwargs
    ) -> str:
        input_messages = [SystemMessage(text=system_prompt)] if system_prompt else []

        hashing_kv = kwargs.pop("hashing_kv", None)
        if history_messages:
            for msg in history_messages:
                if msg.get("role") == "user":
                    input_messages.append(HumanMessage(text=msg["content"]))
                else:
                    input_messages.append(AIMessage(text=msg["content"]))

        input_messages.append(HumanMessage(text=prompt))

        if hashing_kv is not None:
            args_hash = compute_args_hash("model", input_messages)
            if_cache_return = await hashing_kv.get_by_id(args_hash)
            if if_cache_return is not None:
                return if_cache_return["return"]

        output = model(input_messages).text

        print("-" * 50)
        print(output, "\n", "-" * 50)

        if hashing_kv is not None:
            await hashing_kv.upsert({args_hash: {"return": output, "model": "model"}})

        return output

    return llm_func


def wrap_embedding_func(model: BaseEmbeddings) -> Callable:
    async def embedding_func(texts: list[str]) -> np.ndarray:
        outputs = model(texts)
        embedding_outputs = np.array([doc.embedding for doc in outputs])

        return embedding_outputs

    embedding_dim = len(model(["Hi"])[0].embedding)
    embedding_func = EmbeddingFunc(
        embedding_dim=embedding_dim,
        max_token_size=8192,
        func=embedding_func,
    )

    return embedding_func


def wrap_vector_store_cls(default_vector_store: BaseVectorStore) -> type:
    class VectorStoreAdapter(BaseVectorStorage):
        embedding_func: EmbeddingFunc
        meta_fields: set = field(default_factory=set)
        vector_store: BaseVectorStore = default_vector_store

        async def query(self, query: str, top_k: int) -> list[dict]:
            embeddings = await self.embedding_func([query])
            embedding = embeddings[0]
            _, similarities, out_ids, metadatas = self.vector_store.query(
                embedding, top_k=top_k
            )

            # Filter out results with missing metadata fields
            results = []
            for id_, sim, metadata in zip(out_ids, similarities, metadatas):
                metadata = {k: v for k, v in metadata.items() if k in self.meta_fields}
                if len(metadata.keys()) < len(self.meta_fields):
                    continue
                results.append({"id": id_, "distance": 1 - sim, **metadata})

            return results

        async def upsert(self, data: dict[str, dict]):
            """Use 'content' field from value for embedding, use key as id.
            If embedding_func is None, use 'embedding' field from value
            """
            # Parse input
            data = {k: v for k, v in data.items() if "content" in v}
            ids = list(data.keys())
            contents = [v["content"] for v in data.values()]
            metadata = [
                {k: v for k, v in v.items() if k in self.meta_fields}
                for v in data.values()
            ]

            # Get embeddings
            embeddings = await self.embedding_func(contents)

            # Add to vector store
            docs_with_embedding = [
                DocumentWithEmbedding(
                    id_=id_, text=content, embedding=embedding.tolist()
                )
                for id_, content, embedding in zip(ids, contents, embeddings)
            ]
            self.vector_store.add(
                docs_with_embedding,
                metadatas=metadata,
            )

    return VectorStoreAdapter
