#!/bin/zsh
# 启动 WebDriverAgent 并把手机 8100 端口转到 Mac。
# 用法: wda-start.sh [UDID] [--rebuild]
#   UDID 省略时取 idevice_id -l 的第一台;--rebuild 强制重编(签名过期 / 换证书)。
# 签名团队:优先用环境变量 WDA_TEAM;没设就从本机第一张「Apple Development」证书里自动读 OU。
# bundle id:优先 WDA_BUNDLE,默认 com.<本机用户名>.wda.runner.<团队 ID>(带团队 ID,不会和别人撞)。
# 编译产物缓存在 ~/Library/Caches/iphone-wda,不放任何仓库工作区。
#
# 安全:WDA 默认对手机所在的整个 Wi-Fi 开放、不要密码,同一网络里谁都能截屏、点按。
# 这里让它只听手机本机(127.0.0.1),Mac 只经数据线(iproxy)连过去:
#   - 操控端口 8100:运行时传 USE_IP=127.0.0.1
#   - 截屏推流端口 9100:上游不认 USE_IP,固定 WDA 版本后打一行补丁让它也只听 127.0.0.1
set -u
C=~/Library/Caches/iphone-wda
WDA_REPO=https://github.com/appium/WebDriverAgent.git
WDA_REV=d15c0b2dbaa850fa712fba817e51cf8d5026d9f2   # 2026-10-08 的 master,实测过;升级时连补丁一起验
UDID=""; REBUILD=0
for a in "$@"; do [[ $a == --rebuild ]] && REBUILD=1 || UDID=$a; done

for t in idevice_id iproxy xcodebuild git; do
  command -v $t >/dev/null || { echo "缺少 $t:先装 Xcode 和 libimobiledevice(brew install libimobiledevice)"; exit 1; }
done
[[ -z $UDID ]] && UDID=$(idevice_id -l | head -1)
[[ -z $UDID ]] && { echo "没找到真机:检查数据线、手机上点「信任此电脑」"; exit 1; }

TEAM=${WDA_TEAM:-}
if [[ -z $TEAM ]]; then
  CERT=$(security find-identity -v -p codesigning | grep -m1 "Apple Development" | sed -E 's/.*"(.*)".*/\1/')
  [[ -z $CERT ]] && { echo "本机没有 Apple Development 证书。只登录 Apple ID 还不够:Xcode → Settings → Accounts → 选中你的团队 → Manage Certificates → 左下角 + → Apple Development,建好再重跑。或者设 WDA_TEAM=<10 位团队 ID>"; exit 1; }
  TEAM=$(security find-certificate -c "$CERT" -p | openssl x509 -noout -subject | sed -nE 's/.*OU ?= ?([A-Z0-9]{10}).*/\1/p')
  [[ -z $TEAM ]] && { echo "没读出团队 ID,手动设 WDA_TEAM=<10 位团队 ID>"; exit 1; }
fi
BUNDLE=${WDA_BUNDLE:-com.$(whoami | tr -cd 'a-zA-Z0-9').wda.runner.$TEAM}
STAMP="$WDA_REV $UDID $TEAM $BUNDLE patched"   # 编译输入:任何一项变了都要重编
mkdir -p $C

# 8100 上有东西在跑:确认是自己起的 WDA、连的是这台手机、签名设置也没变,才直接复用
if curl -s -m 3 -o /dev/null http://localhost:8100/status 2>/dev/null; then
  if [[ $REBUILD == 0 && -f $C/running && "$(cat $C/running)" == "$UDID" && "$(cat $C/build.stamp 2>/dev/null)" == "$STAMP" ]] &&
     curl -sf -m 3 http://localhost:8100/status 2>/dev/null | grep -q '"sessionId"'; then
    echo "WDA 已在运行(8100 通,$UDID)"; exit 0
  fi
  if [[ -f $C/running ]]; then
    echo "8100 上是之前起的 WDA,但手机、签名设置不同或要重编:先关掉再启动"
    ${0:A:h}/wda-stop.sh >/dev/null
  fi
  if curl -s -m 3 -o /dev/null http://localhost:8100/status 2>/dev/null; then
    echo "8100 端口被别的程序占着(不是这里起的 WDA):先关掉它再重跑。查是谁:lsof -nP -iTCP:8100 -sTCP:LISTEN"
    exit 1
  fi
fi

# 取固定版本的 WDA 源码,打补丁:截屏推流端口也只听 USE_IP 指定的地址
W=$C/WebDriverAgent
if [[ ! -d $W/.git || "$(git -C $W rev-parse HEAD 2>/dev/null)" != $WDA_REV ]]; then
  rm -rf $W; mkdir -p $W
  { git -C $W init -q && git -C $W fetch -q --depth 1 $WDA_REPO $WDA_REV && git -C $W checkout -q FETCH_HEAD; } ||
    { echo "下载 WebDriverAgent 失败(网络?)"; rm -rf $W; exit 1; }
