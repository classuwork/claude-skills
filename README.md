# claude-skills

自己写的 Claude Code skill。

| skill | 干什么 |
|---|---|
| [`iphone-wda`](iphone-wda/SKILL.md) | 用 WebDriverAgent 操控连在 Mac 上的真机 iPhone:截屏、列元素、点击、输入、滑动 |
| [`sms-forwarder`](sms-forwarder/SKILL.md) | 安卓专机 + SmsForwarder 把短信验证码转到飞书群;adb + scrcpy 从 Mac 操控安卓手机 |

## 安装

```bash
git clone https://github.com/classuwork/claude-skills.git
mkdir -p ~/.claude/skills
cp -R claude-skills/iphone-wda claude-skills/sms-forwarder ~/.claude/skills/
```

装好后在 Claude Code 里说「真机」「操控手机」「短信转发」之类的话就会用上。
