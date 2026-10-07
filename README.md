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
