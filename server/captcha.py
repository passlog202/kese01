"""图片验证码生成器（Pillow 实现）。

生成 4 位数字+大写字母验证码，绘制干扰线/噪点/字符随机倾斜，
输出 base64 编码的 PNG data-uri，供前端 <img> 直接显示。

资源依赖：
- Pillow（绘图）
- TTF 字体（环境变量 KESE_CAPTCHA_FONT 指定，未设置则从常见路径查找，
  找不到回退到 Pillow 内置默认字体，保证任何环境都能运行）
"""
from __future__ import annotations

import base64
import io
import os
import random
import string
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 验证码字符集（去掉了易混淆的 0/O/1/I）
_CHARSET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
_CAPTCHA_LEN = int(os.environ.get("KESE_CAPTCHA_LEN", 4))
_CAPTCHA_TTL = int(os.environ.get("KESE_CAPTCHA_TTL", 180))  # 3 分钟

_FONT_CANDIDATES = [
    os.environ.get("KESE_CAPTCHA_FONT") or "",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _random_color(start: int, end: int) -> tuple[int, int, int]:
    return (random.randint(start, end), random.randint(start, end), random.randint(start, end))


def generate_captcha_image(code: str) -> str:
    """根据验证码字符串绘制干扰图片，返回 base64 data-uri。"""
    width, height = 130, 46
    image = Image.new("RGB", (width, height), (245, 247, 250))
    draw = ImageDraw.Draw(image)

    # 1) 背景噪点
    for _ in range(60):
        x, y = random.randint(0, width - 1), random.randint(0, height - 1)
        draw.point((x, y), fill=_random_color(180, 235))

    # 2) 干扰线
    for _ in range(4):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=_random_color(150, 215), width=1)

    # 3) 逐字符绘制（随机大小/旋转/颜色）
    font = _load_font(30)
    total_w = 0
    for ch in code:
        total_w += draw.textlength(ch, font=font) + 8
    start_x = max(6, int((width - total_w) // 2))
    for ch in code:
        ch_img = Image.new("RGBA", (40, 46), (0, 0, 0, 0))
        ch_draw = ImageDraw.Draw(ch_img)
        ch_draw.text((4, 2), ch, font=font, fill=_random_color(20, 120))
        ch_img = ch_img.rotate(random.randint(-28, 28), expand=False, resample=Image.BICUBIC)
        image.paste(ch_img, (start_x, random.randint(-2, 2)), ch_img)
        start_x += int(draw.textlength(ch, font=font)) + 8

    # 4) 轻微模糊 + 锐化，增强抗机器识别（轻微）
    image = image.filter(ImageFilter.SMOOTH)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def new_captcha() -> tuple[str, str, str]:
    """生成新验证码，返回 (captcha_id, code, image_data_uri)。"""
    captcha_id = uuid.uuid4().hex
    code = "".join(random.choices(_CHARSET, k=_CAPTCHA_LEN))
    image = generate_captcha_image(code)
    return captcha_id, code, image


CAPTCHA_TTL_SECONDS = _CAPTCHA_TTL
