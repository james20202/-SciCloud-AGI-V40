# SciCloud AGI V40.100

V40.81-40.100 完整 Episode Pipeline：Plan → Shot Queue → Local Media → Assemble → QC → Publish。

## 原则
- 不伪造媒体成功
- 缺模型/工作流时明确 blocked
- 每个阶段持久化，可恢复
- 最终视频必须是真实文件
- 发布包只在 QC 通过后生成
