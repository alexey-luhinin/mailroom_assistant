from typing import Literal, Optional
from pydantic import BaseModel

Status = Literal["pending", "done", "failed"]


class BriefRequest(BaseModel):
    days: int = 1


class BriefJobResponse(BaseModel):
    job_id: str
    status: Status


class BriefSummary(BaseModel):
    total: int
    urgent: int
    action_needed: int
    fyi: int
    calendar: int
    newsletter: int
    promo: int
    spam: int


class BriefResponse(BaseModel):
    job_id: str
    status: Status
    created_at: Optional[str] = None
    summary: Optional[BriefSummary] = None
    content: Optional[str] = None
    error: Optional[str] = None


class BriefListItem(BaseModel):
    job_id: str
    created_at: str
    summary: BriefSummary
