"""LLM models and types."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    LLAMA = "llama"


class TokenUsage(BaseModel):
    """Token usage statistics."""

    provider: LLMProvider
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str  # "system", "user", "assistant"
    content: str


class ChatResponse(BaseModel):
    """Chat response model."""

    content: str
    tokens_used: Optional[TokenUsage] = None
    model_used: str = None
    provider: Optional[LLMProvider] = None
