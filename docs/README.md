# Project documentation

This folder contains project-specific technical notes. The setup and quick-start instructions are in the [root README](../README.md).

## System overview

The application has two main parts:

- **Frontend:** Next.js dashboard for signing in, choosing a Kubernetes context and optional namespace/pod scope, starting investigations, viewing progress and diagnosis, and browsing recent history.
- **Backend:** FastAPI service that uses `kubectl` to collect evidence from the selected context, then calls OpenRouter to reason over findings when the cluster has detected issues.

The frontend uses InsForge for email/password authentication, database-backed investigation history, and realtime progress events. The backend sends progress events through InsForge Realtime. AI model credentials are read by the backend and should remain server-side.

## Investigation flow

1. The dashboard loads available kubeconfig contexts, namespaces, and pods from the API.
2. The operator starts an investigation for a context, optionally scoped to a namespace or pod.
3. The backend checks pod health and logs, Kubernetes events, deployment availability, and service networking. It publishes progress as these steps run.
4. If no issues are found, the API returns a healthy result without calling the language model. Otherwise, the backend sends the collected evidence to OpenRouter for a diagnosis with explanation, suggested fix, commands, and confidence information.
5. The UI displays the result and saves diagnosis history to InsForge for the signed-in user.

The investigation path is intended to read cluster state. The test-scenario endpoints are different: they create resources for reproducing failures and remove the scenario namespace during cleanup.

## API reference

The backend serves interactive OpenAPI docs at `/docs` and the schema at `/openapi.json`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET` | `/clusters` | List contexts from the backend kubeconfig |
| `GET` | `/namespaces` | List namespaces; accepts optional `context` query parameter |
| `GET` | `/namespaces/{namespace}/pods` | List pods in a namespace; accepts optional `context` query parameter |
| `POST` | `/investigate` | Investigate a cluster; body fields: `channel`, `context`, `namespace`, `pod_name` |
| `GET` | `/test-scenarios` | List available failure scenarios |
| `POST` | `/test-scenarios/apply` | Apply a scenario; body fields: `scenario_id`, optional `context` |
| `POST` | `/test-scenarios/cleanup` | Delete a scenario namespace; body fields: `scenario_id`, optional `context` |

## Configuration

See the root README for complete Docker and local setup. The key configuration areas are:

- **Kubernetes:** Mount or provide a kubeconfig to the backend and ensure its identity has the required cluster permissions. Investigation needs read access to pods, logs, events, deployments, and services. Applying and cleaning scenarios needs additional create/delete permissions.
- **OpenRouter:** Set `OPENROUTER_API_KEY` in the backend environment. `OPENROUTER_MODEL` is optional; the backend has a default model.
- **InsForge:** Configure the project URL and anon key for the frontend and backend. The frontend database integration expects an `investigations` table matching `frontend/types/investigation.ts`, with access policies for users' own history. Realtime progress uses the `investigations` channel and `progress` event.
- **Frontend API URL:** Set `NEXT_PUBLIC_API_BASE_URL` to the FastAPI service URL reachable by the browser.

Never expose the OpenRouter key or an InsForge service-role key in frontend variables.

## Test scenarios

The dashboard includes scenarios for CrashLoopBackOff, ImagePullBackOff, OOMKilled, and service selector mismatch. Applying one creates resources in a dedicated `agent-test-*` namespace. Use the cleanup action after testing; it deletes that namespace and its contents. Run scenarios only against a cluster where creating and deleting these resources is acceptable.

## Code map

```text
backend/app/api/          FastAPI route handlers
backend/app/kubernetes/   kubectl executor and evidence inspectors
backend/app/ai/           prompt construction, OpenRouter client, diagnosis parsing
backend/app/services/     investigation orchestration, kubeconfig, realtime, scenarios
backend/app/models/       API and diagnosis data models
frontend/app/             Next.js app entry points
frontend/components/      Dashboard, auth, progress, diagnosis, history, scenarios
frontend/services/        Backend API and InsForge clients
frontend/types/           Shared frontend data types
```

Backend tests are under `backend/tests/`; run them from `backend/` with `python -m pytest`.
