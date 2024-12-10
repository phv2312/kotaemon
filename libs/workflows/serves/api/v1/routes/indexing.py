from concurrent.futures import Executor
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from fastapi import (
    APIRouter, 
    Depends, 
    File, 
    HTTPException, 
    UploadFile, 
    status
)
from libs.workflows.workflows.interface import IWorkflow

from ..deps import get_executor, get_workflow
from ..models import IndexedResponse, IndexedStatus

router = APIRouter()


def index_single(
    filepath: Path,
    workflow: IWorkflow,
) -> IndexedResponse:
    indexed_ids, errors, _ = workflow.index([filepath])
    if len(indexed_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing for {filepath.name} returned unexpected tuple"
        )
    
    if len(errors) > 0 and errors[0] is not None:
        # error
        return IndexedResponse(
            file=filepath.name,
            file_id=indexed_ids[0],
            status=IndexedStatus.FAILED,
            message=str(errors[0])
        )
         
    # success
    return IndexedResponse(
        file=filepath.name,
        file_id=indexed_ids[0],
        status=IndexedStatus.SUCCESS,
    )


@router.post(
    "/index", 
    response_model=list[IndexedResponse]
)
async def indexing(
    files: list[UploadFile] = File(...),
    workflow: IWorkflow = Depends(get_workflow),
    executor: Executor = Depends(get_executor),
) -> list[IndexedResponse]:
    
    with TemporaryDirectory() as temp_dir:
        futures = []
        for file in files:
            temp_file = Path(temp_dir) / file.filename
            
            with temp_file.open("wb") as file_content:
                shutil.copyfileobj(file.file, file_content)

            futures.append(
                executor.submit(
                    index_single,
                    temp_file, 
                    workflow
                )
            )
        
        responses: list[IndexedResponse] = [
            future.result() 
            for future in futures
        ]

    return responses
