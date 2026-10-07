# SciCloud AGI V40.30.0 · Local Production Factory

V40.21～V40.30 将 V40 的 AI Director 核心连接到真实本地媒体生产能力。

## 已实现
- 本地图像/视频：通过 Model Hub -> ComfyUI Adapter 提交真实工作流；没有工作流或模型时明确失败，不伪造生成。
- 本地 TTS：通过命令适配器调用用户配置的本地 TTS；只有实际输出文件存在才算成功。
- FFmpeg Media Engine：视频拼接、音视频合成、字幕烧录、音频响度标准化、MP4 导出。
- Subtitle Engine：把导演/对白段落生成标准 SRT。
- Audio Engine：人声与背景音乐基础混音。
- Production Engine：创建生产运行、提交 ComfyUI、TTS、字幕、装配、导出。
- UI：新增“本地生产工厂”页，用于检查 FFmpeg/FFprobe、ComfyUI/TTS 开关与创建生产运行。

## 版本批次
- 40.21：本地媒体生产基础
- 40.22：ComfyUI 图像/视频执行接入
- 40.23：TTS 真实输出校验
- 40.24：字幕生成
- 40.25：音频处理
- 40.26：自动剪辑装配
- 40.27：MP4 导出
- 40.28：Production Run 状态
- 40.29：生产工厂 UI
- 40.30：真实生产链整合

## 原则
模型能力由用户本机配置决定。V40 不把“任务已提交”冒充“成片已生成”，也不伪造视觉/视频评分。
