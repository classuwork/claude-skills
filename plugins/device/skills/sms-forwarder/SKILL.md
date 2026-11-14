---
name: sms-forwarder
description: 用一台安卓专机插收码卡,装 SmsForwarder,把短信(验证码)自动转发到飞书群;含用 adb + scrcpy 从 Mac 操控安卓手机的脚本(截屏、列元素、点击、装 APK、查权限)。用于新搭一路收码、换机、排查「收不到码 / 卡片没正文」。触发词:短信转发、收码卡、验证码转发、SmsForwarder、安卓专机、飞书收码群、操控安卓手机、adb、scrcpy。
allowed-tools: Bash, Read
---

# sms-forwarder:收码卡 → 安卓专机 → 飞书群

**一张卡 = 一台安卓机 = 一个飞书群。** 安卓专机插收码卡,装 SmsForwarder,通过飞书群「自定义机器人」Webhook 把短信转到只含看码人的飞书群。iPhone 不行(装不了 SmsForwarder,快捷指令转发 2026-09 实测走不通)。

脚本在本 skill 的 `scripts/` 目录,下面用 `S` 代指它:`S="${CLAUDE_PLUGIN_ROOT}/skills/sms-forwarder/scripts"`。

## 0. Mac 上的工具(一次性)

```bash
brew install --cask android-platform-tools   # adb:命令行装 App、授权、截屏、点击
brew install scrcpy                          # 把手机画面投到 Mac,用鼠标键盘直接操作
```

**手机打开 USB 调试**(小米 / 红米):设置 → 我的设备 → 全部参数 → 连点「MIUI / HyperOS 版本」7 次 → 返回 设置 → 更多设置 → 开发者选项 → 打开「USB 调试」,**还要打开「USB 调试(安全设置)」**(否则 adb 点击、输入无效;这一项要插 SIM 卡并登录小米账号)。数据线连 Mac,手机上点「允许 USB 调试」。

```bash
python3 $S/a.py devices      # 能看到设备就通了;连了多台用 ANDROID_SERIAL=<序列号> 指定
scrcpy                       # 打开投屏窗口,人可以直接在 Mac 上点手机;中文输入在这里用键盘打
```

## 1. 操控安卓手机(`a.py`,坐标是屏幕像素)

```bash
a(){ python3 $S/a.py "$@"; }   # 要定义成函数;写成 X="python3 …" 再 $X 调用,在 zsh 里会报 no such file
a shot a.png            # 截屏
a labels 60             # 屏幕上的文字 / 描述 + 中心坐标(找按钮最快)
a find "发送通道"        # 点含该文字的元素
a tap 540 1200          # 按坐标点
a swipe 540 1800 540 600 300
a type "abc123"         # 只支持 ASCII;中文在 scrcpy 窗口里打。符号会原样输入,不会被手机当命令执行
a key back|home|enter|recent|wake
a launch cn.ppps.forwarder
a install /path/x.apk
a perms cn.ppps.forwarder          # 看运行时权限是否已授予
a grant cn.ppps.forwarder android.permission.RECEIVE_SMS
```

小米系统里有些开关(「通知类短信」、自启动、省电策略)是厂商私有设置,adb 授不了,**用 `labels` + `find` / `tap` 去设置页点,或让人在 scrcpy 窗口里点**。

## 2. 搭一路

1. **卡**:首选电信 5 元无忧卡(套餐 `201905`)。同一身份证线上只能办 1 张,签收后 20 天内激活。**一台机只插一张卡**。
2. **飞书群 + Webhook**(人在飞书里做):新建群(群名写用途 + 卡尾号)→ 只拉需要看码的人 → 群设置 → 群机器人 → 添加「自定义机器人」→ 复制 Webhook。加签、关键词都不用开。
3. **下载并核对 APK**:
   ```bash
   $S/get-apk.sh            # 默认 arm64-v8a;老机器用 get-apk.sh armeabi-v7a
   ```
   从官方 GitHub Release 拉最新版,自动和 GitHub 公布的 SHA-256 比对;不一致、或 GitHub 没公布摘要,都删掉并退出。
4. **安装**:`a install <上一步打印的路径>`。专机别装代理。
5. **权限**:
   ```bash
   for p in RECEIVE_SMS READ_SMS READ_PHONE_STATE POST_NOTIFICATIONS; do a grant cn.ppps.forwarder android.permission.$p; done
   a perms cn.ppps.forwarder
   ```
   🔴 **小米 / 红米还必须**在 App 权限里开「**通知类短信**」,并在系统「短信」App 设置里**关掉「免费网络短信」**(还不行再关「短信智能识别」)。验证码都是 `106` 开头的服务号发的,MIUI 算「通知类短信」;不开的话**飞书照收,但卡片没有正文**,而且「重发」补不回来。
