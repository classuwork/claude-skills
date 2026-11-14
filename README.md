# claude-skills

happy 自己写的 Claude Code skill，按插件市场格式组织，市场名叫 `happy-skills`。一共 **2 个插件、3 个 skill**。按插件安装，用不到的插件可以不装。

| 插件 | skill | 干什么 | 要先装的东西 |
|---|---|---|---|
| [`doc-tools`](plugins/doc-tools) | [`watermark`](plugins/doc-tools/skills/watermark/SKILL.md) | 证件、执照、合同发给第三方之前，自动加「仅用于 XX，他用无效」斜向水印。全程用脚本处理，Claude 不打开图片 | Python 3.9+（Pillow 第一次用时自动装）；处理 PDF 要 poppler |
| [`device`](plugins/device) | [`iphone-wda`](plugins/device/skills/iphone-wda/SKILL.md) | 让 Claude 操控用数据线连在 Mac 上的 iPhone：截屏、找按钮、点击、输入、滑动 | macOS、Xcode、libimobiledevice |
| | [`sms-forwarder`](plugins/device/skills/sms-forwarder/SKILL.md) | 用一台安卓专机把收到的短信验证码转发到飞书群；也能让 Claude 通过 adb 操控安卓手机 | adb、scrcpy |

> 只想要水印功能，装 `doc-tools` 一个插件就够了。`device` 只对手头有真机要测的人有用。

## 安装

在终端里运行：

```bash
# 1. 添加这个市场，每台电脑只需要做一次
claude plugin marketplace add classuwork/claude-skills

# 2. 装需要的插件，可以只装其中一个
claude plugin install doc-tools@happy-skills
claude plugin install device@happy-skills
```

**3. 重开 Claude Code**，已经开着的会话也可以运行 `/reload-plugins`。

第 1 步做完后，也可以在 Claude Code 里运行 `/plugin`，在界面里点选安装。

> 这台电脑没有配置 GitHub SSH 密钥也没关系。SSH 克隆失败时会自动改用 HTTPS（2026-11-14 实测）。

### 确认装上了

```bash
claude plugin list
```

能看到 `doc-tools@happy-skills`，并显示 `Status: ✔ enabled`，就说明装好了。想看某个插件里包含哪些 skill：

```bash
claude plugin details doc-tools@happy-skills    # 会列出 Skills (1) watermark
```

装好之后不需要手动调用。在 Claude Code 里正常说话，比如「把营业执照发给园区」「加水印」「截一下手机屏幕」，Claude 会自己选用对应的 skill。也可以直接输入 `/doc-tools:watermark` 来调用。

## 更新

### 拿到新版（使用方）

第三方市场**默认不会自动更新**，有两种办法拿新版。

**手动更新**，想更新的时候运行：

```bash
claude plugin marketplace update happy-skills      # 拉取最新的插件清单
claude plugin update doc-tools@happy-skills        # 每个装了的插件各运行一次
claude plugin update device@happy-skills
```

看到 `updated from 1.0.0 to 1.0.1` 就说明更新成功了；显示 `already at the latest version` 则表示没有新版。更新之后要**重开 Claude Code**，或者运行 `/reload-plugins`。

**打开自动更新**，只需要设置一次：在 Claude Code 里运行 `/plugin`，进入 Marketplaces，选 `happy-skills`，点 Enable auto-update。之后每次打开会话，Claude Code 会在后台检查新版，有新版会提示 `Plugin updated … Run /reload-plugins to apply`。

### 发新版（作者，也就是 happy）

每个插件的 `plugin.json` 里都写着 `version`。**改了某个插件，就要把这个插件的版本号往上调，再推送到 GitHub。** 版本号不变，对方运行 `update` 也只会得到 `already at the latest version`，拿不到新内容。

```bash
# 例:改了 device 里的任意文件
#   plugins/device/.claude-plugin/plugin.json  "version": "1.0.0" → "1.0.1"
git commit -am "device 1.0.1:……" && git push
```

- 只改 README、没改插件目录，版本号不用动。
- 版本号规则：小修小补改最后一位，比如 1.0.1；加了新 skill 或新参数改中间一位，比如 1.1.0。
- 新增一个插件：在 `.claude-plugin/marketplace.json` 的 `plugins` 里加一条，再新建 `plugins/<插件名>/.claude-plugin/plugin.json`，从 `1.0.0` 写起。

## 卸载

```bash
claude plugin uninstall doc-tools@happy-skills     # 卸载单个插件
claude plugin marketplace remove happy-skills      # 连市场一起删掉，之后就看不到这些插件了
```

