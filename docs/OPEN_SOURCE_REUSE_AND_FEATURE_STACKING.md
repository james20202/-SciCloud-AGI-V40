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
