# Kotaemon Backend

## Setup

```bash
pip install -e . "libs/kotaemon-workflows"
```

## Usage

```python
from kotaemon_workflows.pipeline import Pipeline


pipeline = Pipeline.from_yaml("libs/kotaemon-workflows/cfgs/default.yaml")

# Indexing
docs = pipeline.index(
    file_paths=["<your_file_path>"],
    reindex=True
)

for doc in docs:
    print(doc)

# Retrieving
retrieved_docs = pipeline.retrieve(text="<your_query>",)

print(f"Number of relevant nodes: {len(retrieved_docs)}")
for doc in retrieved_docs:
    print(doc)

# Save your workflow
pipeline.save_yaml("default_rag.yaml")
```
