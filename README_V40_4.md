# SciCloud AGI V40.4

## Asset Center

V40.4 adds a persistent asset registry under `data/assets.json` and `data/assets/`.

### Stable identity
- Character: `CHAR-00001`
- Scene: `SCENE-00001`
- Generated result: `ASSET-XXXXXXXX`
- Entity versions are tracked independently (`V1`, `V2`, ...).

### Execution integration
Workflow execution now registers successful planning artifacts and adapter output files into Asset Center. Character/scene execution also imports entities from the Director Plan into the asset registry.

No output file is claimed as generated unless a real file exists.
