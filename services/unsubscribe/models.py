from typing import Literal, Optional
from pydantic import BaseModel

Recommendation = Literal["unsubscribe", "consider"]


class AnalyzeRequest(BaseModel):
    days: int = 30


class AnalyzeJobResponse(BaseModel):
    job_id: str
    status: str


class Candidate(BaseModel):
    sender: str
    name: str
    total: int
    opened: int
    open_rate: float
    recommendation: Recommendation
    unsubscribe_url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    days: Optional[int] = None
    total_senders: Optional[int] = None
    candidates: Optional[list[Candidate]] = None
    error: Optional[str] = None
