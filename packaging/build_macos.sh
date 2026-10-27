#!/bin/bash
# Build a standalone macOS .app for SciCloud AGI V40 (personal use).
#
# Usage (on your Mac, from the repository/install directory):
#   bash packaging/build_macos.sh
#
# Output:
#   dist/SciCloud AGI V40.app   -- double-click it to launch, or drag
#                                  it to /Applications.
#
# What this script does, and does NOT do:
# - macOS only. It refuses to run on any other platform.
# - Builds in an isolated venv under build/.packaging-venv (ignored by
#   git). PyInstaller and the runtime deps (requirements.txt) are
#   installed only into that venv; requirements.txt itself is NOT
#   changed, and nothing is installed into your system python.
# - Uses PyInstaller onedir (see packaging/SciCloudAGI.spec). It never
#   copies, moves or deletes projects/, data/, output/, logs/ or
#   backups/: those are user data, they are not bundled, and the
#   packaged app resolves them at runtime (see core/config.py and
#   packaging/README.md).
# - Does NOT sign, notarize, or make a DMG. This is an unsigned
#   local build for your own Mac. Do not send it to other people to
#   install.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "错误：packaging/build_macos.sh 只能在 macOS 上运行。" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：未找到 python3，请先安装 Python 3。" >&2
  exit 1
fi

# 构建用 python 的选择，实测结论，不要改回 PATH 第一个 python3：
# 在 James 的 Mac 上，Terminal 的 python3 和 /usr/bin/python3 实际都走
# CommandLineTools 的 Python 3.9 框架，用它建虚拟环境两次都失败：
# venv 在读取一个用户 site 的 .pth 时因非 UTF-8 字节（byte 0xb0）直接
# 崩掉，logs/build.log 里有完整 traceback，dist/ 没有产出。
# 第三次改用 Homebrew python3.12 建虚拟环境才成功：
# PyInstaller 6.22.3、Python 3.12.16、macOS-15.1.1-arm64，
# 产出 dist/SciCloud AGI V40.app，大小 220M。
# 同时忽略用户 site，避免那个坏 .pth 再把 venv 拖崩。
export PYTHONNOUSERSITE=1
export PYTHONUTF8=1
BUILD_PYTHON=""
for candidate in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3 /usr/bin/python3; do
  if [ -x "$candidate" ]; then BUILD_PYTHON="$candidate"; break; fi
done
if [ -z "$BUILD_PYTHON" ]; then BUILD_PYTHON="$(command -v python3)"; fi
echo "构建用 python：$BUILD_PYTHON"

VENV="$ROOT/build/.packaging-venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "创建构建虚拟环境：$VENV"
  mkdir -p "$ROOT/build"
  "$BUILD_PYTHON" -m venv "$VENV"
fi

# Build-only installs. This does not touch requirements.txt and does
# not install anything into the system python.
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r "$ROOT/requirements.txt" pyinstaller

echo "运行 PyInstaller（onedir，见 packaging/SciCloudAGI.spec）……"
"$VENV/bin/python" -m PyInstaller --noconfirm \
  --distpath "$ROOT/dist" --workpath "$ROOT/build" \
  "$ROOT/packaging/SciCloudAGI.spec"

APP="$ROOT/dist/SciCloud AGI V40.app"
if [ ! -d "$APP" ]; then
  echo "错误：构建后未找到 $APP。" >&2
  exit 1
fi

# Guard: user data must never end up inside the bundle. If a future
# spec change bundles one of these by mistake, fail loudly here
# instead of shipping a bundle that swallows the user's data.
BUNDLE_INTERNAL="$APP/Contents/MacOS"
for user_dir in projects data output logs backups; do
  if [ -e "$BUNDLE_INTERNAL/$user_dir" ]; then
    echo "错误：打包产物里出现了用户数据目录 $user_dir，构建已中止。" >&2
    exit 1
  fi
done

echo ""
echo "构建完成："
echo "  $APP"
echo "大小：$(du -sh "$APP" | cut -f1)"
echo ""
echo "启动：双击上面的 .app，或把它拖到“应用程序”文件夹后再从程序坞打开。"
echo "数据：打包版默认用 ~/SciCloud AGI V40；想继续用旧安装目录的数据，"
echo "      见 packaging/README.md（SCICLOUD_HOME，或一次性复制旧数据）。"
echo "注意：这是未签名的本地构建，仅供自己用，不要发给别人安装。"
