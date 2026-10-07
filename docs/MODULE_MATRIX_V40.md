# V40 模块矩阵

| 模块 | 一级职责 | 依赖 | 状态 |
|---|---|---|---|
| Director | 总导演、调度 | Workflow/Memory/Skills | 规划 |
| Producer | 制片、任务拆解 | Workflow/Project | 规划 |
| Planner | 内容与生产计划 | Story/Trend | 规划 |
| Creator | 内容生成 | Prompt/Model | 规划 |
| Reviewer | AI审片 | QC/Memory | 规划 |
| Fixer | 自动修复 | QC/Workflow | 规划 |
| Trend | 趋势信号 | Web/Memory | 规划 |
| Hook | 开头与留存 | Story/Rhythm | 规划 |
| Story | 剧本与世界观 | Memory/Knowledge | 规划 |
| Rhythm | 节奏 | Story/Timeline | 规划 |
| Character | 人物圣经 | Asset/Prompt | 规划 |
| Scene | 场景圣经 | Asset/Prompt | 规划 |
| Prompt | Prompt组合与适配 | Character/Scene/Model | 规划 |
| Cinematic | 镜头语言 | Shot/Prompt | 规划 |
| Battle | 战斗导演 | Cinematic/Action | 规划 |
| Atmosphere | 氛围导演 | Cinematic/Sound | 规划 |
| Ritual | 民俗幻想视觉导演 | Cinematic/Prompt | 规划 |
| Sound | 声音导演 | Timeline/Audio | 规划 |
| Workflow | 可恢复生产流程 | Tasks/Skills | 基础存在，待重构 |
| Skills | 能力注册 | Model Hub | 规划 |
| Model Hub | 模型适配 | Skills | 规划 |
| Asset Center | 资产管理 | Storage/Version | V30基础存在 |
| Memory | 项目记忆 | Database | 规划 |
| Knowledge | 导演知识库 | Storage/Memory | 规划 |
| Storage | 本地/网络存储 | File adapters | 规划 |
| Media | FFmpeg/MoviePy | Skills | V30基础存在 |
| Timeline | 多轨编辑 | Media | 规划 |
| QC | 视觉/音频/连续性检查 | Media/AI | 规划 |
| Publish | 平台发布 | Export | V30基础存在 |
| Data Feedback | 发布后数据 | Publish/Memory | 规划 |
| System | 系统诊断 | Runtime | V40基础存在 |
| Update | 升级/回滚 | Backup | V40基础存在 |
