#!/usr/bin/env python3
"""WebDriverAgent 小客户端:截屏 / 列元素 / 点击 / 输入 / 滑动 / 回主屏 / 启动 App。

坐标一律用「点(pt)」,不是截图像素。会话 id 缓存在 ~/Library/Caches/iphone-wda/.sid,失效会自动重建。
用法见 SKILL.md。WDA 地址默认 http://localhost:8100,可用环境变量 WDA_URL 覆盖。
"""
import base64, json, os, sys, urllib.error, urllib.request

U = os.environ.get("WDA_URL", "http://localhost:8100")
HERE = os.path.dirname(os.path.abspath(__file__))
SF = os.path.join(os.environ.get("WDA_STATE_DIR", os.path.expanduser("~/Library/Caches/iphone-wda")), ".sid")


def req(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(U + path, method=method, data=data, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def sid():
    if os.path.exists(SF):
        s = open(SF).read().strip()
        try:
            req("GET", f"/session/{s}/window/size")
            return s
        except Exception:
            pass
    s = req("POST", "/session", {"capabilities": {"alwaysMatch": {}}})["sessionId"]
    os.makedirs(os.path.dirname(SF), exist_ok=True)
    open(SF, "w").write(s)
    return s


def pointer(s, steps):
    req("POST", f"/session/{s}/actions", {"actions": [{"type": "pointer", "id": "f",
        "parameters": {"pointerType": "touch"}, "actions": steps}]})


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    c, a = sys.argv[1], sys.argv[2:]
    if c == "locked":
        print("锁屏中" if req("GET", "/wda/locked", timeout=10).get("value") else "未锁屏")
    elif c == "status":
        print(json.dumps(req("GET", "/status", timeout=10).get("value", {}).get("state", "?")))
    elif c == "shot":
        out = a[0] if a else "shot.png"
        open(out, "wb").write(base64.b64decode(req("GET", "/screenshot")["value"])); print("saved", out)
    elif c == "size":
        print(req("GET", f"/session/{sid()}/window/size")["value"])
    elif c == "tap":
        x, y = float(a[0]), float(a[1])
        pointer(sid(), [{"type": "pointerMove", "duration": 0, "x": x, "y": y}, {"type": "pointerDown"},
                        {"type": "pause", "duration": 80}, {"type": "pointerUp"}]); print("tapped", x, y)
    elif c == "swipe":  # swipe x1 y1 x2 y2 [ms]
        x1, y1, x2, y2 = map(float, a[:4]); ms = int(a[4]) if len(a) > 4 else 300
        pointer(sid(), [{"type": "pointerMove", "duration": 0, "x": x1, "y": y1}, {"type": "pointerDown"},
                        {"type": "pointerMove", "duration": ms, "x": x2, "y": y2}, {"type": "pointerUp"}]); print("swiped")
    elif c == "click":
        s = sid()
        q = "'" + a[0].replace("\\", "\\\\").replace("'", "\\'") + "'"  # 按钮名里有 ' 或 \ 时要转义,否则谓词语法错
        for using, val in (("accessibility id", a[0]),
                           ("predicate string", f"label == {q} OR name == {q}"),
                           ("predicate string", f"label CONTAINS {q}")):
            try:
                e = req("POST", f"/session/{s}/element", {"using": using, "value": val})["value"]
                eid = e.get("ELEMENT") or list(e.values())[0]
                req("POST", f"/session/{s}/element/{eid}/click", {}); print("clicked via", using); break
            except Exception:
                continue
        else:
            sys.exit("NOT FOUND")
    elif c == "type":
        req("POST", f"/session/{sid()}/wda/keys", {"value": list(a[0])}); print("typed")
    elif c == "home":
        req("POST", "/wda/homescreen", {}); print("home")
    elif c == "launch":
        req("POST", f"/session/{sid()}/wda/apps/launch", {"bundleId": a[0]}); print("launched", a[0])
    elif c == "labels":
        src = req("GET", f"/session/{sid()}/source?format=json")["value"]; out = []
        def walk(n):
            lab = n.get("label") or n.get("name"); r = n.get("rect", {})
            if lab and n.get("isVisible", True):
                cx = int(r.get("x", 0) + r.get("width", 0) / 2); cy = int(r.get("y", 0) + r.get("height", 0) / 2)
                t = n.get("type", "").replace("XCUIElementType", "")
                out.append(f'{t:<14} {lab[:40]!r} @({cx},{cy})')
            for ch in n.get("children") or []:
                walk(ch)
        walk(src); print("\n".join(out[: int(a[0]) if a else 80]))
    else:
        print("未知命令:", c); print(__doc__)


READONLY = {"status", "shot", "size", "labels", "locked"}


def run():
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if c and c not in READONLY:
            try:
                if req("GET", "/wda/locked", timeout=10).get("value") is True:
                    sys.exit("手机锁屏了:请先在手机上解锁(停在主屏或目标 App),再重试")
            except urllib.error.HTTPError:
                pass
        main()
    except urllib.error.HTTPError as e:
        try:
            v = json.load(e).get("value") or {}
            msg = v.get("message") if isinstance(v, dict) else str(v)
        except Exception:
            msg = ""
        sys.exit(f"WDA 返回 {e.code}:{(msg or e.reason)[:200]}")
    except urllib.error.URLError as e:
        sys.exit(f"连不上 WDA({U}):{e.reason}。先跑 wda-start.sh")


if __name__ == "__main__":
    run()
