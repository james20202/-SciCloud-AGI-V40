# SciCloud AGI V40 · macOS 打包版（自己用）

这是一套**本地打包工具链**，不是发给别人的安装包。它把 SciCloud
打成一个真正独立的 `.app`：以后双击图标就能开，不用再开
Terminal、不用再手动 pip、不用再点 `launch.command`。

**明确不是什么：未签名、未公证、没有 DMG、没有上架。**
这是你自己在自己 Mac 上构建、自己用的版本，**不要发给别人装**。
也不要为了绕过拦截去关 Gatekeeper，或者用危险命令强行绕过
签名验证——下面有安全的打开方法。

## 构建（在你的 Mac 上，一条命令）

在仓库/安装目录里运行：

```bash
bash packaging/build_macos.sh
```

构建脚本只在 macOS 上跑，会：

1. 在 `build/.packaging-venv/` 里建一个隔离的构建虚拟环境，
   把 PyInstaller 和运行依赖（`requirements.txt` 里的 PySide6 /
   Pillow）只装到这个虚拟环境里；**不改 `requirements.txt`，
   不往系统 python 里装东西**；
2. 用 PyInstaller onedir 方式构建（见 `SciCloudAGI.spec`，不是
   onefile：PySide6 用 onefile 启动慢、Qt 插件容易出问题）；
3. 产出 `dist/SciCloud AGI V40.app`，并打印路径和大小。

构建时间取决于机器，PySide6 的包不小，第一次构建请耐心等它跑完。

## 启动

- 双击 `dist/SciCloud AGI V40.app`，或把它拖到“应用程序”
  文件夹，再从程序坞打开。正常情况下不会再弹出 Terminal 窗口。
- 第一次打开如果 macOS 拦截：**不要关 Gatekeeper**。本地构建的
  app 一般不带下载隔离属性；如果仍被拦截，在 Finder 里对它点
  **右键 → 打开**，在弹出的确认框里再点一次“打开”即可。
  这是一次性的本机确认，不是绕过签名验证的通用操作。

## 数据放在哪（重要，先看这一节）

打包版**不会**把你的项目和数据打进 `.app` 包里，也不会在构建
时清空它们。构建脚本只写 `build/` 和 `dist/`，从来不碰
`projects/`、`data/`、`output/`、`logs/`、`backups/`。

打包版运行时的数据目录按 `core/config.py` 的规则定：

| 情况 | 数据目录 |
| --- | --- |
| 设置了 `SCICLOUD_HOME` 环境变量 | 就是那个目录 |
| 打包版（PyInstaller）且没设 `SCICLOUD_HOME` | `~/SciCloud AGI V40`（家目录下，和包分开，移动 .app 也不丢数据） |
| 源码版（`python main.py` / `launch.command`） | 安装目录本身（老行为，不变） |

所以第一次用打包版时，它默认是一个**新的空数据目录**
（`~/SciCloud AGI V40`），旧项目不会自动出现。要继续用旧数据，
二选一，做一次就行：

1. **推荐，改动最小**：把旧安装目录里的 `projects/`、`data/`、
   `output/` 一次性复制到 `~/SciCloud AGI V40/` 里；或者
2. 设 `SCICLOUD_HOME` 指向旧安装目录，例如旧目录是
   `/Volumes/修仙漫剧/SciCloud AGI V40` 时，让打包版启动时带上
   这个环境变量（用 Automator / 启动脚本包一层即可）。

## 还是要本机另行准备的东西

打包只解决了“应用本身一键启动”，下面这些是本机外部服务，
打包版**不会**替你启动，也**不会**打进包里：

- FFmpeg / FFprobe：剪辑与质检要用，本机装好即可；
- ComfyUI：图片/视频渲染走 `http://127.0.0.1:8188`，要自己先启动；
- Ollama：本地导演模型走本机 Ollama，要自己先启动；
- 云端 LLM 适配器：默认仍是关闭的，和打包无关，开启方式不变。

## 打包版不要用应用内 ZIP 升级

源码版的“检查在线更新 / 导入 ZIP 升级包”是针对源码安装的：
它会把新源码解压并用 `apply_update.py` 覆盖安装目录。打包版
里没有源码安装目录可覆盖，点了会报错。**打包版要升级时，
重新跑一次 `bash packaging/build_macos.sh` 即可**，不要在打包版
里点 ZIP 升级。

## 构建后要回告的检查点

这个打包支持目前**没有在 Mac 上实测过**（开发环境不是 Mac，
CI 也不是 Mac 构建机）。James 在 Mac 上构建后，请确认并回告：

1. `bash packaging/build_macos.sh` 能跑完，`dist/` 里有
   `SciCloud AGI V40.app`；
2. 双击 .app 能打开，不弹 Terminal、不弹缺依赖的框；
3. 系统中心里显示的版本号是对的；
4. 能进创作页和生产页，旧项目按上面“数据放在哪”一节处理后
   能正常看到。
