"""Memory and conversation management."""

from typing import Dict, List

from backend.models import Conversation, Message


class ConversationMemory:
    """In-memory conversation storage with sliding window."""

    def __init__(self, max_history: int = 20):
        self.conversations: Dict[int, Conversation] = {}
        self.max_history = max_history

    def get_or_create(self, channel_id: int, conversation_id: str = None) -> Conversation:
        """Get or create a conversation."""
        if channel_id not in self.conversations:
            conv_id = conversation_id or f"conv_{channel_id}_{id(self)}"
            self.conversations[channel_id] = Conversation(id=conv_id, channel_id=channel_id)
        return self.conversations[channel_id]

    def add_message(self, channel_id: int, message: Message) -> None:
        """Add a message to conversation, trimming to max_history."""
        conv = self.get_or_create(channel_id)
        conv.messages.append(message)
        if len(conv.messages) > self.max_history:
            conv.messages.pop(0)

    def get_history(self, channel_id: int) -> List[dict]:
        """Get message history as list of dicts suitable for LLM."""
        conv = self.get_or_create(channel_id)
        return [{"role": m.role, "content": m.content} for m in conv.messages]

    def get_context(self, channel_id: int, max_messages: int = 5) -> str:
        """Build a lightweight context string from recent history."""
        history = self.get_history(channel_id)
        if not history:
            return ""
        entries = []
        for item in history[-max_messages:]:
            role = item["role"].capitalize()
            entries.append(f"{role}: {item['content']}")
        return "\n".join(entries)

    def clear(self, channel_id: int) -> None:
        """Clear conversation history for a channel."""
        self.conversations.pop(channel_id, None)
