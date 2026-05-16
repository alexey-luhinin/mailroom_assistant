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


class CalendarAttendee(BaseModel):
    email: str
    name: str
    status: str


class CalendarEvent(BaseModel):
    id: str
    title: str
    start: str
    end: str
    all_day: bool
    description: Optional[str] = None
    location: Optional[str] = None
    meet_link: Optional[str] = None
    attendees: list[CalendarAttendee] = []
    organizer: str


class CalendarEventsResponse(BaseModel):
    week: str
    events: list[CalendarEvent]


class SentEmailSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    to: str
    subject: str
    date: str
    thread_id: str


class ThreadMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    date: str


class DraftRequest(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None


class DraftResponse(BaseModel):
    draft_id: str
