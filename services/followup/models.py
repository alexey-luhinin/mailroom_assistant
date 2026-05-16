from typing import Literal

from pydantic import BaseModel


class FollowupRequest(BaseModel):
    days: int = 30


class WaitingEmail(BaseModel):
    id: str
    thread_id: str
    to: str
    subject: str
    sent_at: str
    days_waiting: int


class JobPending(BaseModel):
    job_id: str
    status: Literal["pending"]


class JobDone(BaseModel):
    job_id: str
    status: Literal["done"]
    days: int
    waiting_count: int
    emails: list[WaitingEmail]


class JobFailed(BaseModel):
    job_id: str
    status: Literal["failed"]
    error: str
