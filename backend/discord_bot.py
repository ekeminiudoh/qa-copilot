"""Discord bot integration for QA Copilot — all slash commands with streaming."""

import asyncio
import os
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from backend.config import settings


DISCORD_MAX_MSG = 1900  # Safe Discord message limit


def _truncate(text: str, limit: int = DISCORD_MAX_MSG) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _split_message(text: str, limit: int = DISCORD_MAX_MSG) -> list[str]:
    """Split long text into multiple messages under Discord's limit."""
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts


class QACopilotBot(commands.Cog):
    """QA Copilot Discord bot commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_url = os.getenv("API_URL", "http://localhost:8000")
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None
        self._history: list = []

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_token(self) -> str:
        """Authenticate with the backend using admin credentials."""
        if self._token:
            return self._token
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.api_url}/auth/login",
                json={"username": settings.admin_username, "password": settings.admin_password},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._token = data.get("access_token", "")
                    logger.info("Discord bot authenticated with backend")
                    return self._token
        except Exception as exc:
            logger.error("Discord bot auth failed: %s", exc)
        return ""

    async def _api_post(self, path: str, payload: dict) -> Optional[dict]:
        token = await self._get_token()
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.api_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 401:
                    self._token = None  # Force re-auth on next call
                text = await resp.text()
                logger.warning("API %s returned %d: %s", path, resp.status, text[:200])
        except Exception as exc:
            logger.error("API call to %s failed: %s", path, exc)
        return None

    async def _send_long(self, interaction: discord.Interaction, text: str, title: str = "") -> None:
        """Send potentially long text, splitting into multiple messages."""
        parts = _split_message(text)
        header = f"**{title}**\n" if title else ""
        for i, part in enumerate(parts):
            prefix = header if i == 0 else ""
            await interaction.followup.send(f"{prefix}{part}")
            if i < len(parts) - 1:
                await asyncio.sleep(0.3)

    # ─── Slash Commands ───────────────────────────────────────────────────────

    @app_commands.command(name="analyze", description="Analyze a requirement or specification with the Analyst agent")
    @app_commands.describe(content="The requirement, spec, or content to analyze")
    async def analyze(self, interaction: discord.Interaction, content: str):
        await interaction.response.defer(thinking=True)
        result = await self._api_post("/api/qa/analyze", {"content": content, "analysis_type": "general"})
        if result:
            text = result.get("analysis", "No analysis returned")
            conf = result.get("confidence", 0)
            await self._send_long(interaction, text, f"Analysis (confidence: {conf:.0%})")
        else:
            await interaction.followup.send("Error: Could not reach backend API")

    @app_commands.command(name="testcases", description="Generate test cases from a requirement")
    @app_commands.describe(
        requirement="The requirement or user story to test",
        framework="Optional automation framework (karate, playwright, cypress)"
    )
    async def testcases(
        self,
        interaction: discord.Interaction,
        requirement: str,
        framework: Optional[str] = None,
    ):
        await interaction.response.defer(thinking=True)
        result = await self._api_post("/api/qa/test-cases/generate", {
            "requirement": requirement,
            "test_types": ["positive", "negative", "boundary", "edge"],
            "framework": framework,
        })
        if result:
            text = result.get("test_cases", "No test cases returned")
            conf = result.get("confidence", 0)
            await self._send_long(interaction, text, f"Test Cases (confidence: {conf:.0%})")
        else:
            await interaction.followup.send("Error: Could not generate test cases")

    @app_commands.command(name="sql", description="Review a SQL query for performance and security")
    @app_commands.describe(query="The SQL query to review", dialect="Database dialect (postgresql, mysql, etc.)")
    async def sql(
        self,
        interaction: discord.Interaction,
        query: str,
        dialect: Optional[str] = "generic",
    ):
        await interaction.response.defer(thinking=True)
        result = await self._api_post("/api/qa/sql/review", {"sql_query": query, "dialect": dialect or "generic"})
        if result:
            text = result.get("review", "No review returned")
            conf = result.get("confidence", 0)
            await self._send_long(interaction, text, f"SQL Review (confidence: {conf:.0%})")
        else:
            await interaction.followup.send("Error: Could not review SQL")

    @app_commands.command(name="automation", description="Generate automation scripts")
    @app_commands.describe(
        requirement="What to automate",
        framework="Framework to use: karate, playwright, cypress, selenium, rest_assured, postman"
    )
    async def automation(
        self,
        interaction: discord.Interaction,
        requirement: str,
        framework: str = "karate",
    ):
        await interaction.response.defer(thinking=True)
        result = await self._api_post("/api/qa/automation/generate", {
            "requirement": requirement,
            "framework": framework,
        })
        if result:
            text = result.get("automation_code", "No code returned")
            conf = result.get("confidence", 0)
            await self._send_long(interaction, f"```\n{text[:1800]}\n```", f"Automation ({framework}) confidence: {conf:.0%}")
        else:
            await interaction.followup.send("Error: Could not generate automation code")

    @app_commands.command(name="security", description="Review code for security vulnerabilities")
    @app_commands.describe(code="Code snippet to review (keep it short for Discord)")
    async def security(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(thinking=True)
        result = await self._api_post("/api/qa/security/review", {
            "code": code,
            "language": "unknown",
            "focus": ["owasp", "injection", "auth"],
        })
        if result:
            text = result.get("review", "No review returned")
            await self._send_long(interaction, text, "Security Review")
        else:
            await interaction.followup.send("Error: Could not complete security review")

    @app_commands.command(name="bug", description="Investigate a bug using description and/or logs")
    @app_commands.describe(
        description="Bug description",
        logs="Optional: paste a short log excerpt"
    )
    async def bug(
        self,
        interaction: discord.Interaction,
        description: str,
        logs: Optional[str] = "",
    ):
        await interaction.response.defer(thinking=True)
        result = await self._api_post("/api/qa/bug/investigate", {
            "description": description,
            "logs": logs or "",
        })
        if result:
            text = result.get("investigation", "No investigation returned")
            conf = result.get("confidence", 0)
            await self._send_long(interaction, text, f"Bug Investigation (confidence: {conf:.0%})")
        else:
            await interaction.followup.send("Error: Could not investigate bug")

    @app_commands.command(name="report", description="Get the latest test execution report summary")
    async def report(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        token = await self._get_token()
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.api_url}/api/reports/history",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 5},
            ) as resp:
                if resp.status != 200:
                    await interaction.followup.send("No execution history found.")
                    return
                runs = await resp.json()

            if not runs:
                await interaction.followup.send("No test runs found. Execute some tests first!")
                return

            lines = ["**Recent Test Execution Reports:**\n"]
            for run in runs[:5]:
                lines.append(
                    f"• `{run['run_id']}` — {run.get('framework', '?')} | "
                    f"{run.get('passed', 0)}/{run.get('total_tests', 0)} passed "
                    f"({run.get('success_rate', 0):.1f}%) | {str(run.get('created_at', ''))[:10]}"
                )
            await interaction.followup.send("\n".join(lines))
        except Exception as exc:
            logger.error("Report command failed: %s", exc)
            await interaction.followup.send(f"Error fetching reports: {exc}")

    @app_commands.command(name="history", description="Show your recent chat and query history")
    async def history(self, interaction: discord.Interaction):
        if not self._history:
            await interaction.response.send_message("No history yet in this session.")
            return
        lines = ["**Recent Queries:**\n"]
        for i, item in enumerate(self._history[-10:], 1):
            lines.append(f"{i}. {item[:100]}")
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="upload", description="Instructions for uploading documents to the knowledge base")
    async def upload(self, interaction: discord.Interaction):
        msg = """**Uploading Documents to QA Copilot Knowledge Base**

