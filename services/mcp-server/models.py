from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EmailSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    subject: str
    date: str
    snippet: str
    thread_id: str


class Email(EmailSummary):
    body: str


class DraftRequest(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None


class DraftResponse(BaseModel):
    draft_id: str
