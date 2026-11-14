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
import os, re, shlex, signal, subprocess, sys, xml.etree.ElementTree as ET

signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # 输出接 head 等被截断时安静退出

ADB = os.environ.get("ADB", "adb")


def adb(*args, binary=False, check=True):
    r = subprocess.run([ADB, *args], capture_output=True)
    if check and r.returncode != 0:
        sys.exit((r.stderr or r.stdout).decode(errors="ignore").strip() or f"adb {' '.join(args)} 失败")
    return r.stdout if binary else r.stdout.decode(errors="ignore")


def sh(*args, check=True):
    """在手机上跑命令。adb shell 会把参数拼成一行交给手机的 shell 再解析一遍,
    所以每个参数都要先加引号,不然 ; & ' $() 这类字符会被当成命令执行。"""
    return adb("shell", " ".join(shlex.quote(str(x)) for x in args), check=check)


def num(v):
    if not re.fullmatch(r"\d+", v):
        sys.exit(f"坐标 / 时长要是整数:{v!r}")
    return v


# 飞书 Webhook 是密钥:屏幕文字里出现就打码,不打进对话
HOOK = re.compile(r"(hook/)[\w-]+", re.I)


def safe(t):
    return HOOK.sub(r"\1***", t)


UI = "/data/local/tmp/__ui.xml"  # 别放 /sdcard:那里别的 App 也能读


def dump_nodes():
    sh("uiautomator", "dump", UI)
    xml = adb("exec-out", "cat", UI)
    sh("rm", "-f", UI, check=False)
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
            print(f"{cls:<16} {safe(t)[:40]!r} @({x},{y}){' 可点' if ck == 'true' else ''}")
    elif c == "tap":
        sh("input", "tap", num(a[0]), num(a[1])); print("tapped", a[0], a[1])
    elif c == "find":
        hits = [n for n in dump_nodes() if a[0] in n[0]]
        if not hits: print("NOT FOUND"); return
        t, x, y, *_ = hits[0]; sh("input", "tap", x, y); print(f"tapped {safe(t)[:40]!r} @({x},{y})")
    elif c == "swipe":
        ms = a[4] if len(a) > 4 else "300"; sh("input", "swipe", *map(num, a[:4]), num(ms)); print("swiped")
    elif c == "type":
        if any(ord(ch) > 127 for ch in a[0]): sys.exit("adb input text 不支持中文:在 scrcpy 窗口里用键盘输入")
        sh("input", "text", a[0].replace(" ", "%s")); print("typed")
    elif c == "key":
        k = str(KEYS.get(a[0], a[0]))
        if not k.isdigit(): sys.exit(f"不认识的按键:{a[0]}(可用 {'/'.join(KEYS)} 或数字键码)")
        sh("input", "keyevent", k); print("key", a[0])
    elif c == "launch":
        sh("monkey", "-p", a[0], "-c", "android.intent.category.LAUNCHER", "1"); print("launched", a[0])
    elif c == "install":
        print(adb("install", "-r", a[0]).strip())
    elif c == "perms":
        txt = sh("dumpsys", "package", a[0])
        for line in txt.splitlines():
            if "permission" in line and "granted=" in line: print(line.strip())
    elif c == "grant":
        sh("pm", "grant", a[0], a[1]); print("granted", a[1])
    else:
        print("未知命令:", c); print(__doc__)


if __name__ == "__main__":
    main()
