"""Core query API endpoint."""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents import create_agents
from backend.auth import get_current_user_db, optional_auth
from backend.db import get_db
from backend.db.crud import save_prompt_history
from backend.db.models import UserDB
from backend.memory import ConversationMemory
from backend.models import Message, QueryRequest
from backend.router import RouterService
from knowledge import KnowledgeBase

router = APIRouter(prefix="/api", tags=["api"])

# Shared singletons (initialized once per process)
_memory = ConversationMemory(max_history=20)
_agents = create_agents()
_router_service = RouterService(_agents)
_knowledge_base = KnowledgeBase()


@router.post("/query")
async def query(
    request: QueryRequest,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Process a query through the agent router with RAG context injection."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    start = time.time()

    try:
        if request.agent:
            agent = _agents.get(request.agent)
            if agent is None:
                raise HTTPException(status_code=404, detail="Requested agent not found")

            context = request.context or _knowledge_base.context_for(request.query)
            agent_response = await agent.process(request.query, context=context)
            agent_name = agent.name
            responses = [(agent_name, agent_response)]
        else:
            # Enrich context: conversation history + knowledge base
            history_ctx = _memory.get_context(channel_id=0, max_messages=5)
            kb_ctx = _knowledge_base.context_for(request.query)
            enriched_context = ""
            if history_ctx:
                enriched_context += f"Conversation history:\n{history_ctx}\n\n"
            if kb_ctx:
                enriched_context += kb_ctx
            if request.context:
                enriched_context += f"\n\nAdditional context:\n{request.context}"

            responses = await _router_service.execute(request.query, context=enriched_context)
            agent_name = responses[0][0] if responses else "unknown"
            agent_response = _router_service.merge_responses(responses)

        # Update conversation memory
        if request.query:
            _memory.add_message(0, Message(role="user", content=request.query))
        if agent_response:
            _memory.add_message(0, Message(role="assistant", content=agent_response))

        duration_ms = int((time.time() - start) * 1000)

        # Persist to DB
        await save_prompt_history(
            db,
            prompt=request.query,
            response=agent_response,
            agent_name=agent_name,
            user_id=current_user.id if current_user else None,
            duration_ms=duration_ms,
        )
        await db.commit()

        # Confidence heuristic
        conf = min(0.98, 0.7 + min(len(agent_response) / 2000, 0.28))

        return {
            "agent": agent_name,
            "agents_used": [r[0] for r in responses],
            "response": agent_response,
            "confidence": round(conf, 2),
            "duration_ms": duration_ms,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
