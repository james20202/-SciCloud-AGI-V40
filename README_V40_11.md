# SciCloud AGI V40.11.0

## AI导演镜头级智能决策

V40.11 adds a Director Decision Layer between visual QC feedback and automatic repair.

Flow:

Vision/QC → Director Decision → repair target selection → re-execute → QC again

Repair targets are classified as character, action, composition, camera, lighting, prompt, or scene. Decisions are persisted under `data/director_decisions` and attached to workflow tasks.

If character/scene/camera continuity is implicated, the decision marks `cascade=true`, allowing later versions to expand this into cross-shot dependency repair.

No visual intelligence is fabricated: a real local vision model remains required for semantic visual feedback.
