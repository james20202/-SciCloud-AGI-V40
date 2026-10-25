# Open-source integration note: code-video-showcase

Reference repository: https://github.com/Moessif/code-video-showcase  
Reference license: MIT (copyright 2026 Moessif; retain the copyright and license when redistributing its source or substantial portions).

## What was verified

The upstream README and `SKILL.md` describe a pure-code showcase-video skill. It renders deterministic HTML/Canvas/SVG/Three.js frames, synthesizes a soundtrack with Python NumPy/SciPy, then assembles media with FFmpeg. The default showcase structure is designed around short style demonstrations and title cards; it is not a text-to-video or image-generation model and does not replace SciCloud's comic storyboard/ComfyUI pipeline.

Upstream's documented rendering stack includes Node 20+, Playwright/Chromium, FFmpeg and NumPy/SciPy. SciCloud's existing install is intentionally lighter, so this integration does **not** make Node, Chromium, NumPy or SciPy mandatory and does not download models.

## SciCloud implementation

`core/motion_graphics_engine.py` is a small, independent local renderer for intro/section/outro title cards. It uses the already-required Pillow dependency to draw a card, and FFmpeg to produce a subtle zoom/fade MP4. It supports 9:16, 16:9 and 1:1; provides several built-in palettes; validates duration, frame rate and dimensions; atomically writes PNG cards; and verifies that rendered output exists and is non-empty.

This module reuses general production techniques (deterministic layout, shared timeline values, title-card framing and output verification), but does not copy the upstream templates or claim to implement the full upstream skill. It is a reusable building block; wiring it into a visible episode-workflow action and verifying it on the target Mac remain follow-up tasks.

## Constraints and license handling

- No remote API or paid token is required.
- No model is downloaded or modified.
- The upstream MIT license does not mean every bundled font or any separately referenced asset has the same license; check each asset's own notice before redistributing it.
- If upstream source files are copied into SciCloud in a later change, preserve their copyright notice and include the MIT license text in the distributed package.
- Validate output on the target Mac with the installed FFmpeg and available CJK fonts before treating it as release-ready.

## Validation

The accompanying tests cover PNG creation, aspect-ratio/style selection, invalid inputs, FFmpeg invocation and non-empty output verification. CI can validate those contracts without requiring FFmpeg to actually render a video. Real render quality and Mac performance still require a local smoke test.
