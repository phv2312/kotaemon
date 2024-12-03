import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile


def save_upload_file_tmp(upload_file: UploadFile) -> str:
    # https://stackoverflow.com/questions/63580229/how-to-save-uploadfile-in-fastapi
    try:
        suffix = Path(upload_file.filename).suffix
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = Path(tmp.name)
            # Perform file processing here...
            # Example:
            # process_file(tmp_path)

    except Exception as e:
        print(f"Error processing file: {e}")
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        raise e

    finally:
        upload_file.file.close()

    return str(tmp_path)
