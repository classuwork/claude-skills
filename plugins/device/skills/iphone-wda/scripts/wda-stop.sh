#!/bin/zsh
# 关掉 WDA(手机上的白字提示会消失)和端口转发。
# 只关 wda-start.sh 自己起的进程(记在 pid 文件里,并核对进程确实是它),不碰本机别的 xcodebuild 测试。
C=~/Library/Caches/iphone-wda
stop() {  # stop <pid 文件> <进程命令行里必须有的一段>
  local f=$1 want=$2 pid
  [[ -f $f ]] || return 0
  pid=$(<$f)
  [[ $pid == <-> ]] && ps -p $pid -o command= 2>/dev/null | grep -qF -- "$want" && kill $pid 2>/dev/null
  rm -f $f
}
stop $C/xcodebuild.pid "test-without-building -xctestrun $C/"
stop $C/iproxy.pid "iproxy 8100 8100"
# 旧版脚本起的 WDA 没有 pid 文件:命令行里带本缓存目录的才是它起的
pkill -f "test-without-building -xctestrun $C/" 2>/dev/null
rm -f $C/.sid $C/running
sleep 1
curl -s -m 2 http://localhost:8100/status >/dev/null 2>&1 && echo "8100 还通,手机上同时按住两个音量键几秒强制结束" || echo "已关闭"
