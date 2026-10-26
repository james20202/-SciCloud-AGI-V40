# Production Artifact Contract (V40)

This document defines when a workflow task may be reported as completed.

## Domain artifacts

- Director plans and storyboards are persisted as JSON using same-directory temporary files, flush/fsync, and atomic replacement.
- A prompt artifact contains one record per storyboard shot. Each record carries `shot_id`, `shot_index`, `duration`, `visual_prompt`, dialogue/voiceover, scene ID, character IDs, and the generated prompt text.
- Asset registry entries are created only for existing, non-empty files. Structured adapter output metadata is retained alongside the path.

## Media adapter completion

- ComfyUI media tasks use `render()`, not queue-only `execute()`. The render path submits the graph, waits for completion, downloads real output files into a local task-scoped directory, and returns those files to the execution engine.
- FFmpeg success is not enough to claim a media artifact. The adapter verifies that the command's final output path exists and is non-empty before returning it as an output.
- The execution engine validates every media output again before completing the task. A queued job, missing file, or empty file cannot satisfy this contract.

## Local output layout

When a ComfyUI media task does not specify `output_dir`, outputs are placed under:

`<PROJECT_DIR>/output/comfyui/<safe-workflow-id>/<safe-task-id>/`

A task may override the directory explicitly. No model weights are downloaded by this contract.

## Failure semantics

A failed render or missing artifact must leave the task failed rather than done. Errors should be surfaced through the task result and workflow state. Retry invalidates downstream task state so old outputs are not treated as current task results.

## Validation boundary

Unit tests use temporary files and fake adapters. They validate contracts and state transitions, not actual model quality. A successful CI run does not prove a real local ComfyUI installation, model, FFmpeg binary, or Mac GUI has been tested.
