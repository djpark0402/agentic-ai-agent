from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    system: str | None = None
    model: str | None = None
    conversation_id: Optional[UUID] = None


class ConversationCreate(BaseModel):
    session_id: str
    title: str | None = None


class ConversationRead(BaseModel):
    id: UUID
    session_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
