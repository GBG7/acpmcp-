# lorecollector.py

import os
from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from smolagents import CodeAgent, DuckDuckGoSearchTool, VisitWebpageTool
from groq import Groq
from smolagents.models.base import BaseModel
from dotenv import load_dotenv
load_dotenv()


# Custom wrapper for Groq to be compatible with smolagents
class GroqChatModel(BaseModel):
    def __init__(self, model_id: str, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model_id = model_id

    def complete(self, messages: list[dict], **kwargs) -> str:
        completion = self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1024),
            top_p=kwargs.get("top_p", 0.95),
            stream=False,
        )
        return completion.choices[0].message.content


# Hardcoded Groq API key for now
GROQ_API_KEY = os.getenv("GROQ_API")

# Initialize Groq-powered model
model = GroqChatModel(
    model_id="qwen/qwen3-32b",
    api_key=GROQ_API_KEY
)

# Start ACP server
server = Server()


@server.agent()
async def health_agent(
        input: list[Message],
        context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Handles health-related questions from patients using web tools + Groq Qwen."""

    agent = CodeAgent(
        tools=[DuckDuckGoSearchTool(), VisitWebpageTool()],
        model=model
    )

    prompt: str = input[0].parts[0].content
    response = agent.run(prompt)

    yield Message(parts=[MessagePart(content=str(response))])


if __name__ == "__main__":
    server.run(port=8000)
