#!/usr/bin/env python3
"""用 adb 操作安卓手机的小客户端:截屏 / 列屏幕元素 / 点击 / 输入 / 滑动 / 按键 / 启动 App / 装 APK / 查权限。

坐标是手机屏幕像素(adb 用的就是像素)。连了多台时用环境变量 ANDROID_SERIAL=<序列号> 指定。
用法:
  a.py devices                  列出已连接设备(序列号 / 型号)
  a.py shot out.png             截屏
  a.py labels [N]               列出屏幕上的文字 / 描述和中心坐标(找按钮最快)
  a.py tap X Y                  点击
  a.py find "文字"              找到含该文字的元素并点它的中心
  a.py swipe X1 Y1 X2 Y2 [ms]   滑动
  a.py type "ascii文字"         输入(adb 只支持 ASCII;中文请在 scrcpy 窗口里用键盘输入)
  a.py key back|home|enter|recent|power|wake
  a.py launch <包名>            启动 App
  a.py install <apk路径>        安装 / 覆盖安装 APK
  a.py perms <包名>             看这个 App 的运行时权限授予情况
  a.py grant <包名> <权限>      授权,如 android.permission.RECEIVE_SMS
"""
import os, re, signal, subprocess, sys, xml.etree.ElementTree as ET

signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # 输出接 head 等被截断时安静退出

ADB = os.environ.get("ADB", "adb")


def adb(*args, binary=False, check=True):
    r = subprocess.run([ADB, *args], capture_output=True)
    if check and r.returncode != 0:
        sys.exit((r.stderr or r.stdout).decode(errors="ignore").strip() or f"adb {' '.join(args)} 失败")
    return r.stdout if binary else r.stdout.decode(errors="ignore")


def dump_nodes():
    adb("shell", "uiautomator", "dump", "/sdcard/__ui.xml")
    xml = adb("exec-out", "cat", "/sdcard/__ui.xml")
    adb("shell", "rm", "-f", "/sdcard/__ui.xml", check=False)
    out = []
    for n in ET.fromstring(xml[xml.index("<"):]).iter("node"):
        text = n.get("text") or n.get("content-desc") or ""
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds", ""))
        if text.strip() and m:
            x1, y1, x2, y2 = map(int, m.groups())
            out.append((text.strip(), (x1 + x2) // 2, (y1 + y2) // 2, n.get("class", "").split(".")[-1], n.get("clickable")))
    return out


KEYS = {"back": 4, "home": 3, "enter": 66, "recent": 187, "power": 26, "wake": 224}


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    c, a = sys.argv[1], sys.argv[2:]
    if c == "devices":
        for line in adb("devices", "-l").splitlines()[1:]:
            if line.strip(): print(line)
    elif c == "shot":
        out = a[0] if a else "shot.png"
        open(out, "wb").write(adb("exec-out", "screencap", "-p", binary=True)); print("saved", out)
    elif c == "labels":
        for t, x, y, cls, ck in dump_nodes()[: int(a[0]) if a else 80]:
            print(f"{cls:<16} {t[:40]!r} @({x},{y}){' 可点' if ck == 'true' else ''}")
    elif c == "tap":
        adb("shell", "input", "tap", a[0], a[1]); print("tapped", a[0], a[1])
    elif c == "find":
        hits = [n for n in dump_nodes() if a[0] in n[0]]
        if not hits: print("NOT FOUND"); return
        t, x, y, *_ = hits[0]; adb("shell", "input", "tap", str(x), str(y)); print(f"tapped {t!r} @({x},{y})")
    elif c == "swipe":
        ms = a[4] if len(a) > 4 else "300"; adb("shell", "input", "swipe", *a[:4], ms); print("swiped")
    elif c == "type":
        if any(ord(ch) > 127 for ch in a[0]): sys.exit("adb input text 不支持中文:在 scrcpy 窗口里用键盘输入")
        adb("shell", "input", "text", a[0].replace(" ", "%s")); print("typed")
    elif c == "key":
        adb("shell", "input", "keyevent", str(KEYS.get(a[0], a[0]))); print("key", a[0])
    elif c == "launch":
        adb("shell", "monkey", "-p", a[0], "-c", "android.intent.category.LAUNCHER", "1"); print("launched", a[0])
    elif c == "install":
        print(adb("install", "-r", a[0]).strip())
    elif c == "perms":
        txt = adb("shell", "dumpsys", "package", a[0])
        for line in txt.splitlines():
            if "permission" in line and "granted=" in line: print(line.strip())
    elif c == "grant":
        adb("shell", "pm", "grant", a[0], a[1]); print("granted", a[1])
    else:
        print("未知命令:", c); print(__doc__)


if __name__ == "__main__":
    main()
