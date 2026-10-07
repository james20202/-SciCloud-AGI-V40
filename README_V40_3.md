# SciCloud AGI V40.3

V40.3 把 V40.2 的“能力注册”推进到“真实执行适配层”：

- Model Hub：统一登记本地模型 / 工具
- Adapter：FFmpeg、ComfyUI、TTS command
- Execution Engine：Workflow → Skill → Model → Adapter → Result
- Model Hub UI：启用/停用/连接检测
- 真实执行原则：没有模型、命令或连接时，不会伪造“生成成功”
- 规划任务可以生成真实的本地执行记录 JSON；媒体任务必须有实际适配器能力

## 默认模型

1. FFmpeg 本地媒体引擎：默认启用
2. ComfyUI：默认关闭，地址 `http://127.0.0.1:8188`
3. TTS command：默认关闭，需要配置本机 TTS 命令

## 下一步 V40.4

- Asset Center 与执行结果真正打通
- ComfyUI 工作流模板 / Prompt 自动注入
- 图片 / 视频结果自动登记 Asset ID
- Character / Scene Bible 与 Prompt Engine 联动
- 更完整的 QC 与自动修复闭环
