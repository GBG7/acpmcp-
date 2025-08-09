import re
import webbrowser
from pathlib import Path
from groq import Groq
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageColor
from dotenv import load_dotenv
load_dotenv()


# -- Configuration ----------------------------------------------------------
API_KEY = os.getenv("GROQ_API")
MODEL_ID = "qwen/qwen3-32b"
SVG_FILE = "triangle.svg"
FINAL_IMAGE = "final_map.png"
BACKGROUND_IMAGE = "data/halo-reach-map.png"  # ensure this exists

PROMPT = (
    """You are a fantasy cartographer. Generate **ONLY** valid SVG markup (<svg>…</svg>) for a map based on the JSON below.  
    • No markdown.  
    • No commentary.  
    • NO <think> sections.  

    Each location must be placed at the given x,y coordinates on an 800x600 map.
    Indicate:
    - Faction regions as shaded: blue (UNSC), red (Covenant), yellow (Civilians) 
      - Use radius 100 and opacity 0.2 for visibility
    - Conflict zones with red ring, radius 125
    - Terrain features with small black pin and label
    - Add a visible legend with color swatches and labeled text (include text beside each swatch!)
    - Print summary text at the bottom of the SVG

    JSON:
    {
      "locations": [
        {"name": "New Alexandria", "x": 370, "y": 290},
        {"name": "Sword Base", "x": 670, "y": 90},
        {"name": "Visgrad Relay", "x": 400, "y": 370},
        {"name": "Aszod shipbreaking yards", "x": 210, "y": 480},
        {"name": "Szurdok Ridge", "x": 640, "y": 320},
        {"name": "Spire", "x": 450, "y": 430},
        {"name": "Winter Contingency Zone", "x": 490, "y": 390}
      ],
      "terrain_features": [
        "New Alexandria (Urban)", "Sword Base (Military Base)", "Visgrad Relay (Communication Hub)",
        "Aszod shipbreaking yards (Industrial)", "Szurdok Ridge (Mountainous)", "Spire (Landmark/Fortification)",
        "Winter Contingency Zone (Rural/Defensive Perimeter)"
      ],
      "faction_regions": [
        "UNSC: New Alexandria, Sword Base",
        "Covenant: Aszod shipbreaking yards, Szurdok Ridge",
        "Civilians: New Alexandria, Visgrad Relay"
      ],
      "conflict_zones": [
        "New Alexandria", "Sword Base", "Szurdok Ridge", "Aszod shipbreaking yards", "Spire", "Winter Contingency Zone"
      ],
      "summary": "The fall of Reach in 2552 depicts a brutal Covenant invasion across key locations. Noble Six's sacrifice ensures the Pillar of Autumn's escape, marking the beginning of the Halo saga."
    }
    """
)

# ---------------------------------------------------------------------------
client = Groq(api_key=API_KEY)
completion = client.chat.completions.create(
    model=MODEL_ID,
    messages=[{"role": "user", "content": PROMPT}],
    temperature=0.9,
    max_completion_tokens=10000,
    top_p=0.8,
    reasoning_effort="default",
    stream=True,
)

# -- 1. Collect streamed response ------------------------------------------
raw_text = "".join(chunk.choices[0].delta.content or "" for chunk in completion)

# -- 2. Strip <think> blocks & prefix garbage -------------------------------
raw_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE)
if "<svg" in raw_text:
    raw_text = raw_text[raw_text.find("<svg"):]

# -- 3. Extract SVG block ---------------------------------------------------
match = re.search(r"<svg[\s\S]*?</svg>", raw_text, re.IGNORECASE)
svg_markup = match.group(0) if match else ""

if not svg_markup:
    print("❌ No <svg> block found. Falling back.")
    svg_markup = """
    <svg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'>
      <polygon points='100,10 40,190 160,190' fill='#0077cc' stroke='black' stroke-width='3'/>
    </svg>"""

# Guarantee xmlns attribute
if "xmlns" not in svg_markup.split("\n", 1)[0]:
    svg_markup = svg_markup.replace("<svg", "<svg xmlns='http://www.w3.org/2000/svg'", 1)
print(raw_text)
# -- 4. Parse SVG; fallback if malformed ------------------------------------
try:
    root = ET.fromstring(svg_markup)
except ET.ParseError as e:
    print(f"Malformed SVG ({e}). Using fallback triangle.")
    svg_markup = """
    <svg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'>
      <polygon points='100,10 40,190 160,190' fill='#0077cc' stroke='black' stroke-width='3'/>
    </svg>"""
    root = ET.fromstring(svg_markup)


# -- 5. Helper for percentages ---------------------------------------------
def parse_svg_float(val: str, default: float = 0.0) -> float:
    try:
        if val.endswith('%'):
            return 800 * float(val.rstrip('%')) / 100
        return float(val)
    except Exception:
        return default


def apply_opacity(hex_color: str, opacity: float) -> tuple:
    try:
        rgb = ImageColor.getrgb(hex_color)
        return (*rgb, int(255 * opacity))
    except Exception:
        return None


# -- 6. Rasterise simple shapes onto Pillow ---------------------------------
overlay = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
canvas = ImageDraw.Draw(overlay)

for elem in root.iter():
    tag = elem.tag.split('}')[-1]
    style = elem.attrib.get('style', '')
    fill = elem.attrib.get('fill')
    stroke = elem.attrib.get('stroke')
    stroke_w = int(parse_svg_float(elem.attrib.get('stroke-width', '1')))
    opacity = float(elem.attrib.get('opacity', '1.0'))

    if fill == 'none':
        fill = None
    else:
        fill = apply_opacity(fill, opacity)

    if stroke == 'none':
        stroke = None

    try:
        if tag == 'rect':
            x = parse_svg_float(elem.attrib.get('x', '0'))
            y = parse_svg_float(elem.attrib.get('y', '0'))
            w = parse_svg_float(elem.attrib.get('width', '0'))
            h = parse_svg_float(elem.attrib.get('height', '0'))
            canvas.rectangle([x, y, x + w, y + h], fill=fill, outline=stroke, width=stroke_w)
        elif tag == 'circle':
            cx = parse_svg_float(elem.attrib.get('cx', '0'))
            cy = parse_svg_float(elem.attrib.get('cy', '0'))
            r = parse_svg_float(elem.attrib.get('r', '0'))
            canvas.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=stroke, width=stroke_w)
        elif tag == 'polygon':
            pts = [(parse_svg_float(x), parse_svg_float(y)) for x, y in
                   (p.split(',') for p in elem.attrib.get('points', '').split() if ',' in p)]
            canvas.polygon(pts, fill=fill, outline=stroke)
    except ValueError as ve:
        print(f"Skipping element due to error: {ve}")
        continue

# -- 7. Composite on background --------------------------------------------
try:
    bg = Image.open(BACKGROUND_IMAGE).convert('RGBA')
    overlay = overlay.resize(bg.size)
    result = Image.alpha_composite(bg, overlay)
    result.save(FINAL_IMAGE)
    print(f"✅ Saved {FINAL_IMAGE}")
    webbrowser.open(Path(FINAL_IMAGE).resolve().as_uri())
except FileNotFoundError:
    print(f"❌ Background '{BACKGROUND_IMAGE}' not found.")
