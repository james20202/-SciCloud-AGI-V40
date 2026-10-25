# Compatibility-first upstream review — 2026-10-26

## New candidate shortlist

The upstream discovery index is https://github.com/PAMPAS-Lab/awesome-ai-short-drama. It is a discovery list, not a license grant; inspect each canonical repository and license before copying source.

| Candidate | Upstream | Candidate capability | SciCloud decision |
|---|---|---|---|
| Toonflow | https://github.com/skylight-9/Toonflow | Broad short-drama production workspace and storyboard UX | Study data contracts only; do not import the separate web stack. Confirm current canonical repo/license before copying. |
| Kineo | https://github.com/Agions/Kineo | Local motion-comic studio, project blackboard, continuity anchors, native rendering | Monitor as an early release; do not add Tauri/React/Rust dependencies to the Qt/Python app. |
| ai-fusion-video | https://github.com/Stonewu/ai-fusion-video | Storyboard/media persistence and ComfyUI-oriented task management | Compare retry and media persistence behavior; reuse concepts in existing workflow engine. |
| Drama Skills | https://github.com/zenstory-ai/drama-skills | Continuity, script/storyboard QA, production checklists | Translate selected checklists into native SciCloud tests/skills; inspect each file and license notice before copying. |
| FireRed-OpenStoryline | https://github.com/FireRedTeam/FireRed-OpenStoryline | Natural-language editing, media retrieval, reusable style skills | Future optional editing planner; preserve FFmpeg as execution backend and avoid a second timeline system. |
| VibeFrame | https://github.com/VeriContext/VibeFrame | Storyboard-driven generation, captions, voice/music, rendering and inspection | Reference for timeline validation and render inspection; do not replace existing adapters. |
| PenShot / Story Shot Agent | https://github.com/neopen/Story-Shot-Agent | Shot breakdown, continuity and model-ready prompts | Evaluate as a pre-production adapter only after checking canonical repository URL, license and current API. |

## Implemented in SciCloud

`core/shot_contract.py` introduces a dependency-light canonical shot contract. It normalizes legacy `id`/`index`/`prompt`/`narration` fields into `shot_id`/`shot_index`/`visual_prompt`/`voiceover`, preserves dialogue, scene and character references, validates duration and duplicate shot IDs, and builds a timeline manifest that explicitly reports target-duration gaps instead of silently stretching clips.

`tests/test_shot_contract.py` covers legacy field compatibility, character reference normalization, duplicate IDs, invalid durations/types, and timeline target mismatch.

## Integration boundary

This is the contract layer, not yet a claim that every existing stage has been migrated to it. Next integration pass should call the normalizer at storyboard load/save and prompt/media handoff, then assert the same shot IDs and metadata survive image/video/audio/edit tasks. Do not change existing project files in place during migration; normalize in memory and preserve unknown fields.

## Runtime constraints

- Keep Python/Qt and the current workflow engine.
- Keep Ollama and ComfyUI optional; no model download is required by the contract module.
- Do not add a second database, scheduler, frontend, or provider registry.
- A GitHub CI pass is not proof of a real Mac render or visual quality.
- Verify canonical upstream license files before copying code; discovery-catalog license labels are leads, not legal verification.