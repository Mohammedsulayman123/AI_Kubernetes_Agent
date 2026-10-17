# Project prompts

This folder contains reusable instructions for planning, implementing, and reviewing changes to the AI Kubernetes Agent. Prompts are development aids; the source code, API models, and project documentation remain the source of truth for application behavior.

## Available prompts

- [Five-step implementation roadmap](implementation-roadmap.md): sequential, gap-driven prompts covering foundations, Kubernetes evidence collection, AI diagnosis, dashboard and InsForge flows, and end-to-end integration.

The repository already implements parts of these phases. Inspect the current code before following a step, and preserve working behavior while addressing concrete gaps.

## Writing and maintaining prompts

Keep each prompt focused and include its goal, relevant code areas, requirements, safety boundaries, and completion criteria. Kubernetes investigations should remain read-only; clearly identify operations that create or delete cluster resources. Keep OpenRouter credentials server-side. For InsForge integration changes, follow `AGENTS.md` and fetch current official documentation before writing code.

Update prompts when the architecture or implementation changes. For setup and architecture details, see the root [README](../README.md) and [project documentation](../docs/README.md).
