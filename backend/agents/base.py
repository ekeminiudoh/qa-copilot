"""Base agent implementations and interfaces."""

from abc import ABC, abstractmethod
from typing import List, Mapping

from backend.llm import llm_client


class Agent(ABC):
    """Base agent interface."""

    def __init__(self, name: str, system_prompt: str, tools: list | None = None):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []

    @abstractmethod
    async def process(self, query: str, context: str = "") -> str:
        """Process a query and return a response."""
        pass

    def build_messages(self, query: str, history: List[dict]) -> List[dict]:
        """Build message list for LLM."""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})
        return messages


class SimpleAgent(Agent):
    """Simple agent that calls the LLM."""

    async def process(self, query: str, context: str = "") -> str:
        """Process query using LLM."""
        system_msg = self.system_prompt
        if context:
            system_msg += f"\n\nContext:\n{context}"
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query},
        ]
        response = await llm_client.chat(messages)
        return response.content
