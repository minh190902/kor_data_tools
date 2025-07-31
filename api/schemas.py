from typing import List, Optional
from pydantic import BaseModel

class ProcessingStatus(BaseModel):
    success: bool
    message: str
    processed_images: int
    extracted_questions: int
    csv_filename: Optional[str] = None

class APIResponse(BaseModel):
    status: str
    data: Optional[dict] = None
    message: str

class FileInfo(BaseModel):
    filename: str
    size: int
    created: str
    download_url: str

class ProcessRequest(BaseModel):
    source_info: str = "TOPIK Practice"

class ProcessResponse(BaseModel):
    success: bool
    message: str
    processed_images: int
    extracted_questions: int
    csv_filename: Optional[str] = None
    download_url: Optional[str] = None
