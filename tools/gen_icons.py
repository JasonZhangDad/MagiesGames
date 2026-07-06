"""生成 PWA 图标(192/512/maskable):深蓝渐变卡面 + 金色 M,与 favicon.svg 同风格。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make(size: int, maskable: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 0 if maskable else int(size * 0.03)
    radius = int(size * (0.5 if maskable else 0.22))
    # 对角渐变底
    c0, c1, c2 = (27, 35, 80), (42, 31, 102), (19, 26, 62)
    grad = Image.new("RGBA", (size, size))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        t = y / size
        color = lerp(c0, c1, t * 2) if t < 0.5 else lerp(c1, c2, (t - 0.5) * 2)
        gd.line([(0, y), (size, y)], fill=color + (255,))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [pad, pad, size - pad, size - pad], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)
    # 金色描边
    inset = int(size * (0.16 if maskable else 0.07))
    d.rounded_rectangle([inset, inset, size - inset, size - inset],
                        radius=int(size * 0.14), outline=(245, 193, 69, 200),
                        width=max(2, size // 100))
    # 金色 M
    font = None
    for name in ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                 "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, int(size * 0.5))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default(size=int(size * 0.5))
    bbox = d.textbbox((0, 0), "M", font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]
    for glow in range(6, 0, -2):
        d.text((x, y), "M", font=font,
               fill=(245, 193, 69, 26), stroke_width=glow, stroke_fill=(245, 193, 69, 22))
    d.text((x, y), "M", font=font, fill=(250, 205, 90, 255))
    return img


make(192, False).save(OUT / "icon-192.png")
make(512, False).save(OUT / "icon-512.png")
make(512, True).save(OUT / "icon-maskable-512.png")
print("icons ->", OUT)
