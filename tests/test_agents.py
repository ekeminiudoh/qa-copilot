"""Tests for agent system."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.agents.specialized import (
    AnalystAgent,
    AutomationAgent,
    BugInvestigatorAgent,
    DeveloperAgent,
    DocumentationAgent,
    PerformanceEngineerAgent,
    SecurityReviewerAgent,
    SQLAgent,
    TesterAgent,
    create_specialized_agents,
    AGENT_REGISTRY,
)
from backend.agents.base import SimpleAgent
from backend.router import RouterService


# ─── Agent Creation ───────────────────────────────────────────────────────────

def test_all_agents_registered():
    expected = {
        "analyst", "developer", "tester", "sql", "automation",
        "documentation", "bug_investigator", "security_reviewer", "performance_engineer"
    }
    assert set(AGENT_REGISTRY.keys()) == expected


def test_create_all_agents():
    agents = create_specialized_agents()
    assert len(agents) == 9
    for name, agent in agents.items():
        assert isinstance(agent, SimpleAgent)
        assert agent.name == name
        assert agent.system_prompt


def test_agent_has_system_prompt():
    for AgentClass in AGENT_REGISTRY.values():
        agent = AgentClass()
        assert len(agent.system_prompt) > 50


# ─── Agent Processing ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_process_calls_llm():
    """Agent.process() should call llm_client.chat."""
    from backend.models.llm import ChatResponse, LLMProvider
    from backend.models.llm import TokenUsage

    mock_response = ChatResponse(
        content="Mock agent response",
        tokens_used=None,
        model_used="test-model",
        provider=LLMProvider.OPENROUTER,
    )

    with patch("backend.agents.base.llm_client") as mock_llm:
        mock_llm.chat = AsyncMock(return_value=mock_response)
        agent = TesterAgent()
        result = await agent.process("Generate login test cases")

    assert result == "Mock agent response"
    mock_llm.chat.assert_called_once()


@pytest.mark.asyncio
async def test_agent_process_with_context():
    from backend.models.llm import ChatResponse, LLMProvider

    mock_response = ChatResponse(
        content="Contextual response",
        tokens_used=None,
        model_used="test",
        provider=LLMProvider.OPENROUTER,
    )

    with patch("backend.agents.base.llm_client") as mock_llm:
        mock_llm.chat = AsyncMock(return_value=mock_response)
        agent = AnalystAgent()
        result = await agent.process("Analyze this", context="Some context here")

    assert result == "Contextual response"
    # Verify context was injected into system message
    call_args = mock_llm.chat.call_args[0][0]
    system_msg = next(m for m in call_args if m["role"] == "system")
    assert "Some context here" in system_msg["content"]


# ─── Router ───────────────────────────────────────────────────────────────────

def test_router_selects_tester_for_test_query():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.choose_agents("write test cases for login")
    agent_names = [a.name for a in result.agents]
    assert "tester" in agent_names


def test_router_selects_sql_for_sql_query():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.choose_agents("optimize this SQL query with JOIN")
    agent_names = [a.name for a in result.agents]
    assert "sql" in agent_names


def test_router_selects_security_for_security_query():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.choose_agents("check for SQL injection vulnerability")
    agent_names = [a.name for a in result.agents]
    assert "security_reviewer" in agent_names


def test_router_falls_back_to_default():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.choose_agents("hello world")
    assert len(result.agents) == 1
    assert result.execute_in_parallel is False


def test_router_selects_multiple_for_compound_query():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.choose_agents("write test cases and SQL validation queries")
    agent_names = [a.name for a in result.agents]
    assert len(result.agents) >= 2


@pytest.mark.asyncio
async def test_router_execute():
    from backend.models.llm import ChatResponse, LLMProvider

    agents = create_specialized_agents()
    router = RouterService(agents)

    mock_response = ChatResponse(
        content="SQL review result",
        tokens_used=None,
        model_used="test",
        provider=LLMProvider.OPENROUTER,
    )

    with patch("backend.agents.base.llm_client") as mock_llm:
        mock_llm.chat = AsyncMock(return_value=mock_response)
        responses = await router.execute("optimize this sql query")

    assert len(responses) >= 1
    for name, content in responses:
        assert isinstance(name, str)
        assert isinstance(content, str)


def test_merge_single_response():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.merge_responses([("tester", "Here are the test cases")])
    assert result == "Here are the test cases"


def test_merge_multiple_responses():
    agents = create_specialized_agents()
    router = RouterService(agents)
    result = router.merge_responses([
        ("tester", "Test cases here"),
        ("analyst", "Analysis here"),
    ])
    assert "specialist agents" in result.lower()
    assert "Test cases here" in result
    assert "Analysis here" in result
