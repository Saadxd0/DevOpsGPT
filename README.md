<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Vite-8-646CFF?style=for-the-badge&logo=vite&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini_AI-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
</p>

<h1 align="center">⚡ DevOpsGPT</h1>

<p align="center">
  <b>AI-Powered Infrastructure Operations Copilot</b><br/>
  <sub>Inspect your stack · Troubleshoot faster · Get clear operational guidance</sub>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-cicd-pipeline">CI/CD</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 🎯 What is DevOpsGPT?

DevOpsGPT is an **intelligent DevOps assistant** that turns complex infrastructure questions into concise, actionable answers. It uses a multi-agent graph architecture powered by **Google Gemini AI** and **LangGraph** to route queries to specialized agents — each responsible for a different domain of your infrastructure.

Ask it about Docker containers, Kubernetes clusters, Git histories, Terraform state, or system resources — and it responds with **real-time data** from your actual environment.

> **Human-in-the-Loop Safety:** Destructive operations (delete, stop, create) require explicit user approval before execution.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🤖 Intelligent Agent Routing
A supervisor node classifies every query and routes it to the right specialist agent — no manual selection needed.

### 🐳 Docker Management
Query running containers, images, networks, and volumes. Create, stop, or remove containers with approval.

### ☸️ Kubernetes Insights
Inspect pods, services, and deployments across your cluster with natural language.

### 🧱 Terraform State
Validate infrastructure blueprints and inspect plan state directly from conversation.

</td>
<td width="50%">

### 🔒 Security-First Execution
Every command is validated against an allowlist, blocklist, and dangerous-pattern scanner before execution.

### 🛑 Human-in-the-Loop (HITL)
Mutations require explicit approval — the AI drafts the command, you confirm before it runs.

### 🐙 Git Intelligence
Analyze revision history, branches, and commit logs through conversational queries.

### 🖥️ System Diagnostics
Get real-time CPU, memory, disk, and process information from your infrastructure.

</td>
</tr>
</table>

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│              Vite • Lucide Icons • React Markdown               │
└──────────────────────────┬──────────────────────────────────────┘
                           │  POST /api/v1/chat
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   LangGraph State Machine                 │   │
│  │                                                          │   │
│  │   ┌────────────┐                                         │   │
│  │   │ Supervisor │──── Intent Classification (Gemini AI)   │   │
│  │   └─────┬──────┘                                         │   │
│  │         │  Routes to specialized agents                  │   │
│  │         ▼                                                │   │
│  │   ┌──────────┬───────────┬───────────┬────────────┐      │   │
│  │   │  Infra   │  Docker   │    K8s    │ Terraform  │      │   │
│  │   │  Agent   │  Agent    │   Agent   │   Agent    │      │   │
│  │   └────┬─────┴─────┬─────┴─────┬─────┴──────┬─────┘      │   │
│  │        │           │           │            │             │   │
│  │        └───────────┴───────────┴────────────┘             │   │
│  │                        │                                  │   │
│  │                        ▼                                  │   │
│  │   ┌─────────────────────────────────────────────────┐     │   │
│  │   │              Synthesis Node                      │     │   │
│  │   │       (Gemini AI Response Generation)            │     │   │
│  │   └─────────────────────────────────────────────────┘     │   │
│  │                                                          │   │
│  │   ┌──────────────┐    ┌─────────────────┐                │   │
│  │   │ Approval Gate│───►│ Execution Agent │                │   │
│  │   │   (HITL)     │    │ (Secure Runner) │                │   │
│  │   └──────────────┘    └─────────────────┘                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 22+ |
| npm | 10+ |
| Git | 2.x |

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/DevOpsGPT.git
cd DevOpsGPT
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your Gemini API key:
#   GEMINI_API_KEY=your_key_here

# Start the server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

### 4. Open the App

Navigate to **http://localhost:5173** — the React app connects to the backend at `http://127.0.0.1:8000`.

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Your Google Gemini API key |
| `EXECUTION_TIMEOUT` | ❌ | Max command execution time in seconds (default: `30`) |

> ⚠️ **Never commit your `.env` file.** It's already in `.gitignore`.

---

## 🔄 CI/CD Pipeline

This project includes a **production-grade GitHub Actions pipeline** with two workflows:

### CI Pipeline (`.github/workflows/ci.yml`)

Runs on every **push** and **pull request** to `main` / `develop`:

