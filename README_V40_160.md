# SciCloud AGI V40.131～V40.160 · 模型自动生产层

本批次把 Model Hub / Runtime 与生产流程连接起来：
- Model Router：按 image/video/tts/sound/edit/vision 自动寻找“已启用且实际可探测”的本地能力。
- Production Orchestrator：为一集生产建立持久化能力计划，缺模型时明确 blocked，不伪造成功。
- Model Router UI：扫描本机能力并显示生产路由。
- Vision 默认可选，不配置时不会阻塞基础生产。

本层仍不绑定具体厂商；ComfyUI 工作流决定具体图像/视频模型，TTS 使用用户配置的本地命令。
