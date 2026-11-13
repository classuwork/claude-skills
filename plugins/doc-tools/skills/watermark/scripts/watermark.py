#!/usr/bin/env python3
"""给要外发的图片 / PDF 加铺满全页的斜向文字水印。

设计要点:全程只处理文件,不把图片内容显示或打印出来。终端只输出
文件路径、页数、尺寸和「水印改动了多少像素」,调用方(Claude)不需要、
也不应该打开图片看结果。

用法见 --help 或同目录 ../SKILL.md。
依赖:Pillow;PDF 输入还需要 poppler 的 pdftoppm(brew install poppler)。
--keep-vector 模式另需 pypdf + reportlab。
"""
import argparse
import datetime
import io
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
except ImportError:
    sys.exit("缺少 Pillow:pip3 install Pillow")

Image.MAX_IMAGE_PIXELS = 300_000_000

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
HEIC_EXTS = {".heic", ".heif"}
PDF_EXTS = {".pdf"}

FONT_CANDIDATES = [
    # macOS
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    # Windows
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]

A4_MM = (210, 297)


# ---------------------------------------------------------------- 水印绘制

def find_font(user_font):
    if user_font:
        if not os.path.exists(user_font):
            sys.exit("字体文件不存在:%s" % user_font)
        return user_font
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("找不到中文字体,请用 --font 指定一个 .ttf/.ttc")


def parse_color(s):
    parts = [int(x) for x in s.split(",")]
    if len(parts) != 3 or not all(0 <= x <= 255 for x in parts):
        raise argparse.ArgumentTypeError("颜色写成 R,G,B,如 120,120,120")
    return tuple(parts)


def text_block(lines, font, fill, line_gap):
    """把多行文字画成一块透明底的小图。"""
    dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
    boxes = [dummy.textbbox((0, 0), ln, font=font) for ln in lines]
    w = max(b[2] - b[0] for b in boxes)
    hs = [b[3] - b[1] for b in boxes]
    h = sum(hs) + line_gap * (len(lines) - 1)
    pad = line_gap
    block = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(block)
    y = pad
    for ln, b, lh in zip(lines, boxes, hs):
        lw = b[2] - b[0]
        d.text((pad + (w - lw) / 2 - b[0], y - b[1]), ln, font=font, fill=fill)
        y += lh + line_gap
    return block


