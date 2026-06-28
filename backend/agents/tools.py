"""Agent tool definitions and registration."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AgentTool:
    """Describe a tool available to an agent."""

    name: str
    description: str
    example: str = ""


AGENT_TOOL_CLASSES: Dict[str, List[AgentTool]] = {
    "analyst": [
        AgentTool(
            name="requirement_analysis",
            description="Analyze requirements and identify risk, gaps, and acceptance criteria.",
            example="Assess this requirement for risk and completeness.",
        )
    ],
    "developer": [
        AgentTool(
            name="design_review",
            description="Review architecture and implementation approaches.",
            example="Suggest how to implement this API endpoint.",
        )
    ],
    "tester": [
        AgentTool(
            name="test_plan",
            description="Generate test cases and validation rules.",
            example="Generate regression and boundary tests for this feature.",
        )
    ],
    "automation": [
        AgentTool(
            name="automation_script",
            description="Create automation scripts for test execution.",
            example="Generate a Playwright script for this web flow.",
        )
    ],
    "sql": [
        AgentTool(
            name="sql_review",
            description="Review and optimize SQL statements and schema design.",
            example="Optimize this query for performance.",
        )
    ],
    "documentation": [
        AgentTool(
            name="doc_generation",
            description="Create technical documentation, release notes, and Confluence pages.",
            example="Write release notes for this feature.",
        )
    ],
    "bug_investigator": [
        AgentTool(
            name="root_cause_analysis",
            description="Analyze bug reports, logs, and stack traces for root cause.",
            example="Determine the root cause from this error log.",
        )
    ],
    "security_reviewer": [
        AgentTool(
            name="security_assessment",
            description="Review application security and identify vulnerabilities.",
            example="Check this flow for injection or authentication issues.",
        )
    ],
    "performance_engineer": [
        AgentTool(
            name="performance_assessment",
            description="Evaluate performance risks and optimization opportunities.",
            example="Analyze this endpoint for latency bottlenecks.",
        )
    ],
}


def get_agent_tools(agent_name: str) -> List[AgentTool]:
    """Get the tools available for a specific agent."""
    return AGENT_TOOL_CLASSES.get(agent_name, [])
