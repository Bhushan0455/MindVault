from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    email: str
    password: str


class ContextIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    product: str = "Veyra Beat 200"
    channel: str = "instagram"
    audience: str = "consumer"
    region: str = "IN"
    content_type: str = "paid_ad"
    campaign: str | None = None
    publication_date: date = Field(default_factory=date.today)


class ContentIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    brand_id: str | None = None
    title: str = Field(min_length=1,max_length=255)
    body_text: str = Field(min_length=1,max_length=30000)
    context: ContextIn = Field(default_factory=ContextIn)
    expected_revision_id: str | None = None


class DecisionIn(BaseModel):
    action: Literal["accept", "edit", "reject", "dismiss"]
    edited_text: str | None = None
    note: str | None = None


class ApprovalIn(BaseModel):
    revision_id: str
    comment: str | None = None


class CommentIn(BaseModel):
    body: str = Field(min_length=1,max_length=10000)
    revision_id: str | None = None
    finding_id: str | None = None
