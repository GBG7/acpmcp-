import os
from crewai import Crew, Task, Agent, LLM
from crewai_tools import RagTool
from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
import logging

# ── 0.  Make sure your Gemini API key is available ────────────────────────────
# PowerShell (one-off):  $env:GEMINI_API_KEY="your-key"
# Or put GEMINI_API_KEY=your-key in a .env and load with python-dotenv.

API_KEY = os.getenv("GEMINI_API_KEY")

llm = LLM(
    model="gemini/gemini-1.5-flash",
    api_key=API_KEY,
    max_tokens=8192,
)

config = {
    "llm": {
        "provider": "google",
        "config": {
            "model": "gemini/gemini-1.5-flash",
            "api_key": API_KEY,
        },
    },
    "embedding_model": {        # <-- local embedder, no api_key needed
        "provider": "ollama",
        "config": {
            "model": "all-minilm:latest",
        },
    },
}

rag_tool = RagTool(config=config)
rag_tool.add("./data/gold-hospital-and-premium-extras.pdf", data_type="pdf_file")

# ── 3.  Insurance agent definition -------------------------------------------
insurance_agent = Agent(
    role="Senior Insurance Coverage Assistant",
    goal="Determine whether something is covered or not",
    backstory=(
        "You are an expert insurance agent designed to assist with coverage queries. "
        "Whenever you call the knowledge-base tool the input must follow the pattern "
        "{query:'your query', kwargs:{}}"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[rag_tool],
    max_retry_limit=5,
)

logger = logging.getLogger(__name__)
server = Server()

# ── 4.  ACP agent -------------------------------------------------------------
@server.agent()
async def policy_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Answer insurance-policy questions with RAG + Gemini."""

    task = Task(
        description=input[0].parts[0].content,
        expected_output=(
            "A comprehensive answer to the user's question, containing the word "
            "'THE-FLASH!' at least twice."
        ),
        agent=insurance_agent,
    )
    crew = Crew(agents=[insurance_agent], tasks=[task], verbose=True)

    task_output = await crew.kickoff_async()
    logger.info("Task completed successfully")
    logger.info(task_output)

    # ACP ≥ 0.12: yield the Message itself (no RunYield(...))
    yield Message(
        role="agent/policy_agent",
        parts=[MessagePart(content=str(task_output), content_type="text/plain")],
    )


if __name__ == "__main__":
    server.run(port=8001)
