from fastapi import APIRouter, Depends
from kotaemon_workflows.workflows.interface import IWorkflow

from app.api.v1.deps import get_workflow

router = APIRouter()


@router.post("/retrieved_docs")
def retrieve(
    message: str,
    workflow: IWorkflow = Depends(get_workflow),
):
    return workflow.retrieve(text=message)
