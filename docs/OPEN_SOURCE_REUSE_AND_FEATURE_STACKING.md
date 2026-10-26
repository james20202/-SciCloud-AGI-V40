# Open-source reuse and feature stacking plan

Reviewed: 2026-10-26

This is a selective reuse plan for SciCloud AGI V40. Repositories are reference material, not dependencies to install wholesale. The target runtime remains a low-memory Apple Silicon Mac with local Ollama and optional ComfyUI; cloud-only providers must stay optional.

## Candidates and reuse boundaries

| Project | License reported by its repository/listing | Potential reuse | Decision |
| --- | --- | --- | --- |
| [Toonflow](https://github.com/skylight-9/Toonflow) | Apache-2.0 | Production workspace, storyboard UX, visual workflow and model adapters | Study data contracts and interaction patterns; do not import its full web stack into the Qt desktop app. |
| [LumenX Studio](https://github.com/alibaba/lumenx) | MIT reported in the short-drama project catalog; verify the canonical repository/license before copying | Novel-to-motion-comic stages, asset extraction and storyboard organization | Architecture reference only until the canonical upstream URL and exact license are verified. |
| [ai-fusion-video](https://github.com/Stonewu/ai-fusion-video) | MIT reported in the catalog | Task persistence, storyboard/media management and ComfyUI-oriented orchestration | Compare task lifecycle and media persistence against SciCloud's existing workflow engine; avoid duplicating a second backend. |
| [zenstory-ai/drama-skills](https://github.com/zenstory-ai/drama-skills) | MIT reported by upstream docs | Script, continuity, storyboard prompt and production QA checklists | Adapt ideas and tests into native SciCloud Skills; review each source file and retain required notices if copying code. |
| [PAMPAS-Lab/awesome-ai-short-drama](https://github.com/PAMPAS-Lab/awesome-ai-short-drama) | Curated index; not a code dependency | Discovery index for short-drama and motion-comic projects | Recheck individual repository licenses, activity and dependencies before every adoption. |
| [code-video-showcase](https://github.com/Moessif/code-video-showcase) | MIT reported upstream | Deterministic visual composition and render QA patterns | SciCloud has an independent local title-card engine; no upstream templates were copied. |

## Implemented feature stack

- core/motion_graphics_engine.py: local title/section card generation using Pillow + FFmpeg.
- core/execution_engine.py: title_card and motion_graphics workflow task types invoke the engine, verify a non-empty MP4, persist task outputs, and register the result as an asset.
- tests/test_motion_graphics_execution.py: workflow success and renderer failure-path tests.

## Additional candidates from the next review pass

| Project | License / runtime caveat | Compatible ideas to extract | Integration decision |
| --- | --- | --- | --- |
| [Story Claw](https://github.com/ZC89757/story-claw) | MIT; Node/Electron, API-backed image/LLM stages, ComfyUI + H3 rendering; primarily packaged for Windows | Stage-aware character/scene variants, persistent per-character voice map, resumable episode stages, clip-level visual checks | Do not port the Electron application. Translate the data contracts and failure-mode tests into SciCloud's Python services. Keep remote image APIs optional. |
| [VideoClaw](https://github.com/HITsz-TMG/VideoClaw) | MIT; Python + Node/WebUI, configured model APIs and external generation services | Human approval gates, stage-by-stage production artifacts, first-frame / first-last-frame / reference-image video modes, episode continuation | Reuse workflow concepts and provider capability schemas only after source-level review. Avoid importing its UI or service stack. |
| [Jellyfish](https://github.com/Forget-C/Jellyfish) | Apache-2.0; backend/front-end and Docker services including database, queue and object-storage components | Asset lifecycle, storyboard review, asynchronous job status/cancel/recovery, consistency management | Reference architecture only for now; its infrastructure footprint is too heavy to transplant into the 8 GB Mac desktop build. |
| [LocalMiniDrama](https://github.com/xuanyustudio/LocalMiniDrama) | MIT; JavaScript application, remote model calls may still be needed | Episode workspace, skip-existing/resume behavior, batch retry, project ZIP import/export, prompt editing and multi-aspect-ratio support | Treat as UX and workflow-contract reference. Do not replace SciCloud's Python/Qt core or assume it provides offline inference. |
| [Comic-drama](https://github.com/tccnnd/Comic-drama) | MIT; early local-first prototype | Canonical timeline, provider-neutral media tasks, 2.5D fallback, project-scoped assets and delivery manifests | Compare contracts against SciCloud's existing canonical timeline and FFmpeg assembly before adopting anything; avoid duplicate schemas. |

### Compatibility filter applied before importing any upstream code

1. **Preserve SciCloud's runtime:** Python/Qt desktop, existing workflow engine, local Ollama, optional ComfyUI, FFmpeg, current project and asset directories.
2. **No wholesale app imports:** do not add a second project database, job scheduler, web front end, or provider system when SciCloud already has the corresponding service.
3. **Low-memory first:** CPU-friendly deterministic features should work without downloading models; GPU/video models remain optional and should be capability-checked before task execution.
4. **Stable artifact contracts:** new modules must preserve workflow_id, task_id, storyboard_id, shot identity, duration, visual prompt, dialogue, character references, and real output paths.
5. **Feature adoption must include tests:** happy path, missing dependency, interrupted task/retry, invalid output, legacy workflow compatibility, and no-network/no-model-download behavior where applicable.
6. **License and provenance:** keep attribution and required license texts for copied code; ideas/schema patterns are reviewed separately from verbatim code. No project is considered safe to import merely because its README says open source.

## Next high-value stacks

1. Shot-level production contract: keep shot_id, visual prompt, dialogue, character references, and duration attached through image/video/audio and final edit.
2. Audio-first timeline: generate subtitle/voice timing manifests and validate that the assembled timeline meets the episode duration target.
3. Continuity QA: check missing character/scene references, prompt gaps, repeated shot IDs, duration mismatch, and missing media before export.
4. Reusable episode package: title card, main clips, voice/music, subtitles, QC report, and final export manifest in one task-linked package.
5. Provider-neutral routing: local Ollama/ComfyUI/FFmpeg first; optional remote providers only when explicitly configured.

## Adoption guardrails

- Do not copy code unless the canonical upstream license is confirmed and required notices are preserved.
- Avoid pulling in a full Node/Chromium/database service stack for a single feature.
- Pin dependencies and use isolated optional adapters.
- A CI pass validates contracts and tests; it does not establish visual quality or prove a real Mac/ComfyUI render.
- Keep the feature branch PR open and unmerged until the user validates the install package.


## Audio/subtitle timeline stack (2026-10-26)

The latest candidate review found timeline-first production patterns in [ai-video-studio](https://github.com/yfge/ai-video-studio), and SRT/subtitle export patterns in [AI Video Pipeline](https://github.com/Youhai020616/ai-video-pipeline). These are references only: both describe hosted generation providers in parts of their pipelines, so SciCloud must not silently add API dependencies or download speech models.

SciCloud now has a small native `core/audio_timeline.py` contract derived from the existing canonical shot contract:
- emits per-shot start/end ranges and keeps dialogue, voiceover, and character IDs attached;
- drafts SRT cues from dialogue, falling back to voiceover where dialogue is absent;
- rejects overlapping or invalid SRT cues;
- explicitly marks timestamps as planned shot timing and requires real-audio alignment before final export. It does not claim word-level transcription or actual TTS timing.
- no new dependency, second scheduler, database, UI framework, or model download.

Tests cover timing, subtitle output, duplicate shot IDs, and overlap rejection. The next integration step is to connect this manifest to actual TTS output durations and final edit/export tasks, preserving legacy workflow JSON.


## Episode handoff export (2026-10-26)

Further review of MIT-licensed [Comic-drama](https://github.com/tccnnd/Comic-drama), [LocalMiniDrama](https://github.com/xuanyustudio/LocalMiniDrama), and [OpenManga](https://github.com/pr0h0/OpenManga) highlighted reusable production ideas: canonical timeline data, resumable local artifacts, and a complete episode handoff. SciCloud does not import their application stacks or model dependencies.

Implemented natively in this repository:
- `core/episode_package.py` creates a ZIP handoff from already-generated, non-empty workflow artifacts;
- requires the edit and QC stages to be marked done before packaging;
- includes media, JSON artifacts, available subtitle drafts, QC report payloads, and a manifest with SHA-256 hashes;
- validates the ZIP after writing and atomically replaces the destination;
- reports missing/empty outputs instead of inventing success or regenerating media;
- `publish` tasks now call this package builder through the existing execution engine.

No extra runtime dependency, model download, or new database is required. A draft subtitle is clearly marked as planned-shot timing until aligned to actual audio.


## Production QC: target-duration gate

The prompt-stage artifact records both the sum of planned shot durations and the requested episode duration. QC verifies that the reported actual duration matches the canonical shot sum and that the shot sum is within the target tolerance (max of 1 second or 2% of target). A large mismatch, such as a 30-second shot plan for a 60-second target, fails the prompt-contract check rather than allowing a structurally valid but undersized episode to proceed unnoticed. This is planned-timeline validation; it does not claim that rendered media or voice audio has the same duration until the media QC stage probes actual files.

## ComfyUI workflow registry execution (2026-10-26)

The registry pattern is now wired into the existing `ComfyUIAdapter`; SciCloud does not import a second orchestration runtime.

- A task can select a saved manifest with `workflow_registry_id`; `workflow_params` and `workflow_assets` are bound through the existing manifest compiler.
- Built-in manifests live under `data/comfyui_workflows/builtin/`; user overrides/imports live under `data/comfyui_workflows/user/`. A user manifest with the same ID overrides the built-in one.
- Inline `workflow_manifest` and legacy API `workflow` JSON remain supported for backward compatibility.
- Missing registry IDs and invalid manifests return actionable errors before submitting a ComfyUI job.
- Tests cover registry selection, parameter/asset binding, missing workflow behavior, and legacy manifest compilation.

For upstream video templates, prefer the official [Comfy-Org workflow templates](https://github.com/Comfy-Org/workflow_templates) as versioned starting points. Wan 2.2 includes 5B and 14B video workflows, but those weights are not assumed suitable for an 8 GB M1; the adapter does not download models or silently change providers. A real render still requires a compatible local ComfyUI installation, matching nodes, and model files.

### Capability-based workflow selection

ComfyUI media tasks can now set `workflow_capability` instead of embedding an API graph. If exactly one local registered manifest matches, the adapter compiles it with the task's `workflow_params` and `workflow_assets`. Image tasks default to `image.text2image`; video tasks default to `video.image2video`. When multiple manifests match, execution stops with an instruction to select `workflow_registry_id`, avoiding nondeterministic model selection. Existing inline graphs and explicit registry IDs take precedence.

## TTS artifact verification

The command-based TTS adapter now requires an explicit `output_path` or `output_file`, accepts argument arrays or shell-like quoted command strings without invoking a shell, supports an `{output}` placeholder, and only reports success when the target file exists and is non-empty. Non-zero exits, missing executables, timeouts, and empty/missing audio files fail the task. This closes the previous gap where a command could exit successfully without registering any usable audio artifact. Four regression tests cover the output contract and failure cases. The adapter remains provider-neutral; a compatible local TTS command must still be configured by the user.

### Storyboard-to-TTS handoff

For `voice` tasks using the command adapter, the execution engine now reads the linked storyboard and assembles a narration script from each shot's dialogue (preferred) or voiceover, unless the task supplies its own text. It provides a default local WAV destination under the project output directory. TTS command templates must use `{text}` and `{output}` placeholders to explicitly bind narration and destination; the adapter verifies the resulting non-empty file before marking the task complete. This produces a usable first-pass narration track, not word-level timing: final audio alignment and per-character voice casting remain later production steps.
