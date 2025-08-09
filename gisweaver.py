#!/usr/bin/env python
"""
GIS Weaver (Agent 2) – Maps structured lore to geographic constructs.
Uses Gemini 1.5 Pro. Returns GIS-ready JSON for downstream mapping.
"""
import json
import traceback
import re
from crewai import Crew, Task, Agent, LLM
from crewai_tools import RagTool

from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

import os
import logging
from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger(__name__)

# ── Gemini API key ─────────────────────
api_gem = os.getenv("api_gem")
if not api_gem:
    raise EnvironmentError("Missing api_gem")

# ── LLM Setup: Gemini 1.5 Pro ───────────
llm = LLM(
    model="gemini/gemini-1.5-flash",
    provider="google",
    api_key=api_gem,
    max_tokens=8192,
)

# ── RAG Tool Configuration ─────────────
config = {
    "llm": {
        "provider": "google",
        "config": {
            "model": "gemini-1.5-pro",
            "api_key": api_gem,
        },
    },
    "embedding_model": {
        "provider": "ollama",
        "config": {
            "model": "all-minilm:latest"
        }
    }
}

rag_tool = RagTool(config=config)
rag_tool.add("./data/topomapsymbols.pdf", data_type="pdf_file")

# ── Cartographer Agent Setup ──────────────
gis_agent = Agent(
    role="Fantasy GIS Cartographer",
    goal="Convert lore into terrain, faction regions, and conflict zones for mapping",
    backstory="You translate worldbuilding JSON into GIS-ready structures.",
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

JSON_SCHEMA = """{
  "terrain_features": [ "name (type)" ],
  "faction_regions": [ "faction: region" ],
  "conflict_zones": [ "location: conflict" ],
  "background": "Pick from: snowy, forest, desert, beach, urban, ship, halo-reach-map"
  "notes": "1–2 sentence summary of how terrain, factions, and conflict interrelate"
}"""

PROMPT_TMPL = """You are GIS Weaver.

Transform the structured worldbuilding JSON below into a GIS-friendly format.
In addition to terrain, faction zones, and conflicts, also choose a suitable background map type.

Choose from the following backgrounds: snowy, forest, desert, beach, urban, ship, halo-reach-map.
Pick the background that best matches the biome or dominant setting described in the lore.

Input:
{lore}

Respond EXACTLY in this JSON:

{schema}
"""

# ── ACP Server Setup ───────────────────
server = Server()


@server.agent(name="gis_weaver")
async def gis_weaver(
        input: list[Message],
        context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Transforms lore input into GIS-style cartographic JSON using Gemini 1.5 Pro."""

    lore = input[0].parts[0].content.strip()
    prompt = PROMPT_TMPL.format(lore=lore, schema=JSON_SCHEMA)

    task = Task(
        description=prompt,
        expected_output="Valid JSON with terrain_features, faction_regions, conflict_zones, background_img and notes",
        agent=gis_agent,
    )

    crew = Crew(agents=[gis_agent], tasks=[task], verbose=True)

    try:
        result = await crew.kickoff_async()
    except Exception as e:
        error = {
            "error": "LLM or Crew execution failed",
            "exception": str(e),
            "traceback": traceback.format_exc(),
        }
        yield Message(parts=[MessagePart(content=json.dumps(error, indent=2))])
        return

    # Extract first JSON object from output
    result_str = str(result)
    match = re.search(r"\{[\s\S]*\}", result_str)
    if match:
        try:
            parsed = json.loads(match.group(0))
        except Exception as e:
            parsed = {"error": f"Invalid JSON: {e}", "raw": match.group(0)}
    else:
        parsed = {"error": "No valid JSON found", "raw": result_str}

    yield Message(parts=[MessagePart(content=json.dumps(parsed, indent=2))])


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8001)
