# SciCloud AGI V40

AI内容导演操作系统。本版本基于仙剧工坊 V30.5 升级，保留原生产模块与数据目录。

## 启动

在 Mac 上双击 `launch.command`。首次运行如果缺少依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 升级

以后收到新的 V40 ZIP：打开软件 → 系统中心 → 导入 ZIP 升级包。
升级程序会自动备份代码，并保留 `data/`、`projects/`、`output/`、`logs/`。

## 目录
- `core/` AI与生产核心
- `ui/` 导演驾驶舱与功能页面
- `modules/` 媒体模块
- `data/` 项目数据
- `projects/` 项目文件
- `output/` 成片输出
- `backups/` 自动升级备份


## V40.302.0 变更
- 修复导演计划的镜头总时长分配、分镜字段保留和工作流分镜 ID 关联。
- 修复首页开始创作、快捷操作、查看全部和继续创作等按钮的实际导航/信号连接。
- 增加自动回归测试和 GitHub Actions 检查。


## V40.303.0 变更
- 首页快捷按钮接入实际创作流程：开始创作会生成导演计划；分镜按钮生成计划并建立分镜；一键成片创建真实流水线任务。
- 修复单集流水线按 UUID 字典序绑定错误导演计划的问题，按 plan_id 精确关联。
- 保留导航信号与路由回归测试，并新增计划绑定回归测试。


## V40.304.0 变更
- 升级包导入前先校验 ZIP 路径和应用目录结构，拒绝路径穿越、符号链接及非升级包，避免错误 ZIP 覆盖/破坏现有安装。
- 单集流水线在创建镜头任务时保留导演计划原始镜头 ID；镜头准备失败会明确阻塞，不再继续访问不存在的运行记录。
- 状态输出新增失败阶段列表，便于定位流水线中断位置。


## V40.305.0 变更
- 主导航合并为首页、创作、生产、资产、AI核心五个工作区，另保留更多功能与系统入口。
- 将项目、ComfyUI、工作流、人物场景、Prompt、Skill、模型路由与诊断等低频入口统一放入“更多”，减少左侧按钮密度。


## V40.306.0 变更
- AI导演计划页增加空创意检查、计划结构校验、异常提示和入队错误提示。
- 计划进入生产队列前核验镜头总时长与目标时长，避免计划标称 60 秒但镜头总和不符。
- 增加不同目标时长的自动测试，并验证分镜转换保留镜头 ID、视觉提示词、对白、动作和时长。


## V40.307.0 变更
- 工作流创建前校验 plan_id、tasks 列表、任务 ID 唯一性和任务类型，错误计划不会生成空工作流。
- 所有工作流任务统一关联 storyboard_id，保证后续剧本、分镜、图像、视频、配音、剪辑、质检和发布任务可追溯到同一分镜。
- 空任务工作流不再被误标记为已完成；任务不存在时返回明确错误。


## V40.308.0 变更
- AI导演计划可通过本机 Ollama（默认 qwen2.5:3b）优化剧情梗概、人物描述、场景用途、镜头视觉提示词、动作、对白和导演备注。
- 仅访问本机 localhost Ollama API，不调用云端模型、不消耗在线 Token；模型未运行、未安装或返回格式错误时自动回退到规则计划。
- 模型只负责创意文本，镜头 ID、任务 ID、目标时长和各镜头时长仍由本地程序管理，进入队列前继续校验时长。
- 可通过环境变量 SCICLOUD_OLLAMA_URL 和 SCICLOUD_OLLAMA_MODEL 指定本机服务地址与模型名称。


## V40.309.0 变更
- AI导演计划生成移至后台线程，调用本机 Ollama 时界面不再同步等待；生成中显示状态并暂时禁用重复提交。
- 计划生成完成后自动恢复按钮状态并执行结构/总时长校验，错误通过界面提示。
- 增加异步线程回归测试。


## V40.400.0 · Production Readiness
- 生产中心新增“诊断本机环境”：检查 FFmpeg/FFprobe、Ollama/ComfyUI 本地服务连通性，以及项目数据、输出、日志和备份目录写入权限。
- 诊断只访问本机服务，不安装依赖、不下载模型、不调用云端 AI API；服务连通仅表示接口有响应，不代表模型或工作流已配置完成。
- 镜头生产状态新增阻塞数、待处理数和剩余数；部分批次不再被误判为全部失败，可继续执行剩余镜头。
- 单集生产链支持按阶段续跑，媒体阶段未完成时不会提前进入剪辑；空剧情和空镜头计划会明确拒绝。
- 新增本机诊断与镜头状态自动回归测试。


## V40.401.0 · Real ComfyUI Render Pipeline
- 借鉴开源项目 Calliope 的本地故事到视频阶段化流程、ai-video-drama-platform 的明确 API/媒体契约，以及 ComfyUI 官方 API 的队列/历史/媒体读取模式；仅参考架构思路，没有复制第三方实现代码。
- ComfyUI 适配器从“提交队列即返回”升级为等待执行完成、读取历史输出、下载真实媒体到项目本地目录。
- 图片、视频和音频输出使用安全文件名写入本地；空输出、无可下载媒体、超时和下载失败均明确报错。
- ComfyUI 生成地址默认并限制为 localhost/127.0.0.1/::1，避免把生产工作流提交到意外的外部服务。
- 镜头不能再因为 ComfyUI 仅接受了排队请求就标记完成；必须有非空、可验证的本地媒体文件。
- 新增 ComfyUI 渲染下载契约、外部地址拒绝和空输出阻断测试。
- 参考项目：
  - https://github.com/benjiyaya/Calliope
  - https://github.com/dc-tw/ai-video-drama-platform
  - https://github.com/Comfy-Org/ComfyUI


