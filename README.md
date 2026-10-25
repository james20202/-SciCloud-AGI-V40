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


## V40.406.0 · Consistency Bible & Resumable Shot Jobs
- 新增本地一致性圣经：从导演计划提取稳定人物 ID、外观、服装、标志特征、场景 ID、场景视觉锚点、光照与色彩锚点，并注入每个镜头的规格/视觉提示词；未明确关联的人物不会被系统臆测绑定。
- 镜头任务保存输入指纹。断点续跑时，只有输入未变且输出文件仍存在、非空的镜头才复用；提示词或镜头参数变化会自动失效旧缓存，缺失/空文件不会继续被算作完成。
- 镜头运行状态增加可恢复逻辑：支持继续 ready/blocked/failed 镜头，保留尝试次数、上次错误与有效产物记录；已完成且输入未变的镜头不重复触发生成。
- 增加一致性锚点、输入指纹、缓存失效和素材有效性回归测试。
- 参考 MIT 许可的 [LocalMiniDrama](https://github.com/xuanyustudio/LocalMiniDrama) 对人物/场景资产复用和可重跑工作流的公开设计；本版本相关模块为独立实现，未复制其源文件。此前直接复用的 Comic-drama MIT 代码许可仍见 THIRD_PARTY_NOTICES.md。


## V40.407.0 · SQLite Job Recovery & Production Ledger
- 新增 SQLite 持久化任务账本：任务 ID、类型、状态、进度、消息、结果、错误、创建/更新时间和参数在每次更新后写入本地数据库，跨应用重启保留。
- 镜头生产运行记录同时保存到 SQLite 与原 JSON 文件；SQLite 可作为快速恢复来源，保留旧版 JSON 以兼容既有项目与诊断工具。
- 启动后将上次进程遗留的 queued/running/cancelling 任务标记为 interrupted；镜头运行恢复时把中断中的镜头重新排队，不把旧的 running 状态伪装成正在执行。
- 采用 MIT 项目 StudioLite 的 `filmmaker/job_store.py` 持久化任务存储实现作为直接代码复用基础，保留版权与 MIT 许可证，详见 THIRD_PARTY_NOTICES.md。
- 新增 SQLite 重启恢复、任务更新持久化、JSON/SQLite 镜头运行记录同步和旧版运行记录兼容测试。


## V40.408.0 · Offline TTS & Media Quality Gate

- 新增离线配音适配器：优先使用 macOS 自带 say，也可通过环境变量接入本机 Piper CLI；不会自动下载语音模型、不访问云端接口、不消耗在线 Token。
- 每段对白先剔除括号中的舞台/音效指示；本地 TTS 可用时为对白生成独立音频片段，并按镜头时间线混音。若本机没有可用语音或中文语音，系统明确报告并保留字幕，不会伪造配音成功。
- 新增成片媒体质量扫描：FFprobe 检查视频流、时长、画面尺寸和音频流；FFmpeg 检测长黑帧与长静音，作为人工复核警告，不会把有意黑场或无对白静音直接判成失败。
- QC 结果保存黑帧/静音时间区间、错误码和警告，并继续阻止无效视频流或严重时长偏差的成片进入发布阶段。
- 直接适配 MIT 许可的 creativeone86/tv-series-pipeline/lib/text-control.ts 中对白清理、避免把对白原文塞进画面提示词、CJK 字体发现等辅助逻辑；保留版权与完整 MIT 许可文本，详见 THIRD_PARTY_NOTICES.md。
- 可配置项：SCICLOUD_TTS_BACKEND=auto|say|piper|off、SCICLOUD_TTS_VOICE、SCICLOUD_PIPER_MODEL、CJK_FONT_FILE。Piper 需用户自行安装可执行文件和本地模型；软件不会自动下载。
- 新增本地 TTS、对白清理、提示词净化、黑帧/静音诊断与视频流质检回归测试。CI 自动测试不代表已在用户 Mac 上验证实际语音、中文发音或真实成片渲染。


## V40.409.0 · Character Reference Lock & Continuity Audit

- 素材中心新增“绑定参考图”：可从人物资产直接选角色，导入 PNG/JPG/WEBP/BMP；参考图自动复制进资产目录，登记 SHA-256、尺寸和版本号，原文件不会被移动或覆盖。
- 镜头准备阶段根据明确的角色 ID/名称绑定最新参考图，不猜测未标注角色；每次执行媒体生产前刷新引用，参考图版本变化会改变镜头输入指纹并使旧缓存失效。
- 本地 ComfyUI 参考图注入：仅对明确标记的 LoadImage 节点注入上传图。节点标题使用 `SciCloud Character Ref: <角色ID或名称>`，或把 image 输入设为 `__SCICLOUD_CHARACTER_REFERENCE__:<角色ID>`。未匹配节点时会明确警告，不谎称图片已注入模型。
- 新增参考图覆盖率统计和生成图片对参考图的颜色直方图/结构哈希启发式评分。评分仅用于提示复核，不是人脸识别，也不会单独决定人物身份。
- 从 MIT 许可的 `tccnnd/Comic-drama/backend/consistency_validator.py` 直接适配颜色直方图、平均哈希和汉明相似度算法；版权/许可证信息见 `THIRD_PARTY_NOTICES.md`。
- 增加 Pillow 依赖用于校验图像可解码、读取尺寸和执行启发式图像比较；不下载生成模型、不调用云端图像服务。
- 新增参考图版本管理、工作流节点注入、错误工作流保护、视觉相似度和缺失文件回归测试。


## V40.410.0 · Script Asset Extraction & Selective Shot Recovery

- 新建集成式剧本/导演计划资产提取：从结构化计划自动登记人物、场景、明确列出的道具和每个镜头卡片；保留镜头视觉提示词、对白（含说话人结构）与目标时长，供资产中心和后续生产阶段复用。
- 资产提取按 plan_id + 类型 + 实体 ID 幂等；重复执行不重复堆积相同资产。只提取计划字段中明确存在的实体，不从自由文本臆测人物/道具。
- 单集创建导演计划后自动执行资产提取，并把创建/复用数量写入计划阶段结果，方便诊断与进度追踪。
- 新增按镜头 ID 精准重试：仅重排失败/阻塞镜头；成功镜头的状态、有效产物和缓存不受影响。失败镜头的部分产物只从活动清单移除，不删除磁盘文件。
- 新增自动化测试覆盖资产提取、重复执行、道具去重、对白/提示词保留，以及只重试失败镜头的保护规则。
- 参考并沿用 MIT 许可的 [Comic-drama](https://github.com/tccnnd/Comic-drama) 中结构化剧本→人物/场景/镜头资产的流水线设计；V40.410 的提取器按 SciCloud 的资产登记接口独立适配。已直接复用的 Comic-drama 算法/时间线代码及完整 MIT 许可声明见 `THIRD_PARTY_NOTICES.md`。
- 代码与测试通过 GitHub Actions 不等于已在用户 Mac 上完成完整 ComfyUI 实际渲染；本版本不安装 ComfyUI、不下载模型、不调用云端生成服务。

## V40.411.0 · Episode Acceptance Gate

- 新增纯本地单集时间线验收器，检查视频镜头是否存在、镜头时长是否为正、镜头起止时间是否连续、结束时间是否与起始时间及持续时间一致，以及时间线总时长是否与单集目标相符。
- 单集 QC 现在同时核验成片媒体和 canonical timeline；缺少、损坏或与目标时长明显不符的时间线会阻止发布，并在质检结果中给出结构化错误。
- 新增独立回归测试覆盖有效时间线、间隙/重叠、结束时间错误和空视频轨道。
- 本版本不引入云端模型调用、模型下载或在线 Token 依赖。自动化测试通过不代表已在用户的 Mac 上完成真实 ComfyUI 渲染。
