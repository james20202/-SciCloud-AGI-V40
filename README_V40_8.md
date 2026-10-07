# SciCloud AGI V40.8.0

## AI导演自动执行器
V40.8 将生产工作流从“用户逐任务点击”升级为“AI导演自动推进”。

链路：
**Director Plan → Workflow → Ready Task → Skill/Model/Adapter → Result → Asset → 下一任务**

### 能力
- 自动寻找当前可执行任务
- 按依赖顺序推进
- 调用 V40.3 Execution Engine
- 成功后自动解锁后续任务
- 任一任务真实执行失败立即停止，避免错误向后传播
- 支持暂停/恢复
- 支持停止本轮自动执行
- 保存逐任务执行日志到 `projects/execution_logs/`
- 保留手动执行模式

### 安全原则
V40.8 不会把“没有模型/没有命令/没有真实输出”的任务伪装成成功。自动执行只负责编排，实际生成仍由已配置的本地 Model/Adapter 完成。
