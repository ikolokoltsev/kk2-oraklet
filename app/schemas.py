from pydantic import BaseModel

class UploadResponse(BaseModel):
    rows: int
    columns: list[str]
    dtypes: dict[str, str]