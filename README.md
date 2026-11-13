# claude-skills

happy 自己写的 Claude Code skill,按插件市场格式组织:**2 个插件、3 个 skill**。

| 插件 | skill | 干什么 |
|---|---|---|
| [`doc-tools`](plugins/doc-tools) | [`watermark`](plugins/doc-tools/skills/watermark/SKILL.md) | 证件、执照、合同发给第三方前,自动加「仅用于 XX,他用无效」斜向水印。全程脚本处理,Claude 不打开图片 |
| [`device`](plugins/device) | [`iphone-wda`](plugins/device/skills/iphone-wda/SKILL.md) | 用 WebDriverAgent 操控连在 Mac 上的真机 iPhone:截屏、列元素、点击、输入、滑动 |
| | [`sms-forwarder`](plugins/device/skills/sms-forwarder/SKILL.md) | 安卓专机 + SmsForwarder 把短信验证码转到飞书群;adb + scrcpy 从 Mac 操控安卓手机 |

## 安装

```bash
claude plugin marketplace add classuwork/claude-skills
claude plugin install doc-tools@happy-skills
claude plugin install device@happy-skills
```

装好后在 Claude Code 里说「加水印」「把身份证发给园区」「真机」「短信转发」之类的话就会用上。

## watermark

**触发**:说「加水印」「打水印」,或者 Claude 正准备把身份证、营业执照、合同、社保记录这类文件上传 / 发给外部时,即使没提水印也会先加。

**怎么做的**:

1. 从当前任务推断水印文字,如 `仅用于XX园区入驻申请 他用无效`,第二行自动加日期;推不出就问一句。
2. 跑 `scripts/watermark.py`:图片、PDF、HEIC 都行;PDF 默认整页转图再加,水印抠不掉;`--combine` 能把身份证正反面拼成一页 A4。
3. 脚本只输出文件路径、页数、尺寸和「水印改动了多少像素」。Claude 靠这一行判断成没成,**不用 Read 打开图片看**,身份证号、人脸这些内容不进对话记录。改动低于 1% 的输出自动删掉,不会误发没水印的文件。
4. 发出去的是 `-水印` 新文件,原件不动;输出去掉 EXIF(GPS、机型)。

带电子签章的 PDF 加水印会让签名失效,这种情况会先问。

**依赖**:Python 3.9+、Pillow;PDF 需要 poppler(`brew install poppler`)。