卸载后重开 Claude Code。如果只是暂时不想用，可以改成停用，以后还能再启用：`claude plugin disable doc-tools@happy-skills`。

## 发给别人时怎么说

有新 skill 要分享时，发下面这段就够了，不用另写文档：

```text
<插件名>：<一句话说它干什么>
装法（终端里跑，装完重开 Claude Code）：
  claude plugin marketplace add classuwork/claude-skills
  claude plugin install <插件名>@happy-skills
以后更新：claude plugin marketplace update happy-skills && claude plugin update <插件名>@happy-skills
说明：https://github.com/classuwork/claude-skills
```

## 推送前自查（仓库是公开的）

每次推送前检查一遍，下面这些内容一律不能进仓库：

- 密钥、Token、Webhook 地址、密码、验证码种子
- 手机号、身份证号、真实证件照片和扫描件
- 内网地址（`192.168.*`、`10.*`、公司内网域名）、本机用户目录路径
- 苹果开发者团队 ID 这类账号标识。脚本里要用就改成从环境变量读或者自动识别，不写死
- 只有公司内部才看得懂的引用，比如内部 SOP、issue 链接

只看文件名和命中次数，不把匹配到的内容打印出来：

```bash
for pat in '1[3-9][0-9]{9}' '[0-9]{17}[0-9Xx]' '(api[_-]?key|secret|token|password)["'"'"' ]*[:=]' \
           '(192\.168|10\.[0-9]+\.[0-9]+)\.[0-9]+' '/Users/[a-z]+' 'open-apis/bot'; do
  echo "[$pat]"; git grep -c -E -i "$pat"
  echo "  历史提交里命中: $(git log --all -p | grep -c -E "^\+.*($pat)")"
done
```

正常情况下每一行都应该是 0，或者只命中变量名。README 本身会命中 1 次，那是这段命令自己。命中了就逐个确认，确认没问题再推送。

## watermark

**触发**：说「加水印」「打水印」时会触发。Claude 正准备把身份证、营业执照、合同、社保记录这类文件上传或发给外部时，即使没提水印，也会先加上。

**怎么做的**：

1. 从当前任务推断水印文字，比如 `仅用于XX园区入驻申请 他用无效`，第二行自动加上日期。推断不出来就问一句。
2. 运行 `scripts/watermark.py`。图片、PDF、HEIC 都能处理。PDF 默认整页转成图片再加水印，水印抠不掉。加 `--combine` 可以把身份证正反面拼成一页 A4。
3. 脚本只输出文件路径、页数、尺寸和「水印改动了多少像素」。Claude 靠这一行判断成功与否，**不用 Read 打开图片看**，所以身份证号、人脸这些内容不会进入对话记录。如果改动低于 1%，输出文件会被自动删掉，避免误发没有水印的文件。
4. 发出去的是带 `-水印` 后缀的新文件，原件不动。输出文件去掉了 EXIF 信息（GPS 位置、手机型号）。

带电子签章的 PDF 加水印会让签章失效，遇到这种情况会先问。

**依赖**：

- Python 3.9 以上。Mac 自带的就可以；第一次在终端跑 `python3` 时，如果弹出提示，按提示装命令行工具。
- **Pillow 不用自己装。** 系统 Python 里没有 Pillow 时，第一次加水印会自动在插件自己的数据目录里建一个虚拟环境装上，终端会打出一行「首次使用…」，以后直接复用，卸载插件时一起删掉。Homebrew 或 uv 装的 Python 不让 `pip3 install`（会报 `externally-managed-environment`），这种情况也照样能用（2026-11-14 在 uv 的 Python 3.12 和苹果自带的 Python 3.9 上实测过）。
- 处理 PDF 要 poppler：`brew install poppler`。这个需要自己装。

## device

两个 skill 的完整用法、一次性准备和排错方法，都写在各自的 SKILL.md 里：

- **iphone-wda**：需要先装 Xcode，并在 Xcode 里登录 Apple ID；运行 `brew install libimobiledevice`；手机要打开开发者模式，并点「信任此电脑」。签名团队会自动识别，不需要在脚本里填自己的 ID。WDA 运行期间手机屏幕上会一直显示一行提示，用之前先跟手机主人打个招呼。
- **sms-forwarder**：需要运行 `brew install --cask android-platform-tools` 和 `brew install scrcpy`；手机要打开 USB 调试。飞书 Webhook 只粘贴在手机 App 里，不要写进任何文件。
