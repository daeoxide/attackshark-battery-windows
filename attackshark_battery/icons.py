"""Icones desenhados em tempo de execucao (bandeja, notificacoes e o .exe)."""
from PIL import Image, ImageDraw, ImageFont

GREY, BLUE, RED, YELLOW, GREEN = (128, 128, 128), (40, 120, 230), (220, 40, 40), (230, 180, 0), (40, 170, 70)


def app_icon(size=256):
    """Bateria branca sobre quadrado verde."""
    s = size / 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=48 * s, fill=GREEN)
    d.rounded_rectangle((44 * s, 80 * s, 196 * s, 176 * s), radius=14 * s, outline="white", width=max(1, round(14 * s)))
    d.rectangle((196 * s, 108 * s, 216 * s, 148 * s), fill="white")
    d.rectangle((66 * s, 102 * s, 150 * s, 154 * s), fill="white")
    return img


def _font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_BIG, FONT_SMALL = _font(40), _font(26)


def level_color(pct, on_power, asleep, warn_percent):
    if asleep or pct is None:
        return GREY
    if on_power:
        return BLUE
    if pct <= warn_percent:
        return RED
    if pct <= max(40, warn_percent):
        return YELLOW
    return GREEN


def tray_icon(pct, on_power, asleep, warn_percent=20):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 63, 63), radius=12, fill=level_color(pct, on_power, asleep, warn_percent))
    text = "?" if pct is None else str(pct)
    font = FONT_BIG if len(text) < 3 else FONT_SMALL
    d.text((32, 30), text, font=font, fill="white", anchor="mm")
    if on_power:
        d.polygon([(50, 2), (42, 16), (49, 16), (44, 28), (58, 12), (51, 12), (56, 2)], fill=(255, 230, 0))
    return img
