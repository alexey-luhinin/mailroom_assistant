from typing import Optional
from pydantic import BaseModel


class DraftContent(BaseModel):
    subject: str
    body: str
    language: str


class ReviewRequest(BaseModel):
    draft: DraftContent
    instructions: str = ""
    iteration: int = 1


class ReviewResponse(BaseModel):
    score: int
    approved: bool
    feedback: str
    improved_draft: Optional[None] = None


class BriefContext(BaseModel):
    urgent_count: int = 0
    action_needed_count: int = 0
    meetings_count: int = 0


class BriefReviewRequest(BaseModel):
    content: str
    context: BriefContext
