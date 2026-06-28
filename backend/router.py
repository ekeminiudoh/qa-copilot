"""Query router for agent orchestration."""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Tuple

from backend.agents.base import Agent


@dataclass(frozen=True)
class RoutingResult:
    """Data structure describing selected agents and execution mode."""

    agents: List[Agent]
    execute_in_parallel: bool = True


class RouterService:
    """Routes queries to one or more specialized agents."""

    def __init__(self, agents: Dict[str, Agent]):
        self.agents = agents
        self.default_agent = agents.get("developer", next(iter(agents.values())))

    def choose_agents(self, query: str) -> RoutingResult:
        """Select agents based on the intent of the query."""
        normalized = query.lower()
        selected = []

        intent_keywords = {
            "analyst": ("analysis", "evaluate", "insight", "review", "report", "risk", "requirements"),
            "developer": ("api", "swagger", "endpoint", "request", "code", "implementation", "design"),
            "tester": ("test case", "test", "qa", "bug", "coverage", "assert", "pytest", "regression"),
            "automation": ("automation", "script", "ci", "pipeline", "github", "jenkins", "playwright", "selenium", "karate", "rest assured"),
            "sql": ("sql", "database", "schema", "query", "table", "join", "optimise", "optimize", "transaction"),
            "documentation": ("document", "docs", "readme", "architecture", "diagram", "release notes", "confluence"),
            "bug_investigator": ("bug", "incident", "root cause", "stack trace", "log", "failure", "crash"),
            "security_reviewer": ("security", "vulnerability", "xss", "sql injection", "authentication", "authorization", "secure"),
            "performance_engineer": ("performance", "latency", "throughput", "load", "stress", "benchmark", "scalability"),
        }

        for agent_name, keywords in intent_keywords.items():
            if any(keyword in normalized for keyword in keywords) and agent_name in self.agents:
                selected.append(self.agents[agent_name])

        if any(separator in normalized for separator in [" and ", ";", ","]):
            for name in ("tester", "automation", "sql", "bug_investigator", "security_reviewer"):
                if name in self.agents and self.agents[name] not in selected:
                    selected.append(self.agents[name])

        if not selected:
            return RoutingResult(agents=[self.default_agent], execute_in_parallel=False)

        return RoutingResult(agents=selected, execute_in_parallel=len(selected) > 1)

    async def execute(self, query: str, context: str = "") -> List[Tuple[str, str]]:
        """Execute the selected agents and return ordered responses."""
        routing = self.choose_agents(query)
        if routing.execute_in_parallel:
            tasks = [agent.process(query, context=context) for agent in routing.agents]
            responses = await asyncio.gather(*tasks)
        else:
            responses = [await routing.agents[0].process(query, context=context)]

        return list(zip([agent.name for agent in routing.agents], responses))

    def merge_responses(self, agent_responses: List[Tuple[str, str]]) -> str:
        """Merge multiple agent responses into a combined answer."""
        if len(agent_responses) == 1:
            return agent_responses[0][1]

        merged = ["The query was addressed by multiple specialist agents:"]
        for agent_name, response in agent_responses:
            merged.append(f"### {agent_name.replace('_', ' ').title()}")
            merged.append(response.strip())
        return "\n\n".join(merged)
