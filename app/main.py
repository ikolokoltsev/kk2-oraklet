import io
import logging
import pandas as pd
from typing import Annotated
from fastapi import FastAPI, HTTPException, UploadFile, File

from app import data
from app.schemas import UploadResponse
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/data/upload", responses={400: {"description": "Invalid file"}, 413: {"description": "File is too big"}})
async def upload(file: Annotated[UploadFile, File(...)]) -> UploadResponse:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Wrong file format. It should be .csv")

    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")
    
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds size limit")
    
    for encoding in ("utf-8", "latin-1"):
        try:
            df =pd.read_csv(io.BytesIO(content), encoding=encoding)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    else:
        raise HTTPException(status_code=400, detail="Could not parse CSV file")
    
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file has no data")
    
    data.set_dataset(df)
    logger.info("Uploaded: %s", file.filename)
    
    return UploadResponse(rows=len(df), columns=list(df.columns), dtypes={col: str(dtype) for col, dtype in df.dtypes.items()})

@app.get("/data/stats", responses={404: {"Description": "No dataset uploaded"}})
def stats() -> dict:
    df = data.get_dataset()
    if df is None:
        raise HTTPException(status_code=404, detail="No dataset uploaded")
    
    return data.get_stats()