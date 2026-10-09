# SciCloud AGI V40

AI内容导演操作系统。本版本基于仙剧工坊 V30.5 升级，保留原生产模块与数据目录。

## 启动

在 Mac 上双击 `launch.command`。首次运行如果缺少依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 低配置 Mac 运行建议

当前项目适合在 MacBook（8GB 内存）上轻量运行，但不建议把大模型、项目缓存、素材输出和日志都塞进系统盘。建议把数据目录统一放到外置 SSD 上，例如：

```bash
/Volumes/修仙漫剧/SciCloud AGI V40
```

建议目录结构：

```bash
/Volumes/修仙漫剧/SciCloud AGI V40/
├── data/
├── projects/
├── output/
├── logs/
├── backups/
└── .env
```

### 环境变量（推荐）

在 macOS 中，可以将下面这些环境变量写入 `~/.zshrc`：

```bash
export SCI_DATA_DIR="/Volumes/修仙漫剧/SciCloud AGI V40/data"
export SCI_PROJECT_DIR="/Volumes/修仙漫剧/SciCloud AGI V40/projects"
export SCI_OUTPUT_DIR="/Volumes/修仙漫剧/SciCloud AGI V40/output"
export SCI_LOG_DIR="/Volumes/修仙漫剧/SciCloud AGI V40/logs"
export SCI_BACKUP_DIR="/Volumes/修仙漫剧/SciCloud AGI V40/backups"
```

然后执行：

```bash
source ~/.zshrc
```

如果路径变更，只需修改环境变量即可，不必改代码。

### 运行建议

- 优先使用小模型 / 低分辨率 / 低步骤数
- 不要在同一时刻同时启动多个大规模生成任务
- 所有大文件输出建议落到外置 SSD，而不是系统盘
- 如有外置盘断开连接，需先重新挂载，再继续渲染或导出

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
