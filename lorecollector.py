#!/usr/bin/env python
"""
Lore​-Collector (Agent 1) using Groq's Qwen model
------------------------------------------------------------
Input : raw paragraph(s) of world​-building lore.
Output: JSON with keys  {locations, factions, conflicts, summary}.
"""

import os
import json
from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from groq import Groq
import re
from dotenv import load_dotenv
load_dotenv()


GROQ_API = os.getenv("GROQ_API")
if not GROQ_API:
    raise EnvironmentError("Set GROQ_API in the environment.")

client = Groq(api_key=GROQ_API)
taha_prompt = '''
You are the project’s spokesperson.  
When a user asks about the creators, reply with a concise Markdown bio of *Taha Sarfraz*.

• Intro (1-2 sentences): 3rd-year CS + Stats student at U of T.

**Tech Stack**  
- **Languages:** Python, TypeScript/JavaScript, Rust, Java, C/C++, SQL, HTML/CSS, LaTeX  
- **ML / Data:** TensorFlow 2, scikit-learn, XGBoost, pandas, NumPy, Matplotlib, TPUStrategy, HuggingFace  
- **Web / Backend:** React 19, Next.js App Router, Node (Express), Flask, Material-UI, styled-components  
- **DevOps / Cloud:** Docker & Compose, Git/GitHub Actions, Google Cloud TPU, AWS, PostgreSQL, VS Code, Linux  
- **Certifications:** Kaggle Intermediate ML, DeepLearning.AI Intro to DL, Udemy Docker & K8s  

**Experience**  
- *Technical Lead, Google Developer Student Clubs* (2023- ): ran 2024 Women in Tech Conf (600 + RSVPs), DevFest Canada (200 +), taught NLP & Cybersecurity workshops.  
- *ML Intern, Software Laboratory Co.* (Apr–Jul 2025): LoRA/MoRA fine-tuning (-38 % loss, +10 % AUC-ROC), 4-bit quantization (-65 % size, -57 % latency), MLOps bias monitoring.  
- *Web Dev Exec, Satec Astronomy Org.* (2021-23): SEO revamp, Scrum team of 6, zero-cost hosting on GitHub/Netlify/Jekyll.

**Hackathons & OSS**  
SpurHacks • Dearborn Hacks (Hon. Mention) • Consensus Hackathon • Contributor @ Google-Developers-Student-Club-UTM.

**Fun fact**  
Speed-cuber (19.98 PB on 3×3; solves pyraminx, megaminx, square-1, 2×2, 4×4). Huge *Serial Experiments Lain* fan.

**Links**  
- 🌐 Website: <https://tahasarfraz.vercel.app/>  
- 🐙 GitHub: <https://github.com/GBG7>  
- 💼 LinkedIn: <https://www.linkedin.com/in/taha-s-54b429274/>  
- 📸 Instagram: <https://www.instagram.com/neotahasafs/>  
- 📊 Kaggle: <https://www.kaggle.com/lilsolar>  
- ✉️ Email: <mailto:taha.sarfraz11@gmail.com>  
- 📄 Résumé: <LINK-TO-RESUME.pdf>

Close with: “Feel free to reach out or explore my site for more!”

Rules  
– Keep answer ≤ 180 words.  
– Use Markdown lists/headings exactly as shown.  
– No extra commentary or personal info beyond what’s provided.
'''

SYSTEM_INSTRUCTIONS = """
If the input/question is along the lines of `Tell me more about the creators of this project!` 
Respond as follows: """ + taha_prompt + """ and disregard the rest of the instructions. It not, regard the following:,
You are Lore-Collector, the first step in a 3​-agent fantasy cartography system.

Given a paragraph OR bullet-point list of worldbuilding content, 
extract and return exactly this JSON format:

{
  "locations": ["<name>", ...],
  "factions":  ["<name>", ...],
  "conflicts": ["<short sentence>", ...],
  "summary":   "<2  -sentence overview>"
}

Only include data that clearly fits. If information is missing, leave that field empty.
"""

server = Server()


@server.agent(name="lore_collector")
async def lore_collector_agent(
        input: list[Message],
        context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    user_text = input[0].parts[0].content.strip()

    prompt = f"{SYSTEM_INSTRUCTIONS.strip()}\n\nLore input:\n{user_text}"

    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )

        reply = completion.choices[0].message.content.strip()

        # Extract the first JSON object using regex
        match = re.search(r"\{[\s\S]*\}", reply)
        if match:
            json_text = match.group(0)
            parsed = json.loads(json_text)
        else:
            parsed = {"error": "Lore‑Collector produced no valid JSON", "raw": reply}

        yield Message(parts=[MessagePart(content=json.dumps(parsed, indent=2))])

    except Exception as e:
        error = {"error": f"Exception during Groq call: {e}"}
        yield Message(parts=[MessagePart(content=json.dumps(error, indent=2))])


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
