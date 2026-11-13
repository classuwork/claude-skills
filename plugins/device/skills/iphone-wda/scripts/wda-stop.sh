#!/bin/zsh
# 关掉 WDA(手机上的白字提示会消失)和端口转发。
pkill -f "xcodebuild test-without-building" 2>/dev/null
pkill -f "iproxy 8100" 2>/dev/null
rm -f ~/Library/Caches/iphone-wda/.sid
sleep 1
curl -s -m 2 http://localhost:8100/status >/dev/null 2>&1 && echo "8100 还通,手机上同时按住两个音量键几秒强制结束" || echo "已关闭"
