#!/bin/sh
# 找一个装好依赖的 Python 来跑 watermark.py,参数原样传过去。
#   1. 系统的 python3 已经有 Pillow(用 --keep-vector 时还要有 pypdf、reportlab)→ 直接用
#   2. 否则用私有虚拟环境;第一次用时自动创建并安装依赖,以后直接复用
# 虚拟环境的位置:$WM_DATA/venv(SKILL.md 把插件数据目录传进来,卸载插件时会一起删掉);
# 没传 WM_DATA 时用 ~/.cache/happy-skills/watermark-venv。
# 这样在 Homebrew / uv 装的 Python 上(pip3 install 会报 externally-managed-environment)也能直接用。
HERE=$(cd "$(dirname "$0")" && pwd)
if [ -n "${WM_DATA:-}" ]; then V="$WM_DATA/venv"; else V="$HOME/.cache/happy-skills/watermark-venv"; fi

MODS="PIL"; PKGS="Pillow"
for a in "$@"; do
  [ "$a" = "--keep-vector" ] && { MODS="PIL pypdf reportlab"; PKGS="Pillow pypdf reportlab"; }
done
has() { "$1" -c "import $(echo $MODS | tr ' ' ',')" 2>/dev/null; }

command -v python3 >/dev/null 2>&1 || { echo "没找到 python3:先装 Python 3.9 以上(Mac 上在终端跑一次 python3,按提示装命令行工具)" >&2; exit 1; }

if has python3; then
  PY=python3
elif [ -x "$V/bin/python" ] && has "$V/bin/python"; then
  PY="$V/bin/python"
else
  { [ -x "$V/bin/python" ] || python3 -m venv "$V"; } ||
    { echo "建虚拟环境失败:$V" >&2; exit 1; }
  # reportlab 5.1 起不支持 Python 3.9(苹果自带的就是 3.9),但安装信息里没写,pip 会照装、一导入就报错
  # ⇒ 装进 3.9 时限定 5.0.x。看的是虚拟环境自己的 Python,不是现在 PATH 上的 python3
  "$V/bin/python" -c "import sys; sys.exit(sys.version_info < (3, 10))" ||
    PKGS=$(echo "$PKGS" | sed 's/reportlab/reportlab<5.1/')
  echo "首次使用:系统 Python 缺少 $PKGS,在 $V 建虚拟环境安装(只装这一次)…" >&2
  # shellcheck disable=SC2086  # PKGS 故意按空格拆成多个包名
  "$V/bin/python" -m pip install -q --disable-pip-version-check $PKGS >&2 || {
    Q=$(for p in $PKGS; do printf " '%s'" "$p"; done)
    echo "自动安装失败(多半是没网或 PyPI 连不上)。可以手动跑:\"$V/bin/python\" -m pip install$Q" >&2
    exit 1
  }
  PY="$V/bin/python"
fi
exec "$PY" "$HERE/watermark.py" "$@"
