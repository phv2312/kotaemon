# Kotaemon Backend

## Setup

```bash
pip install -e . "libs/backend"
```

## Usage

```python
from backend.pipeline import Pipeline
from kotaemon.schemas.crud import FileCRUD

pipeline = Pipeline.from_yaml("pipelines/file-collection.yaml")
indexer = pipeline.get("indexer")
retriver = pipeline.get("retriever")

# Indexing
streamed_docs = indexer.stream(
    file_paths=["<your_file_path>"],
    reindex=True
)

for doc in streamed_docs:
    print(doc)

# Retrieving
source = pipeline.get("source")
filecrud = FileCRUD(source)

doc_ids: list[str] = filecrud.list_docids()
retrieved_docs = retriver.run(
    text="<your_query>",
    doc_ids=doc_ids
)

print(f"Number of relevant nodes: {len(retrieved_docs)}")
for doc in retrieved_docs:
    print(doc)

```
