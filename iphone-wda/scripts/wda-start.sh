#!/bin/zsh
# 启动 WebDriverAgent 并把手机 8100 端口转到 Mac。
# 用法: wda-start.sh [UDID] [--rebuild]
#   UDID 省略时取 idevice_id -l 的第一台;--rebuild 强制重编(签名过期 / 换证书)。
# 签名团队:优先用环境变量 WDA_TEAM;没设就从本机第一张「Apple Development」证书里自动读 OU。
# bundle id:优先 WDA_BUNDLE,默认 com.<本机用户名>.wda.runner(随便起,不和别人撞就行)。
# 编译产物缓存在 ~/Library/Caches/iphone-wda,不放任何仓库工作区。
set -u
C=~/Library/Caches/iphone-wda
UDID=""; REBUILD=0
for a in "$@"; do [[ $a == --rebuild ]] && REBUILD=1 || UDID=$a; done

for t in idevice_id iproxy xcodebuild; do
  command -v $t >/dev/null || { echo "缺少 $t:先装 Xcode 和 libimobiledevice(brew install libimobiledevice)"; exit 1; }
done
[[ -z $UDID ]] && UDID=$(idevice_id -l | head -1)
[[ -z $UDID ]] && { echo "没找到真机:检查数据线、手机上点「信任此电脑」"; exit 1; }

TEAM=${WDA_TEAM:-}
if [[ -z $TEAM ]]; then
  CERT=$(security find-identity -v -p codesigning | grep -m1 "Apple Development" | sed -E 's/.*"(.*)".*/\1/')
  [[ -z $CERT ]] && { echo "本机没有 Apple Development 证书:在 Xcode → Settings → Accounts 登录 Apple ID 后再试,或设 WDA_TEAM"; exit 1; }
  TEAM=$(security find-certificate -c "$CERT" -p | openssl x509 -noout -subject | sed -nE 's/.*OU ?= ?([A-Z0-9]{10}).*/\1/p')
  [[ -z $TEAM ]] && { echo "没读出团队 ID,手动设 WDA_TEAM=<10 位团队 ID>"; exit 1; }
fi
BUNDLE=${WDA_BUNDLE:-com.$(whoami | tr -cd 'a-zA-Z0-9').wda.runner}
mkdir -p $C

if curl -s -m 3 http://localhost:8100/status >/dev/null 2>&1; then echo "WDA 已在运行(8100 通)"; exit 0; fi

if [[ ! -d $C/WebDriverAgent ]]; then
  git clone -q --depth 1 https://github.com/appium/WebDriverAgent.git $C/WebDriverAgent || exit 1
fi
xs=($C/dd/Build/Products/*.xctestrun(N)); X=${xs[1]:-}
# 免费 / 个人开发证书签名 7 天过期:产物超过 6 天就重编
if [[ -n $X && $REBUILD == 0 ]] && [[ $(( ($(date +%s) - $(stat -f %m "$X")) / 86400 )) -ge 6 ]]; then
  echo "上次编译已超过 6 天,签名快过期,重编"; REBUILD=1
fi
if [[ -z $X || $REBUILD == 1 ]]; then
  echo "编译 WDA(约 1 分钟,团队 $TEAM)…"
  (cd $C/WebDriverAgent && xcodebuild build-for-testing \
    -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner \
    -destination "id=$UDID" -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
    DEVELOPMENT_TEAM=$TEAM CODE_SIGN_STYLE=Automatic PRODUCT_BUNDLE_IDENTIFIER=$BUNDLE \
    -derivedDataPath $C/dd > $C/build.log 2>&1)
  if ! grep -q "TEST BUILD SUCCEEDED" $C/build.log; then
    echo "编译失败,看 $C/build.log:"; grep -E "error:|Developer Mode|isn't registered|license" $C/build.log | tail -5; exit 1
  fi
  xs=($C/dd/Build/Products/*.xctestrun(N)); X=${xs[1]:-}
fi

pkill -f "xcodebuild test-without-building" 2>/dev/null; pkill -f "iproxy 8100" 2>/dev/null
nohup xcodebuild test-without-building -xctestrun "$X" -destination "id=$UDID" > $C/wda-run.log 2>&1 &
nohup iproxy 8100 8100 -u $UDID > $C/iproxy.log 2>&1 &
for i in {1..45}; do
  sleep 2
  curl -s -m 3 http://localhost:8100/status >/dev/null 2>&1 && { echo "WDA 已启动:http://localhost:8100($UDID)"; exit 0; }
  grep -q -E "Unlock|Locked" $C/wda-run.log 2>/dev/null && { echo "手机锁屏了:解锁后重跑"; exit 1; }
  grep -q "Developer Mode disabled" $C/wda-run.log 2>/dev/null && { echo "手机没开开发者模式:设置→隐私与安全性→开发者模式"; exit 1; }
done
echo "90 秒内没起来,看 $C/wda-run.log 末尾:"; tail -5 $C/wda-run.log; exit 1