fi
F=$W/WebDriverAgentLib/Routing/FBWebServer.m
P='self.screenshotsBroadcaster.interface = FBConfiguration.sharedInstance.bindingIPAddress;'
if ! grep -qF "$P" $F; then
  git -C $W checkout -q -- $F
  /usr/bin/sed -i '' "/initWithPort:(uint16_t)FBConfiguration.sharedInstance.mjpegServerPort\];/a\\
  $P
" $F
  grep -qF "$P" $F || { echo "给 WDA 打补丁失败,不启动(否则截屏推流会对整个 Wi-Fi 开放)"; exit 1; }
  REBUILD=1
fi

xs=($C/dd/Build/Products/*.xctestrun(N)); X=${xs[1]:-}
if [[ -n $X && $REBUILD == 0 && "$(cat $C/build.stamp 2>/dev/null)" != "$STAMP" ]]; then
  echo "手机、签名或 WDA 版本和上次编译时不同,重编"; REBUILD=1
fi
# 免费 / 个人开发证书签名 7 天过期:上次编译超过 6 天就重编。
# 按 build.stamp 算(每次编译成功才写);.xctestrun 内容没变时 xcodebuild 不重写它,看它的时间会一直判成过期
if [[ -n $X && $REBUILD == 0 ]] && [[ $(( ($(date +%s) - $(stat -f %m $C/build.stamp)) / 86400 )) -ge 6 ]]; then
  echo "上次编译已超过 6 天,签名快过期,重编"; REBUILD=1
fi
if [[ -z $X || $REBUILD == 1 ]]; then
  echo "编译 WDA(约 1 分钟,团队 $TEAM)…"
  rm -f $C/build.stamp
  (cd $W && xcodebuild build-for-testing \
    -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner \
    -destination "id=$UDID" -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
    DEVELOPMENT_TEAM=$TEAM CODE_SIGN_STYLE=Automatic PRODUCT_BUNDLE_IDENTIFIER=$BUNDLE \
    -derivedDataPath $C/dd > $C/build.log 2>&1)
  if ! grep -q "TEST BUILD SUCCEEDED" $C/build.log; then
    echo "编译失败,看 $C/build.log:"; grep -E "error:|Developer Mode|isn't registered|license" $C/build.log | tail -5; exit 1
  fi
  xs=($C/dd/Build/Products/*.xctestrun(N)); X=${xs[1]:-}
  print -r -- "$STAMP" > $C/build.stamp
fi

# 只关这里之前起的那一套,不碰本机别的 xcodebuild / iproxy
${0:A:h}/wda-stop.sh >/dev/null
# TEST_RUNNER_ 开头的环境变量,xcodebuild 会去掉前缀传给手机上的测试进程
TEST_RUNNER_USE_IP=127.0.0.1 nohup xcodebuild test-without-building -xctestrun "$X" -destination "id=$UDID" > $C/wda-run.log 2>&1 &
print $! > $C/xcodebuild.pid
nohup iproxy 8100 8100 -u $UDID > $C/iproxy.log 2>&1 &
print $! > $C/iproxy.pid
sleep 1
kill -0 $(<$C/iproxy.pid) 2>/dev/null || {
  echo "端口转发没起来,多半是 8100 被别的程序占着(比如旧版脚本留下的 iproxy)。查是谁:lsof -nP -iTCP:8100 -sTCP:LISTEN"
  ${0:A:h}/wda-stop.sh >/dev/null; exit 1; }
print -r -- "$UDID" > $C/running
for i in {1..45}; do
  sleep 2
  if curl -s -m 3 http://localhost:8100/status >/dev/null 2>&1; then
    grep -q "Using custom binding IP address: 127.0.0.1" $C/wda-run.log 2>/dev/null ||
      { echo "WDA 起来了,但没确认到它只听手机本机,为安全先关掉。看 $C/wda-run.log"; ${0:A:h}/wda-stop.sh >/dev/null; exit 1; }
    echo "WDA 已启动:http://localhost:8100($UDID,只经数据线访问)"; exit 0
  fi
  grep -q -E "Unlock|Locked" $C/wda-run.log 2>/dev/null && { echo "手机锁屏了:解锁后重跑"; ${0:A:h}/wda-stop.sh >/dev/null; exit 1; }
  grep -q "Developer Mode disabled" $C/wda-run.log 2>/dev/null && { echo "手机没开开发者模式:设置→隐私与安全性→开发者模式"; ${0:A:h}/wda-stop.sh >/dev/null; exit 1; }
done
echo "90 秒内没起来,看 $C/wda-run.log 末尾:"; tail -5 $C/wda-run.log; ${0:A:h}/wda-stop.sh >/dev/null; exit 1
