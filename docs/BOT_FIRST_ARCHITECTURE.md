# SciCloud Bot-first architecture proposal

## Decision

Do not replace the current Agent/Director architecture with a chat bot. Treat **Bot as the event-driven, always-available execution surface**, while Agents remain the reasoning/planning capability. The production workflow is the source of truth.

- **Agent**: interprets intent, plans, selects Skills/tools, and proposes decisions.
- **Bot**: receives a trigger, applies explicit rules/permissions, invokes a bounded handler, reports status, and emits an event.
- **Workflow**: persists production stages, dependencies, retries, checkpoints, and artifact IDs.
- **Skill**: a versioned capability used by an Agent or Bot.
- **Memory**: project bible, character/setting continuity, preferences, and run history; not a substitute for task state.
- **Model Router**: chooses an available local/remote model according to capability, readiness, resource budget, and user policy.

## Event contract

Use named events such as `director.plan.requested`, `script.approved`, `storyboard.created`, `workflow.ready`, `task.failed`, `qc.failed`, `qc.passed`, and `render.completed`. Event payloads should carry stable IDs (project, episode, plan, workflow, storyboard, task, artifact), a timestamp, and a schema version as the contract matures.

The initial local runtime is intentionally small: typed-by-convention event names, JSON-safe payloads, handler subscriptions, JSONL audit records, per-handler completion checkpoints, and rejection when a previously seen event ID is reused with different content. Retries skip handlers already checkpointed as successful. It does not create a second production scheduler or run model calls itself.

The WorkflowEngine can receive an optional event publisher and emits lifecycle events after state persistence (workflow.ready, task.started, task.completed, task.failed, task.retried, workflow.paused, workflow.resumed). It exposes the latest event result/error for a UI status surface. The desktop entry point registers the Production Bot with automatic execution disabled by default; the Bot delegates to the existing AutoDirector only when explicitly configured with auto_execute=True. Event delivery failures do not roll back saved workflow state.

## First Bot roles for SciCloud

1. **Director Bot** — turns a user request into a validated plan; it must not fabricate missing required arrays.
2. **Production Bot** — advances only tasks whose dependencies are satisfied, using the existing WorkflowEngine and execution engine.
3. **Continuity Bot** — checks character/setting facts against project memory and flags conflicts.
4. **QC/Repair Bot** — routes failed quality checks to bounded repair plans; repeated failures stop and surface a reason.
5. **Resource Bot** — checks local RAM/backend and shot-size budgets before expensive jobs.
6. **Delivery Bot** — assembles approved assets with FFmpeg, verifies the output, then marks delivery complete.

## Operating rules

- One event should not silently imply successful production; handlers return explicit results and artifacts.
- Idempotency is based on stable event IDs; side-effecting handlers must still make their own operations idempotent.
- Every handler is bounded, logged, and observable. Failures remain visible and retryable.
- Use local-first models on the current M1/8GB machine; do not assume video diffusion will fit in memory.
- No bot should delete/overwrite source assets or publish externally without explicit user approval.
- Start as an in-process local runtime. Add background worker, scheduling, external chat connectors, and multi-agent concurrency only after restart recovery and end-to-end tests are reliable.

## Incremental roadmap

1. Add event runtime and unit tests.
2. Emit workflow lifecycle events from the existing WorkflowEngine.
3. Subscribe Production Bot to workflow-ready events and delegate execution to the existing engines; the app startup registration is approval-gated by default.
4. Surface Bot result/error and task lifecycle events in the desktop UI; then add QC/repair and resource preflight events.
5. Add a single status feed to the UI; then optional Telegram/Discord/webhook connectors.
6. Introduce durable queue/recovery and bounded concurrency only when needed; avoid a distributed-service stack on an 8GB local Mac.

## Limitations

This is an architectural foundation, not yet a production-grade durable queue. JSONL handler checkpoints reduce duplicate work on retry, but a crash between a handler's external side effect and its completion checkpoint can still repeat that side effect. The log is not fsync-backed, multi-process writes are not coordinated, event delivery and workflow persistence are not atomic, and there is no general background replay worker. Those require explicit follow-up work and tests.
