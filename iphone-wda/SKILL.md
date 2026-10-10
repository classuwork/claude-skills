---
name: iphone-wda
description: 直接操控用数据线连在 Mac 上的真机 iPhone(WebDriverAgent):截屏、列屏幕元素、点击、输入、滑动、回主屏、启动 App。用于 App 真机走查 / 回归测试 / 测推送,不用人一步步手点。触发词:真机、操控手机、操作 iPhone、真机测试、WDA、WebDriverAgent、帮我在手机上点、截一下手机屏幕。
allowed-tools: Bash, Read
---

# iphone-wda:让 Claude 直接操作真机 iPhone

手机用数据线连 Mac → `wda-start.sh` 编译并启动 WebDriverAgent、把手机 8100 端口转到 Mac → 用 `w.py` 截屏 / 读元素 / 点击 / 输入 → 用完 `wda-stop.sh` 关掉。

脚本在本 skill 的 `scripts/` 目录。下面用 `S` 代指它:`S=~/.claude/skills/iphone-wda/scripts`。

## 0. 一次性准备(每台 Mac / 每台手机第一次)

| 要什么 | 怎么弄 |
|---|---|
| Xcode | App Store 安装,打开一次,**同意许可协议** |
| libimobiledevice | `brew install libimobiledevice`(提供 `idevice_id`、`iproxy`) |
| 开发证书 | Xcode → Settings → Accounts 登录 Apple ID。免费账号也行,但签名 7 天过期 |
| 手机信任这台 Mac | 连线后手机上点「信任此电脑」;`idevice_id -l` 能打出 UDID 就对了 |
| 手机开发者模式 | 设置 → 隐私与安全性 → 开发者模式 → 打开(会重启) |

Claude 输入框里用 `! sudo ...` 输不了密码。要同意 Xcode 许可时,用系统密码弹窗,由手机 / 电脑主人自己输开机密码:

```bash
osascript -e 'do shell script "/usr/bin/xcodebuild -license accept" with administrator privileges'
```

## 1. 启动

```bash
$S/wda-start.sh                 # 默认取 idevice_id -l 的第一台
$S/wda-start.sh <UDID>          # 连了多台时指定
$S/wda-start.sh <UDID> --rebuild  # 强制重编(换证书 / 签名过期)
```

- **签名团队自动识别**:取本机第一张「Apple Development」证书的团队 ID。有多张证书、想用别的,设 `WDA_TEAM=<10 位团队 ID>`。
- **bundle id** 默认 `com.<本机用户名>.wda.runner`,可用 `WDA_BUNDLE` 改。
- 已在运行就直接返回;没有编译产物、或产物超过 6 天(签名 7 天过期)会自动重编,约 1 分钟。
- 编译产物、日志、会话 id 都在 `~/Library/Caches/iphone-wda/`,**不放任何仓库工作区**。
- **启动前先跟手机主人打招呼**:WDA 运行时手机屏幕上会一直有一行白字(「自动化运行中」)。

## 2. 操作(坐标一律是「点 pt」,不是截图像素)

```bash
w(){ python3 $S/w.py "$@"; }   # 要定义成函数;写成 X="python3 …" 再 $X 调用,在 zsh 里会报 no such file
w status                    # WDA 状态
w locked                    # 手机是否锁屏(锁屏时 home / launch / tap 等会被拒,脚本会先提示「请先解锁」)
w size                      # 屏幕尺寸(点),例如 390×844
w shot /path/a.png          # 截屏(像素一般是点的 3 倍)
w labels 60                 # 列出可见元素:类型 / 文字 / 中心坐标 —— 找按钮最快
w tap 299 91                # 按坐标点
w click "登录"               # 按名字点(依次试 accessibility id、label 相等、label 包含);点不准就改用 tap
w type "要输入的字"          # 往当前焦点输入框打字,先 tap 输入框
w swipe 195 700 195 200 300 # 从 (x1,y1) 滑到 (x2,y2),300ms
w home                      # 回主屏
w launch com.xxx.bundleid   # 启动 App
```

- 截图缩小了看:`sips -Z 400 a.png --out a-small.png`;从缩小图量的坐标换回点:`点 = 像素 × (屏宽点数 / 缩小图宽)`。
- 优先用 `labels` 找坐标再 `tap`;`click` 偶尔点到文字而不是按钮。
- 每步操作后截屏确认,再做下一步。
- `launch` 会回到 App 上次停留的页面,不一定是首页;要从首页开始,先 `home` 再从主屏点图标,或在 App 里多点几次返回。
- 出错时脚本只打一行原因(连不上 WDA / 锁屏 / WDA 返回的错误信息),不会刷一大段 Python 报错。

## 3. 用完关掉

```bash
$S/wda-stop.sh
```

关不掉就在手机上**同时按住两个音量键**几秒强制结束。手机上会留一个 WebDriverAgentRunner App,下次直接 `wda-start.sh`,不用重装。

## 🔴 规矩

- **改数据、付款、确认订单、给真实用户发消息之前,先停下来问手机主人。** 能点不等于该点。
- 截图可能拍到个人信息(通知、相册、聊天),只用于当前任务,**不进仓库、不外发**。
- 测推送:App 停在**前台**时聊天走 WebSocket,不弹推送 ⇒ 先把 App 退到后台或锁屏。

## 排错

| 现象 | 处理 |
|---|---|
| 没找到真机 | 换线 / 重插;手机上点「信任此电脑」;`idevice_id -l` 要能打出 UDID |
| `Developer Mode disabled` | 手机开开发者模式(见第 0 节) |
| `isn't registered in your developer account` | 脚本已带 `-allowProvisioningDeviceRegistration`,一般会自动登记;还不行看 `build.log` |
| 编译报许可没同意 | 用第 0 节的 `osascript` 弹窗同意 |
| 没读出团队 ID / 没有证书 | Xcode 登录 Apple ID;或手动 `WDA_TEAM=<id> $S/wda-start.sh` |
| `Unlock ... to Continue` | 手机锁屏了,解锁后重跑 |
| 第一次装到新手机后打不开 | 手机:设置 → 通用 → VPN 与设备管理 → 点开发者证书 → 信任 |
| 8100 被占 / 状态不对 | 先 `wda-stop.sh` 再 `wda-start.sh` |

日志:`~/Library/Caches/iphone-wda/build.log`(编译)、`wda-run.log`(运行)、`iproxy.log`。

## 实测

- 2026-10-10(iPhone 13 Pro,iOS 26.6.2):从空缓存自动识别签名团队 → 编译 → 启动;照本说明的命令一字不改在 zsh 里执行通过;`status / size / shot / labels / locked / home / launch / swipe` 实测正常,重复启动、关闭正常;手机锁着时 `wda-start.sh` 正确提示「解锁后重跑」。
- `tap / click / type` 在 2026-10 的真机走查里实际用过(写法未变)。
- 尚未在真机上走到的:锁屏状态下 `w` 命令给出「请先解锁」提示这条分支(测试时手机被面容 ID 立即解锁);在别人的 Mac / 证书上首次编译。
