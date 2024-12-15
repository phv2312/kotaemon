# Kotaemon Workflows

## Setup

```bash
pip install -e . "libs/kotaemon-workflows"
```

## Usage

### As-SDK

```python
from workflows.impl.simple import SimpleWorkflow


workflow = SimpleWorkflow("libs/workflows/workflows/cfgs/default.yaml")

# Indexing
ids, errors, docs = workflow.index(
    file_paths=["<your_file_path>"],
    reindex=True
)

for doc in docs:
    print(doc)

# Retrieval
retrieved_docs = workflow.retrieve(text="<your_query>")

print(f"Number of relevant nodes: {len(retrieved_docs)}")
for doc in retrieved_docs:
    print(doc)

# Save your workflow
workflow.save_yaml("default_rag.yaml")
```

### As-API

```sh
fastapi run libs/kotaemon-workflows/app/main.py
```
