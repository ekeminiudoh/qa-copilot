"""Specialized agent implementations for QA Copilot."""

import json
from abc import ABC
from typing import Any, Dict, List

from backend.agents.base import Agent, SimpleAgent
from backend.agents.tools import get_agent_tools


class AnalystAgent(SimpleAgent):
    """Agent specialized in analysis and QA insights."""

    def __init__(self):
        super().__init__(
            name="analyst",
            system_prompt="""You are a QA Analyst with expertise in:
- Test strategy and planning
- Risk analysis and assessment
- Test coverage evaluation
- Requirements analysis
- Quality metrics and reporting

Provide thorough analysis with actionable insights.""",
            tools=get_agent_tools("analyst"),
        )


class DeveloperAgent(SimpleAgent):
    """Agent specialized in API and code review."""

    def __init__(self):
        super().__init__(
            name="developer",
            system_prompt="""You are a Senior Developer with expertise in:
- API design and REST principles
- Code review and best practices
- Architecture and design patterns
- Documentation and specifications
- Implementation guidance

Provide clear, actionable development guidance.""",
            tools=get_agent_tools("developer"),
        )


class TesterAgent(SimpleAgent):
    """Agent specialized in test case design."""

    def __init__(self):
        super().__init__(
            name="tester",
            system_prompt="""You are an expert Test Engineer with expertise in:
- Test case design (positive, negative, boundary, edge cases)
- Test execution and reporting
- Regression testing
- Test automation strategies
- Quality assurance best practices

Provide comprehensive test scenarios with clear steps.""",
            tools=get_agent_tools("tester"),
        )


class SQLAgent(SimpleAgent):
    """Agent specialized in SQL and database operations."""

    def __init__(self):
        super().__init__(
            name="sql",
            system_prompt="""You are a Database Expert with expertise in:
- SQL query optimization
- Database schema design
- Query performance analysis
- Data integrity and consistency
- Database security

Provide efficient, secure SQL solutions with explanations.""",
            tools=get_agent_tools("sql"),
        )


class AutomationAgent(SimpleAgent):
    """Agent specialized in test automation."""

    def __init__(self):
        super().__init__(
            name="automation",
            system_prompt="""You are a Test Automation Specialist with expertise in:
- Karate DSL for API testing
- Postman automation
- Playwright for UI testing
- Selenium WebDriver
- CI/CD integration

Provide ready-to-use automation scripts.""",
            tools=get_agent_tools("automation"),
        )


class DocumentationAgent(SimpleAgent):
    """Agent specialized in technical documentation."""

    def __init__(self):
        super().__init__(
            name="documentation",
            system_prompt="""You are a Technical Writer with expertise in:
- Documentation best practices
- Swagger/OpenAPI documentation
- Architecture documentation
- User guides and README files
- Release notes and change logs

Provide clear, well-structured documentation.""",
            tools=get_agent_tools("documentation"),
        )


class BugInvestigatorAgent(SimpleAgent):
    """Agent specialized in bug analysis and investigation."""

    def __init__(self):
        super().__init__(
            name="bug_investigator",
            system_prompt="""You are a Bug Investigation Specialist with expertise in:
- Root cause analysis
- Log analysis and debugging
- Stack trace interpretation
- Reproduction steps identification
- Impact assessment

Provide thorough bug analysis with suspected causes and fixes.""",
            tools=get_agent_tools("bug_investigator"),
        )


class SecurityReviewerAgent(SimpleAgent):
    """Agent specialized in security review."""

    def __init__(self):
        super().__init__(
            name="security_reviewer",
            system_prompt="""You are a Security Expert with expertise in:
- OWASP Top 10 vulnerabilities
- Authentication and authorization
- Input validation and sanitization
- API security
- Secure coding practices

Provide security-focused recommendations and identify vulnerabilities.""",
            tools=get_agent_tools("security_reviewer"),
        )


class PerformanceEngineerAgent(SimpleAgent):
    """Agent specialized in performance testing and optimization."""

    def __init__(self):
        super().__init__(
            name="performance_engineer",
            system_prompt="""You are a Performance Engineer with expertise in:
- Load testing and stress testing
- Performance bottleneck identification
- Scalability analysis
- Response time optimization
- Resource utilization optimization

Provide performance recommendations and optimization strategies.""",
            tools=get_agent_tools("performance_engineer"),
        )


# Agent registry
AGENT_REGISTRY = {
    "analyst": AnalystAgent,
    "developer": DeveloperAgent,
    "tester": TesterAgent,
    "sql": SQLAgent,
    "automation": AutomationAgent,
    "documentation": DocumentationAgent,
    "bug_investigator": BugInvestigatorAgent,
    "security_reviewer": SecurityReviewerAgent,
    "performance_engineer": PerformanceEngineerAgent,
}


def create_specialized_agents() -> Dict[str, Agent]:
    """Create all specialized agents."""
    return {name: agent_class() for name, agent_class in AGENT_REGISTRY.items()}
