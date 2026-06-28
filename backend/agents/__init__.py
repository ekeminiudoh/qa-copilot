"""Agent registry and prompt factory."""

from pathlib import Path
from typing import Dict

from backend.agents.base import Agent
from backend.agents.specialized import create_specialized_agents
from backend.config import settings
from backend.core.logger import logger

DEFAULT_AGENT_PROMPTS: Dict[str, str] = {
    "analyst": "You are the Analyst agent. Provide requirement analysis, risk assessment, and recommendation summaries for QA engineering projects.",
    "developer": "You are the Developer agent. Provide architecture guidance, API design, implementation recommendations, and code-level analysis.",
    "tester": "You are the Tester agent. Create test plans, generate test cases, identify edge cases, and verify quality requirements.",
    "automation": "You are the Automation agent. Generate automation scripts, CI/CD workflows, and repeatable test execution strategies.",
    "sql": "You are the SQL agent. Review SQL, optimize queries, explain database design, and generate SQL statements.",
    "documentation": "You are the Documentation agent. Create clear technical documentation, release notes, and Confluence-style content.",
    "bug_investigator": "You are the Bug Investigator agent. Analyze logs, stack traces, API payloads, and error reports to diagnose root cause.",
    "security_reviewer": "You are the Security Reviewer agent. Evaluate security posture, identify vulnerabilities, and recommend mitigations.",
    "performance_engineer": "You are the Performance Engineer agent. Assess performance risks, latency, throughput, and scalability issues.",
}


def load_system_prompts() -> Dict[str, str]:
    """Load system prompts for all configured agents."""
    prompts: Dict[str, str] = {}
    prompts_dir = Path(settings.prompts_path)

    for agent_name in settings.agent_names:
        prompt_file = prompts_dir / f"{agent_name}.md"
        if prompt_file.exists():
            prompts[agent_name] = prompt_file.read_text(encoding="utf-8").strip()
        elif agent_name in DEFAULT_AGENT_PROMPTS:
            prompts[agent_name] = DEFAULT_AGENT_PROMPTS[agent_name]
            logger.warning("Missing prompt file for agent '%s'; using fallback prompt.", agent_name)

    return prompts


def create_agents() -> Dict[str, Agent]:
    """Instantiate specialized agents with custom prompts if available."""
    agents = create_specialized_agents()
    prompts = load_system_prompts()
    
    # Override default system prompts with file-based ones if available
    for agent_name, prompt in prompts.items():
        if agent_name in agents:
            agents[agent_name].system_prompt = prompt

    return agents
