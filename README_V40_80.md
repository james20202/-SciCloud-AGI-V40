# SciCloud AGI V40.80

V40.61-V40.80 focuses on real local production orchestration.

## New capabilities
- Shot-level production coordinator
- Real ComfyUI submit-and-wait runner
- Production manifests and artifact validation
- Explicit blocked state when a local capability is missing
- Existing media can be registered without regeneration

## Principle
No fake generation. A task is successful only when a real output exists or a real external execution result is returned. Missing model capabilities remain blocked and can be retried after configuration.
