# SciCloud AGI V40.5 · Character Bible / Scene Bible

V40.5 建立长期创作一致性层。

## 新增
- `core/bible_manager.py`：人物 / 场景 Bible，稳定实体 ID 与版本。
- `ui/pages/bible_center.py`：Bible 管理界面。
- Prompt Engine 自动读取 Character / Scene Bible 约束。
- 正向约束与负面约束自动进入 Prompt。

## 核心链路
Director Plan → Shot → Character/Scene Bible → Prompt Engine → Skill → Model → Result → Asset Center

## 一致性原则
- 人物 ID：`CHAR-XXXXXXXX`
- 场景 ID：`SCENE-XXXXXXXX`
- 修改设定自动升版本，不覆盖旧版本。
- Bible 只是约束层；实际模型能力仍由 Model Hub / Adapter 决定。
