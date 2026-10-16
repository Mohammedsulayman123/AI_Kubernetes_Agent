# AI Kubernetes Agent

On-demand Kubernetes troubleshooting system.

```text
Frontend
    ↓
FastAPI Backend (Orchestrator)
    ↓
Kubernetes Investigation Layer
    ↓
AI Kubernetes Agent
    ↓
LLM Reasoning
    ↓
Root Cause + Suggested Fix
    ↓
Frontend Diagnosis
```

This repository currently contains the **project foundation only**. Kubernetes inspection, AI reasoning, OpenRouter, and authentication are not implemented yet.

## Project structure

```text
backend/     FastAPI orchestrator
frontend/    Next.js UI
docs/        Project documentation
prompts/     Implementation prompts
```

## Run with Docker

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

Backend (`backend/.env`):

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
KUBECONFIG_PATH=
```

Frontend (`frontend/.env.local`):

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
