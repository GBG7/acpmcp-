# LilSolarAI: The Silent Cartographer

> **Multi-agentic AI system that crafts fantasy maps from your prompts.**

[![Docker Pulls](https://img.shields.io/docker/pulls/gbg7/lilsolarai)](https://hub.docker.com/u/gbg7)
[![AWS EC2 Hosted](https://img.shields.io/badge/Hosted%20on-AWS%20EC2-blue)](https://aws.amazon.com/ec2/)
[![Frontend](https://img.shields.io/badge/Frontend-React%2FTS-green)](https://react.dev/)
[![CrewAI](https://img.shields.io/badge/Agent%20Framework-crew%20ai-red)](https://www.crewai.com/)

---

LilSolarAI is a multi-agent AI system that dynamically generates fantasy maps based on user prompts. Combining three powerful LLMs, advanced prompt engineering, and a modular agentic architecture, it delivers beautiful, lore-rich maps tailored to your imagination.

## Features

- **Multi-agentic LLM system**:  
  Three large language models (LLMs) communicate via ACP (Agent Communication Protocol) and use MCP (Map Coordination Protocol) to coordinate map generation.
- **ACP for inter-agent messaging**:  
  LLMs exchange context, instructions, and roles through the ACP protocol.
- **MCP for tool selection**:  
  Agents utilize MCP to choose the best map template/tool, improving background selection and map coherence.
- **RAG Tool AI**:  
  Retrieval-Augmented Generation (RAG) tool enables intelligent template finding and info gathering.
- **LLM Integrations**:  
  Integrated with Qwen3-32b and Gemini 1.5 Pro APIs for advanced reasoning and creativity.
- **WebSocket Server**:  
  Serves both frontend (React/TypeScript) and backend, enabling real-time communication.
- **Frontend**:  
  Modern UI built with React & TypeScript, served via WebSocket.
- **Dockerized & Cloud Hosted**:  
  Fully containerized—deployable via Docker Compose. Hosted on AWS EC2 with custom domain.
- **CrewAI Framework**:  
  Orchestrates agent roles, prompt engineering, and fine-tuning for each LLM agent.
- **SDKs**:  
  Uses `acp_sdk` and `mcp_sdk` for agent communication and tool orchestration.
- **Agent3 Advanced Rendering**:  
  Uses Pillow, Colorama, and SVG markup to draw on backgrounds and templates.

---

## Architecture

```mermaid
graph TD
    A[Frontend: React/TS] -- websocket --> B[WebSocket Server]
    B --> C[Agent 1: Lore Weaver (LLM)]
    C --> D[Agent 2: Background Selector (LLM)]
    D --> E[Agent 3: Map Drawer (LLM)]
    E --> F[Image Output]
    D --> G[MCP/RAG Template Search]
    E --> H[Pillow/Colorama/SVG]
```

- **Frontend UI**:  
  - Built with React/TypeScript.  
  - Input field sends user prompt to backend via WebSocket.
- **Agent 1 (Lore Weaver)**:  
  - Extracts lore and key details from user input.
- **Agent 2 (Background Selector)**:  
  - Determines map background, gathers details with MCP tools, outputs structure in JSON.
- **Agent 3 (Map Drawer)**:  
  - Selects background template via MCP/RAG, draws map elements using Pillow, Colorama, and SVG markup.
- **Communication**:  
  - ACP for agent messaging, MCP for tool choices and template selection.
- **Hosting**:  
  - Dockerized for easy deployment; hosted on AWS EC2 with custom domain.

---

## Technologies Used

- **LLMs**: Qwen3-32b, Gemini 1.5 Pro (API calls)
- **Agent Orchestration**: CrewAI, acp_sdk, mcp_sdk
- **Frontend**: React, TypeScript
- **Backend**: WebSocket server
- **Rendering**: Pillow, Colorama, SVG
- **DevOps**: Docker, Docker Compose, AWS EC2
- **Template Search**: RAG tool AI

---

## How to Run

1. **Pull the Docker images**  
   ```bash
   docker compose pull
   ```
2. **Start the stack**  
   *(replace `<service>` with the actual service name if needed)*
   ```bash
   docker compose up
   ```
   Or, for detached mode:
   ```bash
   docker compose up -d
   ```
3. **Access the app**  
   Visit your AWS EC2 instance at your custom domain.

> **Note:** Images are hosted at [Docker Hub - gbg7](https://hub.docker.com/u/gbg7)

---

## API & Agent Details

- **Agent 1: Lore Weaver**  
  - Receives prompt from frontend, extracts story and world-building elements.
- **Agent 2: Background Selector**  
  - Uses MCP/RAG tools to search for relevant background templates, outputs JSON.
- **Agent 3: Map Drawer**  
  - Selects template, draws map features with Pillow, Colorama, and SVG markup.

---

## Prompt Engineering

- Each agent role is fine-tuned with custom prompt instructions.
- Ensures clarity, separation of duties, and optimal use of LLM capabilities.

---

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT

---

## Credits

- Qwen3-32b, Gemini 1.5 Pro
- CrewAI
- acp_sdk, mcp_sdk
- Pillow, Colorama

---

## TODO / Roadmap

- [ ] Add automated tests
- [ ] Improve frontend styling
- [ ] Add more map templates
- [ ] Integrate additional LLMs

---

## Contact

Questions or feedback? Open an [issue](https://github.com/GBG7/acpmcp-/issues) or email <your-email-here>.
