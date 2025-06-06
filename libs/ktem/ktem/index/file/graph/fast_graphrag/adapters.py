from typing import Any, Type, cast

import numpy as np
from fast_graphrag import BaseEmbeddingService, BaseLLMService
from fast_graphrag._llm._base import T_model
from fast_graphrag._types import BaseModelAlias
from pydantic import BaseModel

from kotaemon.base.schema import AIMessage, HumanMessage, SystemMessage
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import ChatLLM

# def wrap_llm_func(model):
#     async def llm_func(
#         prompt, system_prompt=None, history_messages=[], **kwargs
#     ) -> str:
#         input_messages = [SystemMessage(text=system_prompt)] if system_prompt else []

#         hashing_kv = kwargs.pop("hashing_kv", None)
#         if history_messages:
#             for msg in history_messages:
#                 if msg.get("role") == "user":
#                     input_messages.append(HumanMessage(text=msg["content"]))
#                 else:
#                     input_messages.append(AIMessage(text=msg["content"]))

#         input_messages.append(HumanMessage(text=prompt))

#         if hashing_kv is not None:
#             args_hash = compute_args_hash("model", input_messages)
#             if_cache_return = await hashing_kv.get_by_id(args_hash)
#             if if_cache_return is not None:
#                 return if_cache_return["return"]

#         output = model(input_messages).text

#         print("-" * 50)
#         print(output, "\n", "-" * 50)

#         if hashing_kv is not None:
#             await hashing_kv.upsert({args_hash: {"return": output, "model": "model"}})

#         return output


class FastGraphRAGLLMAdapter(BaseLLMService):
    def __init__(self, llm: ChatLLM):
        self.model = llm

    async def send_message(
        self,
        prompt,
        system_prompt: str | None = None,
        history_messages: list | None = None,
        response_model: BaseModel | BaseModelAlias | None = None,
        **kwargs
    ):
        input_messages = [SystemMessage(text=system_prompt)] if system_prompt else []

        if history_messages:
            for msg in history_messages:
                if msg.get("role") == "user":
                    input_messages.append(HumanMessage(text=msg["content"]))
                else:
                    input_messages.append(AIMessage(text=msg["content"]))

        input_messages.append(HumanMessage(text=prompt))

        response = self.model(input_messages, response_format=response_model)
        print("-" * 50)
        print(response_model)
        print(input_messages)
        print(response)

        if response_model:
            if issubclass(response_model, BaseModelAlias):
                response = response_model.Model.to_dataclass(response)
            else:
                response = response_model.model_validate(response)
            return response, None
        else:
            return response.text, None


class FastGraphRAGEmbeddingAdapter(BaseEmbeddingService):
    def __init__(self, embeddings: BaseEmbeddings):
        self.model = embeddings
        self. embedding_dim = len(self.model(["Hi"])[0].embedding)

    async def encode(self, texts: list[str]) -> np.ndarray[Any, np.dtype[np.float32]]:
        outputs = self.model(texts)
        embedding_outputs = np.array([doc.embedding for doc in outputs])

        return embedding_outputs
