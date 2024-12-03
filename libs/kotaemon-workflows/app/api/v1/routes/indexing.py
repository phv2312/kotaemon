from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from kotaemon_workflows.workflows.interface import IWorkflow

from app.api.v1.deps import get_workflow
from app.utils import save_upload_file_tmp

router = APIRouter()


@router.post("/index_files")
def index_files(
    files: list[UploadFile] = File(...),
    workflow: IWorkflow = Depends(get_workflow),
):
    tmp_files = []
    messages = []
    for file in files:
        try:
            tmp_file = save_upload_file_tmp(file)
            tmp_files.append(tmp_file)
            try:
                file_ids, errors, docs = workflow.index([tmp_file])
                if errors[0] is not None:
                    messages.append(
                        {
                            "file": file.filename,
                            "file_ids": file_ids,
                            "status": "failed",
                            "message": str(errors[0]),
                        }
                    )
                else:
                    messages.append(
                        {
                            "file": file.filename,
                            "file_ids": file_ids,
                            "status": "success",
                        }
                    )
            except Exception as e:
                errors.append(f"Error processing file {file.filename}: {str(e)}")
        except Exception as e:
            errors.append(f"Error saving temporary file {file.filename}: {str(e)}")

    for tmp_file in tmp_files:
        Path(tmp_file).unlink()

    return messages