## V40.402.0 · Reliable Episode Assembly
- 参考 Calliope 的镜头级素材管理与 FFmpeg 成片导出思路，以及 ai-video-drama-platform 的明确媒体输入/输出契约；参考其架构，不直接复制第三方源文件。
- 单集剪辑按镜头顺序收集真实视频；没有视频但有有效分镜图时，使用本地 FFmpeg 将图片转换成指定时长的 H.264 MP4 镜头，再进入拼接流程。该回退是动态漫静帧镜头，不冒充 AI 动态视频。
- 拼接前不再静默丢弃不存在或为空的素材；先尝试无损拼接，编码不兼容时自动尝试统一 H.264/AAC 编码，并返回明确失败信息。
- 清理临时拼接清单；统一验证输出文件存在且非空；字幕烧录输出改为可写入 MP4 的 H.264 编码。
- 增加本地媒体引擎回归测试，覆盖缺失输入、拼接编码回退、静帧视频输入校验和空文件拒绝。
- 参考项目： https://github.com/benjiyaya/Calliope 、https://github.com/dc-tw/ai-video-drama-platform 、https://github.com/Comfy-Org/ComfyUI


## V40.403.0 · Canonical Timeline & QC
- 参考 MIT 许可的 [Comic-drama](https://github.com/tccnnd/Comic-drama) 的 canonical timeline 契约：把镜头顺序、时间范围、素材路径和真实视频/静帧回退来源写入标准 JSON；本版本实现适配 SciCloud 数据结构，没有整段复制第三方实现。
- 每集生成 `canonical_timeline.json`，记录镜头 ID、连续时间码、视觉提示词、媒体路径、真实视频/静帧回退标记，以及可追溯的音频素材。
- 成片质检改为通过 FFprobe 检查真实媒体时长、视频流和目标时长偏差；仅有非空文件但没有可识别视频流，不再视为质检通过。
- 发布包纳入时间线、流水线快照和成片，并为每个打包素材生成 SHA-256 清单，方便校验文件完整性与追踪来源。
- 增加时间线连续性、镜头来源标记和音频素材关联测试。
- 参考源： https://github.com/tccnnd/Comic-drama ，MIT License；本次借鉴其开放时间线契约。第三方源代码如后续直接复用，会保留对应版权与许可声明。


## V40.404.0 · Shot Duration Lock
- 参考 MIT 许可的 Comic-drama 时间线/镜头契约，并结合 MIT 许可的 AI-Short-Drama-Studio 中素材与后期流程的公开设计思路；未复制其整段实现代码。参考：https://github.com/tccnnd/Comic-drama 、https://github.com/JerrIsTheBesta/AI-Short-Drama-Studio
- 单集剪辑阶段将每个镜头按导演分镜计划时长标准化，并统一输出画幅、帧率和像素格式；过短视频使用末帧延展，超长视频按目标时长裁切，避免镜头实际时长偏离计划。
- 标准化前后通过 FFprobe 检查媒体；标准化失败会阻断流水线并保留错误详情，不会继续发布错误时长的成片。
- 若输入镜头带音轨，则按镜头目标时长补齐/裁切音频；没有音轨的镜头保持无音轨，不伪造配音。最终成片仍须通过目标总时长 QC。
- 新增镜头标准化单元测试；CI 结果只验证代码与自动化测试，不代表已在用户的 Mac 上完成真实 ComfyUI/模型渲染。


## V40.405.0 · Dialogue Timeline & Audio Mix
- 从镜头规格中的对白字段生成与镜头绝对时间码对齐的 SRT 字幕；支持字符串对白、带说话人字段的对白对象和对白列表。
- 汇总每个镜头已登记的有效音频素材，按镜头在单集时间线中的起始时间延迟定位，并使用本地 FFmpeg 混合成对白音轨；不会把缺失音频伪装成配音。
- 将对白音轨叠加到成片原有音轨上，保留原视频音频并降低底音轨音量；没有原音轨时直接使用对白音轨。
- 有对白时自动烧录字幕，并把 SRT、对白混音、canonical timeline、成片和 SHA-256 清单一并放入发布包。
- 参考 MIT 许可的 [Comic-drama](https://github.com/tccnnd/Comic-drama) 时间线契约、[LocalMiniDrama](https://github.com/xuanyustudio/LocalMiniDrama) 的阶段化/可恢复制作流程，以及 [tv-series-pipeline](https://github.com/creativeone86/tv-series-pipeline) 的分角色对白、时间轴和字幕工作流。为减少重复开发，`core/otio_export.py` 直接复用了 Comic-drama `backend/timeline_export.py` 中的 OTIO 时间/片段辅助代码并适配 SciCloud 时间线；第三方 MIT 版权与许可全文保存在 `THIRD_PARTY_NOTICES.md`。
- 新增对白绝对时间码、音轨延迟混音、原音轨保留的回归测试。CI 通过不代表已在用户 Mac 上完成真实模型渲染或中文字体显示验收。
