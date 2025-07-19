import os
from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from smolagents import CodeAgent, DuckDuckGoSearchTool, VisitWebpageTool, LiteLLMModel


API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_KEY_HERE")

model = LiteLLMModel(
    model_id="gemini/gemini-1.5-flash",   # or gemini-1.5-pro-latest
    api_key=API_KEY,
    num_ctx=8192,  # ~32k
)

server = Server()


@server.agent()
async def health_agent(
        input: list[Message],
        context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Handles health-related questions from patients using web tools + Gemini."""

    agent = CodeAgent(
        tools=[DuckDuckGoSearchTool(), VisitWebpageTool()],
        model=model
    )

    prompt: str = input[0].parts[0].content
    response = agent.run(prompt)

    yield Message(parts=[MessagePart(content=str(response))])


if __name__ == "__main__":
    server.run(port=8000)
