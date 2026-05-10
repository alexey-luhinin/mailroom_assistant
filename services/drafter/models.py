from typing import Optional
from pydantic import BaseModel


class DraftRequest(BaseModel):
    email_id: str
    instructions: str = ""


class DraftJobResponse(BaseModel):
    job_id: str
    status: str


class DraftResponse(BaseModel):
    job_id: str
    status: str
    email_id: Optional[str] = None
    draft_id: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    language: Optional[str] = None
    error: Optional[str] = None


class DraftListItem(BaseModel):
    job_id: str
    email_id: str
    draft_id: str
    subject: str
    body: str
    language: str
    created_at: str