def make_layer(size, lines, opt):
    """生成和页面一样大的 RGBA 水印层(斜向平铺,错位排布)。"""
    W, H = size
    short = min(W, H)
    font_px = max(14, int(short * opt.scale))
    font = ImageFont.truetype(opt.font_path, font_px)
    alpha = int(round(255 * opt.opacity))
    block = text_block(lines, font, opt.color + (alpha,), max(4, font_px // 3))
    bw, bh = block.size

    gap_x = font_px * 2
    gap_y = int(bh * 0.5)
    diag = int((W ** 2 + H ** 2) ** 0.5) + max(bw, bh) * 2
    canvas = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    row = 0
    y = 0
    while y < diag:
        x = -((bw + gap_x) // 2) if row % 2 else 0
        while x < diag:
            canvas.alpha_composite(block, (int(x), int(y)))
            x += bw + gap_x
        y += bh + gap_y
        row += 1
    canvas = canvas.rotate(opt.angle, resample=Image.BICUBIC)
    left = (diag - W) // 2
    top = (diag - H) // 2
    return canvas.crop((left, top, left + W, top + H))


def stamp(img, lines, opt):
    """返回加好水印的 RGB 图。"""
    base = img.convert("RGBA")
    base.alpha_composite(make_layer(base.size, lines, opt))
    return base.convert("RGB")


def changed_ratio(before, after):
    """水印改动了多少比例的像素(只算数,不输出任何图像内容)。"""
    a = before.convert("L")
    b = after.convert("L")
    if a.size != b.size:
        b = b.resize(a.size)
    small = (min(800, a.width), max(1, int(a.height * min(800, a.width) / a.width)))
    diff = ImageChops.difference(a.resize(small), b.resize(small))
    hist = diff.histogram()
    changed = sum(hist[6:])
    return changed / float(small[0] * small[1])


# ---------------------------------------------------------------- 读入

def open_image(path, tmpdir):
    ext = os.path.splitext(path)[1].lower()
    src = path
    if ext in HEIC_EXTS:
        if not shutil.which("sips"):
            sys.exit("HEIC 需要 macOS 的 sips 转换:%s" % path)
        src = os.path.join(tmpdir, os.path.basename(path) + ".jpg")
        subprocess.run(["sips", "-s", "format", "jpeg", path, "--out", src],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)  # 手机照片按拍摄方向转正
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[3])
        im = bg
    return im.convert("RGB")


def pdf_pages(path, dpi, tmpdir):
    if not shutil.which("pdftoppm"):
        sys.exit("PDF 需要 pdftoppm:brew install poppler(或改用 --keep-vector)")
    prefix = os.path.join(tmpdir, "pg")
    r = subprocess.run(["pdftoppm", "-r", str(dpi), "-png", path, prefix],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0:
        sys.exit("pdftoppm 转换失败(PDF 可能加密或损坏):%s" % path)
    files = sorted(f for f in os.listdir(tmpdir) if f.startswith("pg") and f.endswith(".png"))
    return [os.path.join(tmpdir, f) for f in files]


# ---------------------------------------------------------------- 输出

def out_path(src, outdir, ext, tag):
    base = os.path.splitext(os.path.basename(src))[0]
    d = outdir or os.path.dirname(os.path.abspath(src))
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "%s-%s%s" % (base, tag, ext))
    n = 2
    while os.path.exists(p):
        p = os.path.join(d, "%s-%s-%d%s" % (base, tag, n, ext))
        n += 1
    return p


def save_image(im, path):
    ext = os.path.splitext(path)[1].lower()
    # 不带 EXIF 写出:顺带去掉 GPS、设备型号等元数据
    if ext in (".jpg", ".jpeg"):
        im.save(path, "JPEG", quality=90, optimize=True)
    elif ext == ".png":
        im.save(path, "PNG", optimize=True)
    elif ext == ".webp":
        im.save(path, "WEBP", quality=90)
    else:
        im.save(path)


def save_pdf(pages, path, dpi):
    first, rest = pages[0], pages[1:]
    first.save(path, "PDF", resolution=float(dpi), save_all=True,
               append_images=rest, quality=88)


def report(src, dst, pages, size, ratio):
    w, h = size
    ok = ratio >= 0.01
    if ok:
        print("OK   %s -> %s | %d 页 | %dx%d | 水印改动像素 %.1f%%"
              % (src, dst, pages, w, h, ratio * 100))
    else:
        os.remove(dst)  # 水印几乎没上去:删掉,免得被当成成品发出去
        print("FAIL %s | 水印改动像素只有 %.2f%%,输出已删除" % (src, ratio * 100))
    return ok


# ---------------------------------------------------------------- 各模式

def do_image(path, lines, opt, tmpdir):
    im = open_image(path, tmpdir)
    wm = stamp(im, lines, opt)
    ratio = changed_ratio(im, wm)
    if opt.pdf:
        dst = out_path(path, opt.outdir, ".pdf", opt.tag)
        save_pdf([wm], dst, opt.dpi)
    else:
        ext = os.path.splitext(path)[1].lower()
        if ext in HEIC_EXTS or ext in (".bmp", ".tif", ".tiff"):
            ext = ".jpg"
        dst = out_path(path, opt.outdir, ext, opt.tag)
        save_image(wm, dst)
    return report(path, dst, 1, wm.size, ratio)


def do_pdf_flatten(path, lines, opt, tmpdir):
    sub = tempfile.mkdtemp(dir=tmpdir)
    pages_in = pdf_pages(path, opt.dpi, sub)
    out, ratios = [], []
    for p in pages_in:
        im = Image.open(p).convert("RGB")
        wm = stamp(im, lines, opt)
        ratios.append(changed_ratio(im, wm))
        out.append(wm)
    dst = out_path(path, opt.outdir, ".pdf", opt.tag)
    save_pdf(out, dst, opt.dpi)
    return report(path, dst, len(out), out[0].size, min(ratios))


def do_pdf_vector(path, lines, opt, tmpdir):
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        sys.exit("--keep-vector 需要:pip3 install pypdf reportlab")

    # reportlab 只认 TrueType 轮廓的字体,挨个试
    font_name = None
    for fp in [opt.font_path] + [p for p in FONT_CANDIDATES if p != opt.font_path]:
        if not os.path.exists(fp):
            continue
        try:
            pdfmetrics.registerFont(TTFont("WM", fp, subfontIndex=0))
            font_name = "WM"
            break
        except Exception:
            continue
    if not font_name:
        sys.exit("--keep-vector 找不到 reportlab 能用的中文 TrueType 字体,用 --font 指定")

    reader = PdfReader(path)
    if reader.is_encrypted:
        sys.exit("PDF 已加密,无法加水印:%s" % path)
    writer = PdfWriter()
    for page in reader.pages:
        page.transfer_rotation_to_content()  # 带 /Rotate 的页先摆正,水印方向才对
        pw, ph = float(page.mediabox.width), float(page.mediabox.height)
        x0, y0 = float(page.mediabox.left), float(page.mediabox.bottom)
        size = max(8.0, min(pw, ph) * opt.scale)
        lead = size * 1.3
        widths = [pdfmetrics.stringWidth(ln, font_name, size) for ln in lines]
        bw = max(widths) + size
        bh = lead * len(lines) + size * 0.5
        step_x = bw + size * 2
        step_y = bh * 1.5
        diag = (pw ** 2 + ph ** 2) ** 0.5

        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=(x0 + pw, y0 + ph))
        c.setFillColorRGB(*[v / 255.0 for v in opt.color])
        c.setFillAlpha(opt.opacity)
        c.setFont(font_name, size)
        c.translate(x0 + pw / 2, y0 + ph / 2)
        c.rotate(opt.angle)
        row = 0
        y = -diag
        while y < diag:
            x = -diag - (step_x / 2 if row % 2 else 0)
            while x < diag:
                for i, (ln, w) in enumerate(zip(lines, widths)):
                    c.drawString(x + (bw - w) / 2, y - i * lead, ln)
                x += step_x
            y += step_y
            row += 1
        c.save()
        buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
        writer.add_page(page)
    dst = out_path(path, opt.outdir, ".pdf", opt.tag)
    with open(dst, "wb") as f:
        writer.write(f)

    n = len(PdfReader(dst).pages)
    if n != len(reader.pages):
        os.remove(dst)
        print("FAIL %s | 输出页数 %d 和原件 %d 不符,输出已删除" % (path, n, len(reader.pages)))
        return False
    # 自检:两边各渲染第一页的低分辨率位图,只比像素差,不输出图像
    ratio = 1.0
    if shutil.which("pdftoppm"):
        sub_a = tempfile.mkdtemp(dir=tmpdir)
        sub_b = tempfile.mkdtemp(dir=tmpdir)
        a = subprocess.run(["pdftoppm", "-r", "50", "-f", "1", "-l", "1", "-png", path,
                            os.path.join(sub_a, "pg")], stderr=subprocess.DEVNULL)
        b = subprocess.run(["pdftoppm", "-r", "50", "-f", "1", "-l", "1", "-png", dst,
                            os.path.join(sub_b, "pg")], stderr=subprocess.DEVNULL)
        fa, fb = os.listdir(sub_a), os.listdir(sub_b)
        if a.returncode == 0 and b.returncode == 0 and fa and fb:
            ratio = changed_ratio(Image.open(os.path.join(sub_a, fa[0])),
                                  Image.open(os.path.join(sub_b, fb[0])))
    ok = report(path, dst, n, (int(pw), int(ph)), ratio)
    if ok:
        print("     ↑ 矢量叠加:原文字仍可选中,但水印能被 PDF 编辑软件删掉;尺寸单位是 pt")
    return ok


def do_combine(paths, lines, opt, tmpdir):
    """多张图片拼到 A4 上(默认每页 2 张,上下排),再整页加水印,出一个 PDF。"""
    pw = int(A4_MM[0] / 25.4 * opt.dpi)
    ph = int(A4_MM[1] / 25.4 * opt.dpi)
    margin = int(15 / 25.4 * opt.dpi)
    gap = int(10 / 25.4 * opt.dpi)
    imgs = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext in PDF_EXTS:
            sub = tempfile.mkdtemp(dir=tmpdir)
            imgs.extend(Image.open(x).convert("RGB") for x in pdf_pages(p, opt.dpi, sub))
        else:
            imgs.append(open_image(p, tmpdir))
    n = opt.per_page
    slot_w = pw - margin * 2
    slot_h = (ph - margin * 2 - gap * (n - 1)) // n
    pages, ratios = [], []
    for i in range(0, len(imgs), n):
        page = Image.new("RGB", (pw, ph), (255, 255, 255))
        group = imgs[i:i + n]
        y = margin
        for im in group:
            s = min(slot_w / im.width, slot_h / im.height)
            r = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
            page.paste(r, (margin + (slot_w - r.width) // 2, y + (slot_h - r.height) // 2))
            y += slot_h + gap
        wm = stamp(page, lines, opt)
        ratios.append(changed_ratio(page, wm))
        pages.append(wm)
    dst = opt.combine
    if os.path.exists(dst):
        dst = out_path(dst, None, ".pdf", "new")
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    save_pdf(pages, dst, opt.dpi)
    return report("+".join(os.path.basename(p) for p in paths), dst,
                  len(pages), pages[0].size, min(ratios))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        description="给图片 / PDF 加斜向平铺文字水印,输出新文件,不改原件。")
    ap.add_argument("inputs", nargs="+", help="图片(jpg/png/heic/webp…)或 PDF")
    ap.add_argument("-t", "--text", required=True,
                    help="水印正文,如「仅用于XX园区入驻申请 他用无效」")
    ap.add_argument("--date", default="today",
                    help="第二行日期:today(默认)/ none / 任意文字如 2026-11-13")
    ap.add_argument("-o", "--outdir", help="输出目录(默认和原件同目录)")
    ap.add_argument("--tag", default="水印", help="输出文件名后缀,默认「水印」")
    ap.add_argument("--pdf", action="store_true", help="图片也输出成 PDF")
    ap.add_argument("--combine", metavar="OUT.pdf",
                    help="把所有输入拼到 A4 上输出一个 PDF(如身份证正反面合一页)")
    ap.add_argument("--per-page", type=int, default=2, help="--combine 每页几张,默认 2")
    ap.add_argument("--keep-vector", action="store_true",
                    help="PDF 不转图片,只在上面叠一层水印(文字可选可搜,但水印能被删掉)")
    ap.add_argument("--dpi", type=int, default=200, help="PDF 转图 / 拼 A4 的分辨率,默认 200")
    ap.add_argument("--opacity", type=float, default=0.35, help="不透明度 0~1,默认 0.35")
    ap.add_argument("--color", type=parse_color, default=(110, 110, 110), help="R,G,B,默认灰色")
    ap.add_argument("--angle", type=float, default=30, help="倾斜角度,默认 30")
    ap.add_argument("--scale", type=float, default=0.035,
                    help="字号 = 短边 × scale,默认 0.035")
    ap.add_argument("--font", help="字体文件路径(默认自动找系统中文字体)")
    opt = ap.parse_args()

    opt.font_path = find_font(opt.font)
    if not 0 < opt.opacity <= 1:
        sys.exit("--opacity 要在 0~1 之间")
    if opt.per_page < 1:
        sys.exit("--per-page 至少 1")

    lines = [opt.text.strip()]
    if opt.date.lower() == "today":
        lines.append(datetime.date.today().isoformat())
    elif opt.date.lower() != "none":
        lines.append(opt.date)

    for p in opt.inputs:
        if not os.path.isfile(p):
            sys.exit("文件不存在:%s" % p)
        ext = os.path.splitext(p)[1].lower()
        if ext not in IMAGE_EXTS | HEIC_EXTS | PDF_EXTS:
            sys.exit("不支持的格式:%s" % p)

    tmpdir = tempfile.mkdtemp(prefix="wm-")
    ok = True
    try:
        if opt.combine:
            ok = do_combine(opt.inputs, lines, opt, tmpdir)
        else:
            for p in opt.inputs:
                ext = os.path.splitext(p)[1].lower()
                if ext in PDF_EXTS:
                    fn = do_pdf_vector if opt.keep_vector else do_pdf_flatten
                    ok = fn(p, lines, opt, tmpdir) and ok
                else:
                    ok = do_image(p, lines, opt, tmpdir) and ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if not ok:
        print("有文件没加成功(见 FAIL 行),调 --opacity / --scale 后重跑。")
        sys.exit(2)


if __name__ == "__main__":
    main()