6. **发送通道**(这一步人在 scrcpy 窗口里做,Claude 不截这个页面):App 里「发送通道」→ 新建「飞书群机器人」→ 粘 Webhook → 消息类型「**消息卡片**」→ 标题模板选「短信内容」→「自定义消息卡片 Json」**留空** → 保存 → 测试。Webhook 很长,用 scrcpy 窗口粘贴(Mac 剪贴板会同步到手机)。
7. **转发规则**:发送方 `*` → 选上一步的通道 → 内容模板**只留「短信内容」**。
8. **通用设置**:打开「开机自启动」「监听服务常驻」;**请求重试**设最多 5 次、间隔 10 秒(默认 0 次,网络一闪就丢码)。

**换机**:旧机抄下 Webhook → 卡挪到新机 → 新机照 3–8 步 → 旧机关转发。要搬的只有 Webhook。

## 3. 保活(小米 / 红米,每路必做)

设置 → 应用设置 → 应用管理 → SmsForwarder:**自启动**开、**省电策略「无限制」**(最关键)、通知允许;多任务界面下拉卡片**锁定** 🔒;WLAN「休眠时保持网络连接」选「始终」(找不到就跳过);**长期插电,不开 VPN / 代理**。系统更新可能重置这些,隔一阵抽查。

其他品牌:华为「应用启动管理」改手动并全开;OPPO / vivo 允许自启动、关联启动、后台运行和高耗电;原生安卓电池优化设「不优化」(也可 `adb shell dumpsys deviceidle whitelist +cn.ppps.forwarder`)。

## 4. 验收

- 锁屏放十几分钟,再找个网站 / App 点「获取验证码」,**用 `106` 服务号发来的真验证码测** → 几秒内到群、**卡片里看得到码**。普通手机号发的测试短信测不出「通知类短信」漏开。
- ⚠️ 别反复用自家业务的发码接口测,很多后端按 IP 限流,超了会封 IP。
- 多路时每路各发一条,确认没串群。

## 5. 收不到码怎么查

先看手机上 SmsForwarder 的「转发日志」:**让人在 scrcpy 窗口里自己看**,Claude 不截这个页面(日志里就是短信原文和验证码)。**有日志只说明匹配了规则,不等于到了飞书**;点开那条,滑到详情最底下看结果,把「现象」那一列对应的报错告诉 Claude:

| 现象 | 原因 | 处理 |
|---|---|---|
| 「网络不给力」/ `Unable to resolve host` | 发送时手机没网 | 点「重发消息」;查第 3 节保活和第 2 节第 8 步重试 |
| 飞书收到了,卡片只有时间和来源、没有正文 | 没开「通知类短信」 | 照第 2 节第 5 步改;重发补不回正文 |
| `"code":19001` / `access token invalid` | 机器人被移出群,或 Webhook 被重置 | 群里重新加机器人,新地址换到发送通道 |
| `"code":0` 但群里找不到 | 发到了 Webhook 对应的另一个群 | 先翻另一路的群,再核对 Webhook 末尾几位 |

SmsForwarder 只在飞书返回 `code == 0` 时标「成功」。卡片标题栏最多显示 4 行,长短信看下面的正文那份,**正文那份别删**。

## 🔴 安全红线

- 收码群**只放需要看码的人**,不进大群。
- **Webhook 不进 git、不发聊天、不写进文档**。泄露了别人只能往群里发、读不到群;真泄露就在群里重新生成。
- 只用**自有实名卡**;银行、税务等敏感验证码**绝不走**第三方收码平台。
- **会显示验证码或 Webhook 的页面,Claude 不截屏、不跑 `labels`**:转发日志、短信 App、「发送通道」编辑页。这些页面让人在 scrcpy 窗口里看、里面操作;Claude 只在设置页、权限页这类页面上用 `shot` / `labels`。`labels` / `find` 输出里如果出现 Webhook,会自动打码成 `hook/***`,但别依赖这个。
- 其他截屏只用于当前排查,不进仓库、不外发。

## 实测

- 2026-10-10:`adb`(1.0.41)、`scrcpy`(5.0.1)在 macOS 上安装通过;`get-apk.sh` 拉到 SmsForwarder v3.5.0(arm64-v8a)并与 GitHub 公布的 SHA-256 核对一致;从 APK 清单核实包名是 `cn.ppps.forwarder`。
- 2026-10-10 在一台 Redmi K70 Ultra(HyperOS,Android 16)上实测 `a.py`:`devices / key / shot / labels / launch / swipe / find / tap / type(ASCII)/ perms` 全部正常,中文 `type` 按预期拦下并提示;`scrcpy` 能连上设备。注意 `launch` 会回到 App 上次停留的页面,要从首页开始先多按几次 `key back`。没装 App、没改设置。
