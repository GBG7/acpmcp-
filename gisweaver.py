#!/usr/bin/env python
"""
GIS Weaver (Agent 2) – Maps structured lore to geographic constructs.
Uses Groq (Qwen3-32B) via CrewAI LLM. Returns GIS-ready JSON for downstream mapping.
"""

import os
# kill any telemetry
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "1"
os.environ["CREWAI_TELEMETRY_DISABLED"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"
os.environ["OTEL_LOGS_EXPORTER"] = "none"
os.environ["CREWAI_LOG_LEVEL"] = "DEBUG"

import json
import traceback
import re
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from crewai import Crew, Task, Agent, LLM
from crewai_tools import RagTool

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

GROQ_API2 = os.getenv("GROQ_API2")
if not GROQ_API2:
    raise EnvironmentError("Missing GROQ_API2 in environment (.env)")

# --- LLM on Groq (Qwen3-32B) ---
llm = LLM(
    model="qwen/qwen3-32b",
    provider="groq",
    api_key=GROQ_API2,
    max_tokens=8192,
)

# --- RAG Tool configured to Groq as well (no Google deps) ---
config = {
    "llm": {
        "provider": "groq",
        "config": {
            "model": "qwen/qwen3-32b",
            "api_key": GROQ_API2,
        },
    },
    "embedding_model": {
        "provider": "ollama",
        "config": {"model": "all-minilm:latest"},
    },
}

rag_tool = None
try:
    rag_tool = RagTool(config=config)
    pdf_path = Path("./data/topomapsymbols.pdf")
    if pdf_path.exists():
        rag_tool.add(str(pdf_path), data_type="pdf_file")
    else:
        logger.info("RAG: ./data/topomapsymbols.pdf not found; continuing without it.")
except Exception as e:
    logger.warning("RAG tool init failed; continuing without RAG. %s", e)

# --- Agent ---
gis_agent = Agent(
    role="Fantasy GIS Cartographer",
    goal="Convert lore into terrain, faction regions, and conflict zones for mapping",
    backstory="You translate worldbuilding JSON into GIS-ready structures.",
    llm=llm,
    verbose=True,
    allow_delegation=False,
    )

# FIXED: missing comma before "notes"
JSON_SCHEMA = """{
  "terrain_features": ["name (type)"],
  "faction_regions": ["faction: region"],
  "conflict_zones": ["location: conflict"],
  "background": "Pick from: snowy, forest, desert, beach, urban, ship, halo-reach-map",
  "notes": "1–2 sentence summary of how terrain, factions, and conflict interrelate"
}"""

PROMPT_TMPL = """You are GIS Weaver.

Transform the structured worldbuilding JSON below into a GIS-friendly format.
In addition to terrain, faction zones, and conflicts, also choose a suitable background map type.

Choose from the following backgrounds: snowy, forest, desert, beach, urban, ship, halo-reach-map.
Pick the background that best matches the biome or dominant setting described in the lore.

STRICT OUTPUT RULES:
- Respond with ONLY a JSON object matching the schema (no prose, no code fences).
- Do not include comments.
- Ensure valid JSON (double quotes, commas, etc).
- Use simple strings, not nested objects.

Input:
{lore}

Respond EXACTLY in this JSON:

{schema}
"""

server = Server()

def _extract_json_block(text: str) -> tuple[dict | None, str | None]:
    """Try to parse first JSON object in text. Returns (parsed, raw_json_fragment)."""
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        try:
            return json.loads(t), t
        except Exception:
            pass
    m = re.search(r"\{(?:[^{}]|(?R))*\}", text, flags=re.DOTALL)
    if m:
        frag = m.group(0)
        try:
            return json.loads(frag), frag
        except Exception:
            return None, frag
    return None, None

@server.agent(name="gis_weaver")
async def gis_weaver(
        input: list[Message],
        context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Transforms lore input into GIS-style cartographic JSON using Groq Qwen3-32B."""
    lore = input[0].parts[0].content.strip()
    prompt = PROMPT_TMPL.format(lore=lore, schema=JSON_SCHEMA)

    task = Task(
        description=prompt,
        expected_output="JSON with keys: terrain_features, faction_regions, conflict_zones, background, notes",
        agent=gis_agent,
    )
    crew = Crew(agents=[gis_agent], tasks=[task], verbose=True)

    try:
        result = await crew.kickoff_async()
    except Exception as e:
        error = {
            "error": "LLM or Crew execution failed",
            "exception": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        yield Message(parts=[MessagePart(content=json.dumps(error, indent=2))])
        return

    # get raw model output (CrewAI object can vary)
    raw_out = None
    for attr in ("raw", "text", "final_output", "output", "agent_output"):
        if hasattr(result, attr) and getattr(result, attr):
            raw_out = str(getattr(result, attr))
            break
    if raw_out is None:
        raw_out = str(result)

    parsed, frag = _extract_json_block(raw_out)
    if parsed is not None:
        # validate keys
        required = {"terrain_features", "faction_regions", "conflict_zones", "background", "notes"}
        missing = sorted(list(required - set(parsed.keys())))
        if missing:
            parsed = {"error": f"Missing required keys: {missing}", "raw": parsed}
        yield Message(parts=[MessagePart(content=json.dumps(parsed, indent=2))])
        return

    diagnostics = {
        "error": "Invalid or no JSON found in model output",
        "regex_fragment": frag,
        "full_output_tail": raw_out[-2000:],
        "hint": "Ensure schema commas/quotes are correct and reply with JSON only.",
    }
    yield Message(parts=[MessagePart(content=json.dumps(diagnostics, indent=2))])

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8001)
