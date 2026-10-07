# SciCloud AGI V40.6

## AI导演分镜系统
V40.6 将导演计划中的基础 shots 升级为可执行的导演镜头规范。

每个镜头保存：
- 景别 / Shot Size
- 机位角度
- 摄影机运动
- 构图
- 人物动作
- 表情
- 光线
- 声音
- 节奏
- 入场/出场转场
- 对白与导演备注

分镜 Prompt 会自动读取 Character/Scene Bible，并把导演镜头语言加入 Prompt Engine。

## 生产链
一句话创意 → AI导演计划 → Character/Scene Bible → AI导演分镜 → Prompt → Model Hub → Skill/Adapter → Asset Center

## 注意
V40.6 的分镜与 Prompt 层已真实落盘，但具体图像/视频模型仍由 V40.3 的 Model Hub / Adapter 决定，不虚构生成结果。
