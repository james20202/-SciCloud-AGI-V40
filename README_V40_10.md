# SciCloud AGI V40.10.0

## AI导演视觉审核

V40.10 adds an optional local Vision QC adapter. The deterministic QC remains the baseline; semantic visual scoring is only reported when a real local vision command is configured.

Supported structured output from the configured command:
- `score`: 0-100
- `issues`: array of detected problems
- `suggestions`: array of correction suggestions
- optional domain scores such as `character_consistency`, `composition`, `camera`, `lighting`, `action`

The command receives one JSON argument containing the absolute media path and workflow context, and must print one JSON object to stdout.

No provider is hard-coded and no cloud token is required by the V40 core.

Auto-fix carries QC feedback into the failed task and requeues the task, then QC is run again.
