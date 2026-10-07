# SciCloud AGI V40.1.1

本版本把 V40.1 的“导演计划”接入持久化 Workflow Engine。

## 新增
- Workflow Engine：任务依赖、状态、进度、暂停、恢复、失败、重试
- 导演计划一键进入生产队列
- 生产工作流页面
- Workflow JSON 持久化到 `projects/workflows/`
- 版本号 40.1.1

## 当前定位
这是生产编排层，尚未伪装成真实 AI 模型执行器。后续 Model Hub / Skill Registry 接入后，`start_task` 将由对应 Skill 执行真实任务。
