"""Data models for QA Copilot."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    """Chat message model."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class Conversation(BaseModel):
    """Conversation model."""

    id: str
    channel_id: int
    messages: List[Message] = []
    created_at: datetime = None
    updated_at: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class QueryRequest(BaseModel):
    """API query request."""

    query: Optional[str] = None
    context: Optional[str] = None
    agent: Optional[str] = None
