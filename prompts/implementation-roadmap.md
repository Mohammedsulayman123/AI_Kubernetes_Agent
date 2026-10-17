# Five-step implementation prompts

Use these prompts in order when building or substantially revising the AI Kubernetes Agent. The repository already contains parts of every phase, so inspect the current code first. Treat each step as a gap-driven implementation task: preserve working behavior and implement only missing or incorrect parts. Read the root README and [project documentation](../docs/README.md) before starting.

For any change that integrates with InsForge, follow the repository's `AGENTS.md` requirement to fetch current official InsForge documentation before writing integration code. Keep secrets server-side. Do not claim a feature is complete unless it exists and has been checked.

## Step 1 — Confirm foundations and contracts

```text
Inspect the repository and document the current application structure, configuration, API models, and frontend/backend contracts. Compare them with the root README and docs/README.md. Fix only concrete gaps that block the next implementation phases: backend startup and health endpoint, frontend startup, environment variable handling, CORS, and stable request/response models. Keep Tailwind CSS at version 3.4. Do not introduce a new backend service or expose secrets to browser code. Update documentation when behavior or configuration changes. Summarize existing functionality, changes, and remaining gaps.
```

**Completion criteria:** the documented setup matches the code; the frontend and backend agree on API types; configuration has safe defaults or clear errors; no credentials are added to source control.

## Step 2 — Build reliable Kubernetes evidence collection

```text
Inspect the existing kubectl executor, kubeconfig/context handling, Kubernetes inspectors, API routes, and backend tests. Complete or repair the read-only investigation path for pods, relevant pod logs, events, deployments, and service networking. Preserve optional context, namespace, and pod scoping. Handle missing kubectl, invalid kubeconfig, inaccessible clusters, and command timeouts as useful API errors instead of crashes. Do not apply, patch, or delete cluster resources in the investigation path. Add or update focused tests for behavior changed, using mocks rather than requiring a live cluster. Update API documentation if contracts change.
```

**Completion criteria:** evidence collection works against the selected context, respects requested scope, reports partial and total failures clearly, and does not mutate the cluster.

## Step 3 — Complete AI diagnosis and progress reporting

```text
Inspect the current investigation orchestrator, prompt builder, OpenRouter client, diagnosis parser, response models, and InsForge realtime publisher. Make diagnosis use the collected Kubernetes evidence, return a structured root cause, explanation, suggested fix, commands, and confidence, and skip the model call for healthy clusters. Keep the OpenRouter key and requests in the backend. Make missing credentials, timeouts, invalid model output, and provider errors produce a safe, understandable diagnosis/error result without losing the collected evidence. Keep progress events aligned with the actual investigation stages. Before changing InsForge integration code, fetch the required current official InsForge docs as specified in AGENTS.md. Update relevant tests and docs.
```

**Completion criteria:** healthy and unhealthy results are distinguishable; AI/provider failures are handled; progress uses the agreed channel/event/payload; secrets never reach the frontend.

## Step 4 — Finish the dashboard and InsForge user flows

```text
Inspect the Next.js dashboard, auth flow, cluster/namespace/pod selectors, progress UI, diagnosis card, history service, and InsForge client. Complete the operator flow from sign-in through selecting scope, investigating, viewing results, and revisiting saved history. Keep types aligned with FastAPI request and response models. Handle loading, empty, and error states. Enforce per-user access through appropriate InsForge database policies; do not rely on frontend filtering as authorization. Fetch current official InsForge documentation before changing InsForge integration code, as required by AGENTS.md. Keep public client configuration limited to the anon key and project URL. Update docs for changed setup or behavior.
```

**Completion criteria:** a signed-in operator can use the complete dashboard flow; history is associated with the correct user; progress and errors render clearly; client code contains no server secrets.

## Step 5 — Integrate, verify, and prepare for operation

```text
Review the complete application across backend, frontend, Docker Compose, configuration, tests, and documentation. Check that the health check, API routes, CORS, kubeconfig mount, environment variable names, InsForge table expectations, and realtime channel/event agree end to end. Review test-scenario apply and cleanup behavior separately because it creates and deletes Kubernetes resources; ensure scenarios use dedicated namespaces and cleanup targets only those namespaces. Run the project checks that are requested or defined for this task, fix issues caused by the implementation, and report commands and outcomes accurately. Do not claim live-cluster behavior was verified unless a cluster was actually used. Update the root and docs README files when the operational instructions change.
```

**Completion criteria:** integration contracts and setup docs agree; relevant checks pass or their blockers are documented; cluster mutation behavior is explicit; the final report lists changes, verification, and known limitations.