```
Backend Lint (ruff) ──► Backend Tests (pytest + coverage) ──┐
                                                            ├──► Docker Build & Push (main only)
Frontend Lint (eslint) ──► Frontend Build (vite) ───────────┤
                                                            │
Security Scan (pip-audit + npm audit + gitleaks) ───────────┘
```

| Stage | Tools | Purpose |
|-------|-------|---------|
| 🐍 Backend Lint | `ruff` | Code style + formatting |
| 🧪 Backend Tests | `pytest`, `pytest-cov` | Unit tests with coverage |
| ⚛️ Frontend Lint | `eslint` | Code quality |
| 🏗️ Frontend Build | `vite build` | Production bundle validation |
| 🔒 Security Scan | `pip-audit`, `npm audit`, `gitleaks` | Vulnerability & secret detection |
| 🐳 Docker Build | `docker/build-push-action` | Multi-stage images → GHCR |

### Deploy Pipeline (`.github/workflows/deploy.yml`)

Triggered by **version tags** (`v*`) or **manual dispatch**:

```
CI Gate ──► Staging Deploy ──► Smoke Tests ──► Production Deploy
```

### Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `GEMINI_API_KEY` | Backend API key for Google Gemini |

> `GITHUB_TOKEN` is provided automatically by GitHub Actions.

---

## 📡 API Reference

### `POST /api/v1/chat`

Send a message to the DevOpsGPT agent.

**Request Body:**

```json
{
  "history": [
    { "role": "user", "content": "previous message" },
    { "role": "model", "content": "previous response" }
  ],
  "message": "Show me running Docker containers"
}
```

**Response:**

```json
{
  "response": "Here are your running containers:\n\n```\nCONTAINER ID   NAMES         STATUS\na1b2c3d4e5f6   nginx-proxy   Up 3 hours\n```"
}
```

### `GET /docs`

Interactive Swagger UI documentation (auto-generated by FastAPI).

---

## 📁 Project Structure

```
DevOpsGPT/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline (lint, test, build, security)
│       └── deploy.yml          # Deployment pipeline (staging → production)
├── backend/
│   ├── main.py                 # FastAPI app + LangGraph agent orchestration
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Multi-stage production image
│   ├── .dockerignore           # Build context exclusions
│   ├── .env                    # Local environment (git-ignored)
│   └── tests/
│       └── test_smoke.py       # Smoke tests
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main chat interface
│   │   ├── App.css             # Glassmorphism dark theme
│   │   ├── main.jsx            # React entry point
│   │   └── index.css           # Global styles
│   ├── index.html              # HTML entry point
│   ├── package.json            # Node dependencies
│   ├── vite.config.js          # Vite configuration
│   ├── eslint.config.js        # ESLint flat config
│   ├── Dockerfile              # Multi-stage Node → Nginx image
│   └── .dockerignore           # Build context exclusions
├── .gitignore
└── README.md                   # ← You are here
```

---

## 🐳 Docker

### Build Images Locally

```bash
# Backend
docker build -t devopsgpt-backend ./backend

# Frontend
docker build -t devopsgpt-frontend ./frontend
```

### Run Containers

```bash
# Backend
docker run -d \
  --name devopsgpt-backend \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_key_here \
  devopsgpt-backend

# Frontend
docker run -d \
  --name devopsgpt-frontend \
  -p 80:80 \
  devopsgpt-frontend
```

---

## 🛡️ Security Model

DevOpsGPT implements a **three-layer security model** for command execution:

| Layer | Mechanism | Example |
|-------|-----------|---------|
| **Allowlist** | Only pre-approved executables can run | `docker`, `kubectl`, `git`, `terraform` |
| **Blocklist** | Dangerous executables are always rejected | `sudo`, `shutdown`, `dd`, `mkfs` |
| **Pattern Scanner** | Regex-based detection of destructive patterns | `rm -rf /`, fork bombs, `curl \| sh` |

All mutation commands go through the **Approval Gate** — the AI drafts the command and waits for explicit user confirmation before execution.

---

## 🧑‍💻 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feat/my-feature`
3. **Commit** your changes: `git commit -m "feat: add my feature"`
4. **Push** to the branch: `git push origin feat/my-feature`
5. **Open** a Pull Request

### Code Standards

- **Backend:** Formatted with `ruff` — run `ruff check .` and `ruff format .` before committing
- **Frontend:** Linted with `eslint` — run `npm run lint` before committing
- **Commits:** Follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.)

---

## 📄 License

This project is open-source. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built with ⚡ by <a href="https://github.com/Saadxd0">Saadxd0</a></sub>
</p>
