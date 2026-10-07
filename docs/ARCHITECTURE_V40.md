# SciCloud AGI V40 — AI内容导演操作系统

## 1. 产品定位
V40 不是单纯的视频生成器，而是本地优先的 AI 内容导演操作系统：
用户提供创意意图，Director 负责策划、拆解、调度、生产、质检、修复、发布，并将结果反馈到 Memory/Knowledge。

## 2. 七层架构
1. AI 大脑层：Director / Planner / Creator / Reviewer / Fixer / Producer
2. 内容策划层：Trend / Hook / Story / Rhythm / World / IP
3. 导演创作层：Character / Scene / Prompt / Cinematic / Battle / Atmosphere / Ritual / Sound
4. 生产执行层：Workflow / Skills / Model Hub / Image / Video / Voice / Edit / Timeline
5. 资产数据层：Asset / Memory / Knowledge / Storage / Cache / Version
6. 质量发布层：QC / Auto Fix / Subtitle / Export / Publish / Data Feedback
7. 系统底座层：System / Diagnostics / Plugins / Models / Update / Backup / Rollback

## 3. 核心原则
- Local-first：本地优先，云端作为可选适配器。
- Provider-agnostic：Director 不绑定任何单一模型厂商。
- Skill-first：能力通过 Skill 注册，模型只是执行后端。
- Stateful：所有生产任务可暂停、恢复、重试、回滚。
- Versioned：项目、人物、场景、Prompt、Workflow、输出均可版本化。
- Data-safe：升级只替换程序代码，不覆盖 data/projects/assets/output/backups。
- Simple/Pro 双模式：普通用户只面对创意入口，专业用户可以深入控制。

## 4. 标准生产链
Intent → Trend/Plan → Story → Hook → Rhythm → Character/Scene → Shot Plan → Prompt → Model/Skill → Image/Video/Voice → Timeline/Edit → Sound/Subtitle → QC → Auto Fix → Export → Publish → Data Feedback → Memory/Knowledge

## 5. 核心实体
- Project
- Episode
- Character
- Scene
- Shot
- Prompt
- Asset
- Task
- WorkflowRun
- Skill
- Model
- Memory
- Knowledge
- Version
- QCReport
- PublishRecord

## 6. ID 规则
- PROJECT-00001
- EP-00001
- CHAR-00001
- SCENE-00001
- SHOT-00001
- ASSET-00001
- PROMPT-00001
- TASK-00001
- RUN-00001

## 7. Director 调度原则
Director 不直接执行具体媒体操作；它生成结构化计划并调用 Planner/Workflow/Skill。
执行结果回写 WorkflowRun，Reviewer/QC 给出结构化问题，Fixer 产生修复任务。

## 8. 存储
默认目录：
```
app/       程序
projects/  项目
assets/    角色、场景、素材
memory/    项目记忆
knowledge/ 导演知识库
cache/     可重建缓存
output/    成片
backups/   升级与项目备份
logs/      日志
```
Storage Adapter 预留 Local / SMB-NAS / WebDAV / S3 / Google Drive / OneDrive。

## 9. 升级协议
ZIP → 校验 → 停止应用 → 备份代码 → 保留用户数据 → 替换代码 → 数据迁移 → 自检 → 启动；失败自动回滚。

## 10. 版本路线
- V40.0：基础驾驶舱 + 升级系统（当前）
- V40.1：导演驾驶舱 + Intent → Plan 数据流
- V40.2：Prompt Engine
- V40.3：Character / Scene / Asset Center
- V40.4：Workflow Engine + 可恢复任务
- V40.5：Director Agent
- V40.6：Model Hub + Skill Registry
- V40.7：Media/Timeline/Sound
- V40.8：QC + Auto Fix
- V40.9：Publish + Data Feedback
- V41：完整本地 AI 导演工作站

## V40.12–V40.20 AI导演核心闭环
Cross-shot Director → Story QC → Director Decision → Repair Planner → Workflow Requeue → Director Loop。
视觉语义仍由真实 Vision adapter 提供；没有模型时只做确定性结构与连续性检查。
