# SciCloud AGI V40.130.0 — Model Runtime Layer

V40.101–V40.130 批量升级：
- 本地模型真实能力探测
- FFmpeg / ComfyUI / TTS command 运行时诊断
- ComfyUI workflow JSON 自动解析
- ComfyUI prompt_id 提交结果与可选轮询接口
- 模型可用性摘要与阻塞原因
- 新增“模型实战诊断”页面
- 继续坚持 no fake success：未启动/未配置的模型不会被标记为可生产

本版本不内置任何第三方模型权重，也不会自动下载大模型。
