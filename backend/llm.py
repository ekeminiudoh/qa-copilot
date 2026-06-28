"""LLM API client and embedding wrapper supporting multiple providers."""

import asyncio
from typing import AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI, OpenAIError

from backend.config import settings
from backend.core.logger import logger
from backend.models.llm import ChatResponse, LLMProvider, TokenUsage

# Provider endpoints and models
PROVIDER_CONFIGS = {
    LLMProvider.OPENROUTER: {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": [
            "deepseek/deepseek-chat",
            "openai/gpt-4",
            "anthropic/claude-3-opus",
            "google/gemini-pro",
            "meta-llama/llama-2-70b",
        ],
    },
    LLMProvider.OPENAI: {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": ["gpt-4", "gpt-3.5-turbo"],
    },
    LLMProvider.ANTHROPIC: {
        "base_url": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
    },
}


class LLMClient:
    """Client wrapper for multi-provider LLM access with token tracking."""

    def __init__(self, provider: LLMProvider = LLMProvider.OPENROUTER):
        self.provider = provider
        self.api_key = self._get_api_key()
        self.model = settings.model
        self.embedding_model = settings.embedding_model
        self._client: Optional[AsyncOpenAI] = None
        self.token_usage_history: List[TokenUsage] = []

    def _get_api_key(self) -> str:
        """Get API key for the provider."""
        if self.provider == LLMProvider.OPENROUTER:
            return settings.openrouter_api_key
        # Other providers can be added here
        return ""

    def _get_base_url(self) -> str:
        """Get base URL for the provider."""
        config = PROVIDER_CONFIGS.get(self.provider)
        return config["base_url"] if config else "https://openrouter.ai/api/v1"

    def _get_client(self) -> AsyncOpenAI:
        """Return a cached AsyncOpenAI client instance."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(f"LLM API key is required for {self.provider}")
            self._client = AsyncOpenAI(
                base_url=self._get_base_url(),
                api_key=self.api_key,
            )
        return self._client

    def _track_token_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> TokenUsage:
        """Track token usage and calculate cost."""
        usage = TokenUsage(
            provider=self.provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        # Estimate costs (these are approximate)
        if model.startswith("gpt-4"):
            usage.cost_usd = (prompt_tokens * 0.00003 + completion_tokens * 0.00006)
        elif model.startswith("gpt-3.5"):
            usage.cost_usd = (prompt_tokens * 0.0000005 + completion_tokens * 0.0000015)
        elif "claude" in model:
            usage.cost_usd = (prompt_tokens * 0.00003 + completion_tokens * 0.00015)

        self.token_usage_history.append(usage)
        return usage

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        retries: int = 3,
    ) -> ChatResponse:
        """Send a chat request and return the assistant response with usage."""
        client = self._get_client()
        for attempt in range(1, retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""

                # Track token usage
                tokens_used = None
                if hasattr(response, "usage") and response.usage:
                    tokens_used = self._track_token_usage(
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                        self.model,
                    )

                return ChatResponse(
                    content=content.strip(),
                    tokens_used=tokens_used,
                    model_used=self.model,
                    provider=self.provider,
                )
            except OpenAIError as error:
                logger.warning(
                    "LLM chat attempt %d failed: %s",
                    attempt,
                    error,
                )
                if attempt == retries:
                    logger.error("LLM chat exhausted retries: %s", error)
                    raise
                await asyncio.sleep(2 ** attempt)

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response."""
        client = self._get_client()
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except OpenAIError as error:
            logger.error("LLM stream failed: %s", error)
            raise

    async def embed(self, texts: List[str], retries: int = 3) -> List[List[float]]:
        """Create embeddings for a list of texts."""
        client = self._get_client()
        for attempt in range(1, retries + 1):
            try:
                response = await client.embeddings.create(
                    model=self.embedding_model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except OpenAIError as error:
                logger.warning(
                    "Embedding generation attempt %d failed: %s",
                    attempt,
                    error,
                )
                if attempt == retries:
                    logger.error("Embedding generation exhausted retries: %s", error)
                    raise
                await asyncio.sleep(2 ** attempt)

    def get_token_usage_summary(self) -> Dict:
        """Get summary of token usage."""
        if not self.token_usage_history:
            return {"total_tokens": 0, "total_cost": 0.0, "requests": 0}

        total_tokens = sum(u.total_tokens for u in self.token_usage_history)
        total_cost = sum(u.cost_usd for u in self.token_usage_history)
        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "requests": len(self.token_usage_history),
            "average_tokens_per_request": total_tokens / len(self.token_usage_history),
        }


# Global LLM client instance
llm_client = LLMClient(provider=LLMProvider.OPENROUTER)
