#!/bin/bash
set -e
SOURCE="$(cd "$(dirname "$0")" && pwd)"
DEFAULT="/Volumes/修仙漫剧/SciCloud AGI V40"
TARGET="$DEFAULT"
if [ ! -d "/Volumes/修仙漫剧" ]; then TARGET="$HOME/SciCloud AGI V40"; fi
mkdir -p "$TARGET"
if [ "$SOURCE" != "$TARGET" ]; then
  rsync -a --exclude 'data/' --exclude 'projects/' --exclude 'output/' --exclude 'logs/' --exclude 'backups/' "$SOURCE/" "$TARGET/"
fi
mkdir -p "$TARGET/data" "$TARGET/projects" "$TARGET/output" "$TARGET/logs" "$TARGET/backups"
chmod +x "$TARGET/launch.command" "$TARGET/SciCloud AGI V40.app/Contents/MacOS/SciCloudAGI" 2>/dev/null || true
open "$TARGET/SciCloud AGI V40.app"
