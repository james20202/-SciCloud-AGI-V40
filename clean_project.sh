#!/bin/bash


echo "================================"
echo "仙剧工坊 V30.5 工程清理"
echo "================================"


DATE=$(date +%Y%m%d_%H%M)

BACKUP="../仙剧工坊V30.5清理前备份_$DATE"


echo "创建安全备份..."

mkdir -p "$BACKUP"


cp -r core "$BACKUP/"
cp -r ui "$BACKUP/"
cp main.py "$BACKUP/"


echo "备份完成:"
echo $BACKUP



echo "开始清理历史备份..."



# 删除目录备份

find . -type d -name "backup_*" -prune -exec rm -rf {} \;


# 删除UI历史版本

find ui -type f -name "*_backup.py" -delete


# 删除core历史版本

find core -type f -name "*_backup.py" -delete



# 删除旧升级脚本

rm -f upgrade_v33.py
rm -f upgrade_v33_ui.py
rm -f upgrade_v34.py
rm -f upgrade_v40.py
rm -f upgrade_v40_ui.py
rm -f upgrade_v50_core.py
rm -f upgrade_v50_ui.py
rm -f upgrade_v51_core.py
rm -f upgrade_v51_context.py
rm -f upgrade_v52_core.py



echo "清理Python缓存..."

find . -type d -name "__pycache__" -exec rm -rf {} \;


find . -type f -name "*.pyc" -delete



echo "================================"
echo "清理完成"
echo "================================"


