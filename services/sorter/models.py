from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

Label = Literal["urgent", "action_needed", "fyi", "newsletter", "promo", "spam", "calendar"]

class ClassifiedEmail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    subject: str
    date: str
    label: Label
    reason: str
    priority: int


class SortRequest(BaseModel):
    days: int = 1


class SortResponse(BaseModel):
    total: int
    new: int
    skipped: int
    emails: list[ClassifiedEmail]
