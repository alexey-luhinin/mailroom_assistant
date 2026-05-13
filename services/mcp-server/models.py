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
    is_read: bool = False


class Email(EmailSummary):
    body: str
    list_unsubscribe: Optional[str] = None


class DraftRequest(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None


class DraftResponse(BaseModel):
    draft_id: str