Use the web UI at **http://localhost:8501** to upload documents.

Supported formats: PDF, DOCX, TXT, Markdown, JSON, YAML, SQL, Images (OCR)

**Via API:**
```bash
curl -X POST http://localhost:8000/api/qa/files/upload \\
  -H "Authorization: Bearer <token>" \\
  -F "file=@yourfile.pdf"
```
"""
        await interaction.response.send_message(msg)

    @app_commands.command(name="help", description="Show all available QA Copilot commands")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 QA Copilot Commands",
            description="AI-powered QA assistant for your testing lifecycle",
            color=discord.Color.blue(),
        )
        commands_list = [
            ("/analyze <content>", "Analyze requirements or specifications"),
            ("/testcases <requirement> [framework]", "Generate comprehensive test cases"),
            ("/sql <query> [dialect]", "Review SQL for performance & security"),
            ("/automation <requirement> <framework>", "Generate Karate/Playwright/Cypress scripts"),
            ("/security <code>", "OWASP security vulnerability review"),
            ("/bug <description> [logs]", "Root cause analysis for bugs"),
            ("/report", "Show recent test execution reports"),
            ("/upload", "How to upload documents to knowledge base"),
            ("/history", "Show recent query history"),
            ("/help", "Show this help message"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)

        embed.set_footer(text="QA Copilot v1.0 | Web UI: http://localhost:8501")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="chat", description="Chat with any QA agent")
    @app_commands.describe(
        message="Your message",
        agent="Agent to use (analyst, tester, developer, sql, automation, bug_investigator, security_reviewer)"
    )
    async def chat(
        self,
        interaction: discord.Interaction,
        message: str,
        agent: Optional[str] = None,
    ):
        await interaction.response.defer(thinking=True)
        self._history.append(message)
        payload = {"query": message}
        if agent:
            payload["agent"] = agent

        result = await self._api_post("/api/query", payload)
        if result:
            response = result.get("response", "No response")
            agent_name = result.get("agent", agent or "auto")
            await self._send_long(interaction, response, f"Agent: {agent_name}")
        else:
            await interaction.followup.send("Error: Could not get response from backend")

    async def cog_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()


def create_discord_bot() -> commands.Bot:
    """Create and configure the Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    @bot.event
    async def on_ready():
        logger.info("Discord bot logged in as %s (ID: %s)", bot.user, bot.user.id)
        try:
            synced = await bot.tree.sync()
            logger.info("Synced %d slash commands", len(synced))
        except Exception as exc:
            logger.error("Failed to sync commands: %s", exc)

    @bot.event
    async def on_command_error(ctx, error):
        logger.error("Bot command error: %s", error)

    asyncio.get_event_loop().run_until_complete(bot.add_cog(QACopilotBot(bot)))
    return bot


def run_discord_bot():
    """Run the Discord bot."""
    token = settings.discord_token or os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN is required to start the Discord bot.")

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    @bot.event
    async def on_ready():
        logger.info("Discord bot ready: %s", bot.user)
        try:
            synced = await bot.tree.sync()
            logger.info("Synced %d slash commands", len(synced))
        except Exception as exc:
            logger.error("Failed to sync slash commands: %s", exc)

    async def setup():
        await bot.add_cog(QACopilotBot(bot))

    asyncio.get_event_loop().run_until_complete(setup())
    bot.run(token)


if __name__ == "__main__":
    run_discord_bot()
