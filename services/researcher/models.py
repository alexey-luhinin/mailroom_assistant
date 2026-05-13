from pydantic import BaseModel


class ResearchRequest(BaseModel):
    email_id: str
    max_emails: int = 5


class EmailSummaryItem(BaseModel):
    id: str
    date: str
    subject: str
    summary: str


class ResearchResponse(BaseModel):
    sender: str
    history_count: int
    summaries: list[EmailSummaryItem]
