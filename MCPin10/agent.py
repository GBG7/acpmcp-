#!/usr/bin/env python
"""
MapRender (Agent 3) using Groq's Qwen model and PIL for compositing over background
------------------------------------------------------------------------------------
Input : JSON block with locations, terrain, factions, conflicts, and summary.
Output: Saved map image (PNG path) or raw SVG.
"""

import os
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from groq import Groq
from PIL import Image, ImageDraw, ImageColor
from colorama import Fore
from dotenv import load_dotenv
import os
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "1"
os.environ["CREWAI_TELEMETRY_DISABLED"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"
os.environ["OTEL_LOGS_EXPORTER"] = "none"

load_dotenv()


API_KEY = os.getenv("GROQ_API")
MODEL_ID = "qwen/qwen3-32b"
BACKGROUND_IMAGE = "data/halo-reach-map.png"
FINAL_IMAGE = "final_map.png"

if not API_KEY:
    raise EnvironmentError("Missing GROQ_API key.")

client = Groq(api_key=API_KEY)
server = Server()

# Prompt Template 
reach_coords = """
"locations": [
  {"name": "New Alexandria", "x": 370, "y": 290},
  {"name": "Sword Base", "x": 670, "y": 90},
  {"name": "Visgrad Relay", "x": 400, "y": 370},
  {"name": "Aszod shipbreaking yards", "x": 210, "y": 480},
  {"name": "Szurdok Ridge", "x": 640, "y": 320},
  {"name": "Spire", "x": 450, "y": 430},
  {"name": "Winter Contingency Zone", "x": 490, "y": 390}
],
"""
beach_coords = """
"locations": [
  { "name": "Beach Landing", "x": 650, "y": 480 },
  { "name": "First Covenant Base", "x": 230, "y": 200 },
  { "name": "Undoor Forerunner Complex", "x": 360, "y": 300 },
  { "name": "Secondary Beach", "x": 680, "y": 570 }
]
"""
map_coords = reach_coords


# BASE_PROMPT = """You are a fantasy cartographer. Generate ONLY valid SVG markup (<svg>…</svg>) for a map based on the JSON below.
# • No markdown.  • No commentary.  • NO <think> sections.
#
# The canvas is 800 × 600.
#
# Indicate:
# - Faction regions: <circle>  r=100  opacity=0.20   fill blue/red/yellow.
# - Conflict rings: <circle>  r=125  stroke="red" fill="none" stroke-width="3".
#
# - **Terrain / location labels**
#   · Draw a small black pin <circle>.
#   · Right beside it, draw a semi-transparent black <rect> (opacity = 0.6) **behind** the label.
#   · Label text: <text font-size="14" font-family="serif" fill="white" stroke="black" stroke-width="0.8">.
#     (White letters + thin black outline = readable everywhere.)
#
# - **Legend (top-right)**
#   · White background <rect>.
#   · 20 × 20 colour swatches.
#   · Each swatch label uses the same white-text / black-stroke style.
#   · Font-size 14 px, font-family serif.
#
# - **Summary (bottom)**
#   · Wrap in <g id="summary" transform="translate(400,585)"> so x = 0 is the centre.
#   · Add a white background <rect x="-400" y="-15" width="800" height="60"/>.
#   · For each line do:
#         <text y="0" text-anchor="middle" font-size="14" font-family="serif" fill="black">Line 1</text>
#         <text y="22" …>Line 2</text>
#     (i.e. use y offsets 0, 22, 44 …)
#
# General rules:
# - Every label gets its own contrast rect. No plain black text on map.
# - Use absolute x/y; no percentages, CSS or <style>.
# - No HTML/foreignObject.
#
# Use these coordinates:
# "locations": [
#   {"name": "New Alexandria",        "x": 370, "y": 290},
#   {"name": "Sword Base",            "x": 670, "y":  90},
#   {"name": "Visgrad Relay",         "x": 400, "y": 370},
#   {"name": "Aszod shipbreaking yards","x": 210, "y": 480},
#   {"name": "Szurdok Ridge",         "x": 640, "y": 320},
#   {"name": "Spire",                 "x": 450, "y": 430},
#   {"name": "Winter Contingency Zone","x": 490, "y": 390}
# ],
#
# JSON:
# """

# BASE_PROMPT = """You are a fantasy cartographer. Output ONLY valid SVG (<svg>…</svg>).
# No markdown · No commentary · NO <think> blocks.
#
# Canvas: 800 × 600.
#
# ────────────────────────────────────────
# REGIONS & CONFLICTS
# ────────────────────────────────────────
# • Faction area  <circle r="100" fill="blue|red|yellow" opacity="0.2"/>
# • Conflict ring <circle r="125" stroke="red" fill="none" stroke-width="3"/>
#
# ────────────────────────────────────────
# LOCATION PINS & LABELS   — ALL 7 REQUIRED
# ────────────────────────────────────────
# For every item in the “locations” list:
# 1. Draw a small pin  <circle r="4" fill="black"/>
# 2. Immediately right of the pin create a label group:
#    <g>
#      <rect fill="black" opacity="0.6" x? y? width? height?/>     <!-- contrast bg -->
#      <text font-family="serif" font-size="14" fill="white" stroke="black" stroke-width="0.8">Name</text>
#    </g>
#    If the name is longer than 18 characters, reduce font-size to 12.
# 3. **Do NOT omit any label.**
#
# ────────────────────────────────────────
# LEGEND   (top-right)
# ────────────────────────────────────────
# <g id="legend" transform="translate(630,20)">
#   <!-- draw background FIRST so everything else sits on top -->
#   <rect x="0" y="0" width="150" height="100" fill="white" stroke="black"/>
#
#   <!-- row 1 -->
#   <g transform="translate(10,10)">
#     <rect width="20" height="20" fill="blue"/>
#     <text x="30" y="15" dominant-baseline="middle"
#           font-family="serif" font-size="14"
#           fill="white" stroke="black" stroke-width="0.8">
#       UNSC
#     </text>
#   </g>
#
#   <!-- row 2 -->
#   <g transform="translate(10,40)">
#     <rect width="20" height="20" fill="red"/>
#     <text x="30" y="15" dominant-baseline="middle"
#           font-family="serif" font-size="14"
#           fill="white" stroke="black" stroke-width="0.8">
#       Covenant
#     </text>
#   </g>
#
#   <!-- row 3 -->
#   <g transform="translate(10,70)">
#     <rect width="20" height="20" fill="yellow"/>
#     <text x="30" y="15" dominant-baseline="middle"
#           font-family="serif" font-size="14"
#           fill="white" stroke="black" stroke-width="0.8">
#       Civilians
#     </text>
#   </g>
# </g>
#
# ────────────────────────────────────────
# SUMMARY   (always bottom-centre)
# ────────────────────────────────────────
# <g id="summary" transform="translate(400,570)">
#   <rect x="-400" y="-20" width="800" height="70" fill="white"/>
#   <!-- 2–3 short sentences, manually wrapped -->
#   <text y="0"  text-anchor="middle" font-size="14" font-family="serif" fill="black">Line 1…</text>
#   <text y="22" text-anchor="middle" font-size="14" font-family="serif" fill="black">Line 2…</text>
#   <!-- add <text y="44">…</text> only if a 3rd line is needed -->
# </g>
#
# ────────────────────────────────────────
# RULES
# ────────────────────────────────────────
# • No element may be skipped: all seven labels, all three legend rows, and the summary must appear.
# • Use absolute x/y numbers – no %, CSS, <style>, or <foreignObject>.
# • Output must be a single <svg>…</svg> block.
#
# Use these coordinates exactly:
# "locations": [
#   {"name": "New Alexandria",          "x": 370, "y": 290},
#   {"name": "Sword Base",              "x": 670, "y":  90},
#   {"name": "Visgrad Relay",           "x": 400, "y": 370},
#   {"name": "Aszod shipbreaking yards","x": 210, "y": 480},
#   {"name": "Szurdok Ridge",           "x": 640, "y": 320},
#   {"name": "Spire",                   "x": 450, "y": 430},
#   {"name": "Winter Contingency Zone", "x": 490, "y": 390}
# ],
#
# JSON:
# """


def parse_svg_float(val: str, default: float = 0.0) -> float:
    try:
        if val.endswith('%'):
            return 800 * float(val.rstrip('%')) / 100
        return float(val)
    except Exception:
        return default


def pick_background(json_str: str) -> str:
    """
    Extracts the second JSON block from a string and returns the background image path.
    """
    try:
        # Grab the second JSON object
        match = re.findall(r'\{[\s\S]*?\}', json_str)
        if match and len(match) >= 2:
            data = json.loads(match[1])  # second JSON block
            bg_key = (data.get("background") or "").strip().lower()
            if bg_key:
                cand = Path("data") / f"{bg_key}.png"
                if cand.exists():
                    return str(cand)
    except Exception as e:
        print(Fore.RED + "[pick_background] Failed: {e}" + Fore.RESET)

    return BACKGROUND_IMAGE  # fallback to halo-reach-map.png


def apply_opacity(hex_color: str, opacity: float) -> tuple:
    try:
        rgb = ImageColor.getrgb(hex_color)
        return (*rgb, int(255 * opacity))
    except Exception:
        return None

# ACP Tool Handler 
@server.agent(name="render_map")
async def render_map(
        input: list[Message],
        context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    data = input[0].parts[0].content.strip()
    chosen_bg = pick_background(data)
    print(Fore.LIGHTCYAN_EX + chosen_bg + Fore.RESET)
    if "beach" in chosen_bg:
        map_coords = beach_coords
    else:
        map_coords = reach_coords
    BASE_PROMPT = f"""You are a fantasy cartographer. Generate ONLY valid SVG markup (<svg>…</svg>) for a map based on the 
    JSON below.
    • No markdown.
    • No commentary.
    • NO <think> sections.

    Each location must be placed at the given x,y coordinates on an 800x600 map.

    Indicate:
    - Faction regions as shaded: blue (UNSC), red (Covenant), yellow (Civilians)
      - Use <circle> radius 100 and opacity 0.2 for visibility.

    - Conflict zones with a red ring (stroke only), radius 125.

    - Terrain features:
      - Use a small black pin (<circle> with fill="black")
      - Add a visible label next to each pin using a <text> tag.
      - Use <text> with font-size="18px", font-family="serif", fill="white".

    - Add a visible legend in the top-right corner:
      - Use a white <rect> for background.
      - Add color swatches as <rect> (20x20) with blue/red/yellow fill.
      - Each swatch should have a label beside it using <text>.
      - Add a white <rect> behind each <text> label for visibility.
      - Legend text must use <text> with font-size="14px", fill="black", font-family="serif".

    - At the bottom of the SVG, include a multi-line summary.
      - Wrap the summary block inside a <g> group.
      - Draw a white <rect> behind the summary text block (spanning 100% width if needed).
      - Use <text> elements inside the <g> with x="400" and text-anchor="middle" to center-align.
      - Use font-size="14px", font-family="serif", fill="black".
      - Split long lines into separate <text> lines (e.g., <text y="590">...</text> and <text y="610">...</text>).

    General rules:
    - All text must use <text> tags, not HTML or foreignObject.
    - Always position elements using absolute x/y (not percentages or CSS).
    - Do NOT use <style> blocks, classes, or external stylesheets.

    Use these coordinates:
    {map_coords}

    JSON:
    """

    # try:
    #     data = json.loads(json_input)
    # except Exception as e:
    #     yield Message(parts=[MessagePart(content=f"Error: invalid JSON payload: {e}")])
    #     return

    full_prompt = BASE_PROMPT + data
    # print(full_prompt, flush=True)
    # print(type(full_prompt), flush=True)
    # pick background based on JSON field

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.9,
            max_completion_tokens=10000,
            top_p=0.8,
            stream=True,
        )
        raw_text = "".join(chunk.choices[0].delta.content or "" for chunk in response)

        # Strip <think> blocks and clean
        raw_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE)
        raw_text = raw_text[raw_text.find("<svg"):] if "<svg" in raw_text else raw_text

        # Extract SVG block
        match = re.search(r"<svg[\s\S]*?</svg>", raw_text, re.IGNORECASE)
        svg_markup = match.group(0) if match else ""

        if not svg_markup:
            yield Message(parts=[MessagePart(content="Error: no <svg> block found")])
            return

        if "xmlns" not in svg_markup.split("\n", 1)[0]:
            svg_markup = svg_markup.replace("<svg", "<svg xmlns='http://www.w3.org/2000/svg'", 1)

        # Parse SVG
        try:
            root = ET.fromstring(svg_markup)
        except ET.ParseError as e:
            yield Message(parts=[MessagePart(content=f"Error: malformed SVG: {e}")])
            return
        # ─── draw overlay ──────────────────────────────────────────────
        overlay = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
        canvas = ImageDraw.Draw(overlay)

        # simple transform stack; only handles nested translate(x,y)
        tx_stack = [(0.0, 0.0)]

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]

            # ── track <g transform="translate(x,y)"> ───────────
            if tag == 'g':
                # entering a group
                tr = elem.attrib.get("transform", "")
                if tr.startswith("translate"):
                    nums = re.findall(r"[-+]?[0-9]*\\.?[0-9]+", tr)
                    dx, dy = map(float, nums[:2] or [0, 0])
                else:
                    dx, dy = 0.0, 0.0
                parent_dx, parent_dy = tx_stack[-1]
                tx_stack.append((parent_dx + dx, parent_dy + dy))
                continue
            elif tag == '/g':  # Pillow doesn't give closing tags; ignored
                tx_stack.pop()
                continue

            dx, dy = tx_stack[-1]  # current offset

            fill = elem.attrib.get("fill")
            stroke = elem.attrib.get("stroke")
            stroke_w = int(parse_svg_float(elem.attrib.get("stroke-width", "1")))
            opacity = float(elem.attrib.get("opacity", "1.0"))

            if fill == "none":
                fill = None
            else:
                fill = apply_opacity(fill, opacity)

            if stroke == "none":
                stroke = None

            try:
                if tag == "rect":
                    x = dx + parse_svg_float(elem.attrib.get("x", "0"))
                    y = dy + parse_svg_float(elem.attrib.get("y", "0"))
                    w = parse_svg_float(elem.attrib.get("width", "0"))
                    h = parse_svg_float(elem.attrib.get("height", "0"))
                    canvas.rectangle([x, y, x + w, y + h], fill=fill, outline=stroke, width=stroke_w)

                elif tag == "circle":
                    cx = dx + parse_svg_float(elem.attrib.get("cx", "0"))
                    cy = dy + parse_svg_float(elem.attrib.get("cy", "0"))
                    r = parse_svg_float(elem.attrib.get("r", "0"))
                    canvas.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=stroke, width=stroke_w)

                elif tag == "polygon":
                    pts = [(dx + parse_svg_float(xx), dy + parse_svg_float(yy))
                           for xx, yy in (p.split(',') for p in elem.attrib.get("points", "").split() if ',' in p)]
                    canvas.polygon(pts, fill=fill, outline=stroke)

                elif tag == "text":
                    x = dx + parse_svg_float(elem.attrib.get("x", "0"))
                    y = dy + parse_svg_float(elem.attrib.get("y", "0"))
                    text_content = elem.text or ""
                    font_color = fill or (0, 0, 0, 255)
                    canvas.text((x, y), text_content,
                                fill=font_color,
                                stroke_width=stroke_w if stroke else 0,
                                stroke_fill=stroke if stroke else None)

            except Exception:
                continue

        # Composite on a background
        try:
            try:
                bg = Image.open(chosen_bg).convert("RGBA")
            except FileNotFoundError:
                bg = Image.open(BACKGROUND_IMAGE).convert("RGBA")  # fallback to halo-reach-map.png
            print(Fore.YELLOW + f"[BG LOADED] Using background image: {chosen_bg}" + Fore.RESET)
            overlay = overlay.resize(bg.size)
            result = Image.alpha_composite(bg, overlay)
            result.save(FINAL_IMAGE)
            yield Message(parts=[MessagePart(content=str(Path(FINAL_IMAGE).resolve()))])
        except FileNotFoundError:
            yield Message(parts=[MessagePart(content=f"Error: Background '{BACKGROUND_IMAGE}' not found")])

    except Exception as e:
        yield Message(parts=[MessagePart(content=f"Error: exception during rendering: {e}")])



if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8002)
