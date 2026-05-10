from typing import Literal, Optional
from pydantic import BaseModel

Status = Literal["pending", "done", "failed"]
RunStep = Literal["sorting", "briefing", "done", "failed"]
DraftStep = Literal["researching", "drafting", "reviewing", "done", "failed"]


class RunRequest(BaseModel):
    days: int = 1


class DraftRequest(BaseModel):
    email_id: str
    instructions: str = ""


class BriefingSummary(BaseModel):
    total: int
    urgent: int
    action_needed: int
    fyi: int
    calendar: int
    newsletter: int
    promo: int
    spam: int


class BriefingResult(BaseModel):
    summary: BriefingSummary
    content: str


class RunJobResponse(BaseModel):
    job_id: str
    status: Status
    step: RunStep
    emails_classified: Optional[int] = None
    emails_skipped: Optional[int] = None
    briefing: Optional[BriefingResult] = None
    error: Optional[str] = None


class DraftResult(BaseModel):
    draft_id: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    language: Optional[str] = None


class DraftJobResponse(BaseModel):
    job_id: str
    status: Status
    step: DraftStep
    draft: Optional[DraftResult] = None
    error: Optional[str] = None
