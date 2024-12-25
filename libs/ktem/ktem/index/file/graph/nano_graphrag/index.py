from typing import Any

from ktem.index.file.base import BaseFileIndexIndexing, BaseFileIndexRetriever
from ktem.index.file.index import FileIndex

from .pipelines import NanoGraphRAGIndexingPipeline, NanoGraphRAGRetrieverPipeline


class NanoGraphRAGIndex(FileIndex):
    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = NanoGraphRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [NanoGraphRAGRetrieverPipeline]

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        """Define the interface of the indexing pipeline"""

        prefix = f"index.options.{self.id}."
        stripped_settings = {}
        for key, value in settings.items():
            if key.startswith(prefix):
                stripped_settings[key[len(prefix) :]] = value

        indexer = self._indexing_pipeline_cls.get_pipeline(
            stripped_settings, self.config
        )
        indexer.VS = self._vs

        return indexer

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        prefix = f"index.options.{self.id}."
        stripped_settings = {}
        for key, value in settings.items():
            if key.startswith(prefix):
                stripped_settings[key[len(prefix) :]] = value

        nano_graphrag_retriever = NanoGraphRAGRetrieverPipeline.get_pipeline(
            stripped_settings, self.config, selected
        )
        nano_graphrag_retriever.Index = self._resources["Index"]
        nano_graphrag_retriever.VS = self._vs

        retrievers = [nano_graphrag_retriever]
        return retrievers
