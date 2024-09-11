import json
from pathlib import Path

import pytest
from openai.resources.embeddings import Embeddings

from kotaemon.agents.tools import ComponentTool, GoogleSearchTool, WikipediaTool
from kotaemon.base import Document
from kotaemon.embeddings import LCAzureOpenAIEmbeddings
from kotaemon.indices.vectorindex import VectorIndexing, VectorRetrieval
from kotaemon.storages import ChromaVectorStore, InMemoryDocumentStore

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch):
    monkeypatch.setattr(Embeddings, "create", lambda *args, **kwargs: openai_embedding)


def test_google_tool(mock_google_search):
    tool = GoogleSearchTool()
    assert tool.name
    assert tool.description
    output = tool("What is Cinnamon AI")
    assert output


def test_wikipedia_tool():
    tool = WikipediaTool()
    assert tool.name
    assert tool.description
    output = tool("Cinnamon")
    assert output


def test_pipeline_tool(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = LCAzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )

    index_pipeline = VectorIndexing(
        vector_store=db, embedding=embedding, doc_store=doc_store
    )
    retrieval_pipeline = VectorRetrieval(
        vector_store=db, doc_store=doc_store, embedding=embedding
    )

    index_tool = ComponentTool(
        name="index_document",
        description="A tool to use to index a document to be searched later",
        component=index_pipeline,
    )
    output = index_tool({"text": Document(text="Cinnamon AI")})

    retrieval_tool = ComponentTool(
        name="search_document",
        description="A tool to use to search a document in a vectorstore",
        component=retrieval_pipeline,
    )
    output = retrieval_tool("Cinnamon AI")
    assert output
