# AI Kubernetes Agent

An on-demand Kubernetes troubleshooting dashboard. Choose a Kubernetes context and optionally narrow an investigation to a namespace or pod. The backend gathers cluster evidence, identifies potential issues, and asks an OpenRouter model for a root-cause analysis and suggested remediation. The frontend displays investigation progress, diagnosis details, and recent investigation history.

## Features

- Lists Kubernetes contexts from the backend's kubeconfig.
- Investigates pods and their logs, Kubernetes events, deployments, and service networking.
- Scopes investigations to a namespace or a specific pod.
- Uses an OpenRouter-compatible LLM to explain detected problems and suggest fixes and `kubectl` commands. Healthy clusters skip the LLM call.
- Streams investigation progress to the UI through InsForge Realtime.
- Supports InsForge email/password authentication and stores recent investigation history in the `investigations` database table.
- Includes optional test scenarios for CrashLoopBackOff, ImagePullBackOff, OOMKilled, and service selector mismatch, with cleanup actions.

> Test scenarios apply and delete Kubernetes resources. Use them only on a cluster where you are comfortable creating and removing the scenario resources.

## Architecture

```text
Next.js dashboard
  ├─ InsForge authentication, history, and realtime progress
  └─ FastAPI API
       ├─ kubectl-based, read-only investigation
       ├─ evidence analysis (pods, logs, events, deployments, networking)
       └─ OpenRouter diagnosis when issues are detected
```

The test-scenario endpoints are an exception to the read-only investigation flow: they apply manifests and delete the scenario namespace on cleanup.

## Project structure

```text
backend/     FastAPI API, Kubernetes inspectors, and AI diagnosis
frontend/    Next.js dashboard and InsForge client integration
docs/        Project documentation
prompts/     Implementation prompts
```

## Requirements

- Docker Compose, or Python 3.12+, Node.js 20+, and npm for local development.
- `kubectl` access to the Kubernetes cluster(s) you want to investigate.
- A kubeconfig file available to the backend. The backend process needs Kubernetes read permissions for investigation. Test scenarios also need permissions to create and delete the resources they use.
- An OpenRouter API key and model name to enable AI diagnosis when issues are found.
- An InsForge project configured with authentication, Realtime access, and an `investigations` table for authentication, progress updates, and saved history.

## Configuration

Create `backend/.env`:

```env
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=your-openrouter-model
KUBECONFIG_PATH=/path/to/kubeconfig
CORS_ORIGINS=http://localhost:3000
INSFORGE_BASE_URL=https://your-project.region.insforge.app
INSFORGE_ANON_KEY=your-insforge-anon-key
```

`OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are needed for AI diagnoses. Without a usable model configuration, the backend can still collect evidence, but AI reasoning will report an unavailable diagnosis when an issue requires it.

For the frontend, configure these public variables in `frontend/.env.local` when you are not using the defaults:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_INSFORGE_BASE_URL=https://your-project.region.insforge.app
NEXT_PUBLIC_INSFORGE_ANON_KEY=your-insforge-anon-key
```

The frontend variables are public and are bundled into the browser app. Use only the InsForge anon key here; never put a service-role key or OpenRouter secret in a `NEXT_PUBLIC_` variable. Ensure the InsForge database has an `investigations` table with fields compatible with `frontend/types/investigation.ts` and access policies that allow signed-in users to read and create their own records.

### Kubernetes access with Docker Compose

Compose mounts `${USERPROFILE}/.kube` read-only into the backend container at `/root/.kube` by default and sets `KUBECONFIG_PATH` accordingly. If your kubeconfig is elsewhere, set `KUBECONFIG_DIR` before starting Compose. Verify the selected context and credentials are usable from the Docker environment.

## Run with Docker Compose

```bash
docker compose up --build
```

Then open:

- Dashboard: http://localhost:3000
- Backend health: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

Use `docker compose down` to stop the services.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set backend environment variables in `backend/.env`. Ensure `kubectl` is installed and can access the intended kubeconfig/context.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at http://localhost:3000. Set its InsForge and backend URL values in `frontend/.env.local` as needed.

## API overview

The FastAPI service currently exposes:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check |
| `GET` | `/clusters` | List kubeconfig contexts |
| `GET` | `/namespaces` | List namespaces (`?context=...` optional) |
| `GET` | `/namespaces/{namespace}/pods` | List pods in a namespace (`?context=...` optional) |
| `POST` | `/investigate` | Run an investigation; accepts optional `context`, `namespace`, `pod_name`, and realtime `channel` |
| `GET` | `/test-scenarios` | List built-in test scenarios |
| `POST` | `/test-scenarios/apply` | Apply a scenario to the selected context |
| `POST` | `/test-scenarios/cleanup` | Delete a scenario's namespace from the selected context |

Interactive API documentation is available at `/docs` while the backend is running.

## Tests

Backend tests use pytest. From `backend/` run:

```bash
python -m pytest
```

