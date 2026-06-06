import io
import logging
import pandas as pd
from typing import Annotated
from fastapi import Body, FastAPI, HTTPException, UploadFile, File

from app import data
from app.schemas import AskRequest, AskResponse, UploadResponse
from app.config import settings
from app.chain.pipeline import oraklet
from app.chain.steps import PromptBuilderInput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
def health() -> dict[str, str]:
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

@app.get("/data/stats", responses={404: {"description": "No dataset uploaded"}})
def stats() -> dict:
    df = data.get_dataset()
    if df is None:
        raise HTTPException(status_code=404, detail="No dataset uploaded")
    
    return data.get_stats()

@app.post(
    "/ai/ask",
    responses={400: {"description": "No dataset uploaded yet"}, 500: {"description": "Model error"}},
)
def ask(request: Annotated[AskRequest, Body()]) -> AskResponse:
    if data.get_dataset() is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded yet")

    try:
        return oraklet.invoke(
            PromptBuilderInput(question=request.question, stats=data.get_stats())
        )
    except RuntimeError as e:
        logger.exception("Chain error")
        raise HTTPException(status_code=500, detail=str(e))