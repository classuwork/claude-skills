#!/bin/zsh
# 从 SmsForwarder 官方 GitHub Release 下载最新 APK 并核对 SHA-256。
# 用法: get-apk.sh [abi]   abi 默认 arm64-v8a(红米 K40 等 64 位机);老机器可用 armeabi-v7a
# 下载到 ~/Downloads/SmsForwarder/,打印本地路径。核对不上就删掉文件并退出。
set -eu
ABI=${1:-arm64-v8a}
OUT=~/Downloads/SmsForwarder; mkdir -p $OUT
J=$(curl -fsSL https://api.github.com/repos/pppscn/SmsForwarder/releases/latest)
TAG=$(print -r -- "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['tag_name'])")
read URL NAME DIGEST <<< $(print -r -- "$J" | python3 -c "
import json,sys
j=json.load(sys.stdin); abi=sys.argv[1]
a=[x for x in j['assets'] if x['name'].endswith('.apk') and abi in x['name']]
if not a: sys.exit('没找到 '+abi+' 的 APK')
x=a[0]; print(x['browser_download_url'], x['name'], (x.get('digest') or '-'))" $ABI)
echo "最新版 $TAG:$NAME"
curl -fsSL -o "$OUT/$NAME" "$URL"
LOCAL=$(shasum -a 256 "$OUT/$NAME" | cut -d' ' -f1)
if [[ $DIGEST == sha256:* ]]; then
  [[ ${DIGEST#sha256:} == $LOCAL ]] || { rm -f "$OUT/$NAME"; echo "SHA-256 不一致,已删除"; exit 1; }
  echo "SHA-256 与 GitHub 公布的一致:$LOCAL"
else
  echo "GitHub 没公布这个文件的摘要,本地 SHA-256:$LOCAL(请到 Release 页人工对照)"
fi
echo "$OUT/$NAME"
