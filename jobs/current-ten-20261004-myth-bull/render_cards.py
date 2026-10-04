from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
OUT = ROOT / "final"
OUT.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

cards = [
    {
        "title": "Ο ΤΑΥΡΟΣ ΕΞΟΡΓΙΖΕΤΑΙ\nΜΕ ΤΟ ΚΟΚΚΙΝΟ;",
        "body": "ΜΥΘΟΣ Ή ΑΛΗΘΕΙΑ;",
        "box": (48, 46, 1032, 410),
        "title_size": 66,
        "body_size": 45,
    },
    {
        "title": "ΜΥΘΟΣ",
        "body": "Δεν επιτίθεται επειδή\n«βλέπει κόκκινο».",
        "box": (48, 60, 740, 430),
        "title_size": 80,
        "body_size": 48,
    },
    {
        "title": "ΤΙ ΒΛΕΠΕΙ;",
        "body": "Τα βοοειδή είναι διχρωματικά.\nΞεχωρίζουν καλύτερα το μπλε και\nκιτρινοπράσινες αποχρώσεις — όχι\nτο κόκκινο όπως το βλέπουμε εμείς.",
        "box": (48, 46, 1032, 500),
        "title_size": 68,
        "body_size": 39,
    },
    {
        "title": "Η ΚΙΝΗΣΗ ΜΕΤΡΑΕΙ",
        "body": "Ο ταύρος αντιδρά κυρίως στην κίνηση\nτου υφάσματος και στην απειλή — όχι\nστο κόκκινο χρώμα.\n\nΑν σας άρεσε, ακολουθήστε\nγια περισσότερα.",
        "box": (40, 48, 1038, 640),
        "title_size": 60,
        "body_size": 37,
    },
]

def fit_crop(img: Image.Image, size=(1080, 1080)) -> Image.Image:
    img = img.convert("RGB")
    scale = max(size[0] / img.width, size[1] / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    x = (resized.width - size[0]) // 2
    y = (resized.height - size[1]) // 2
    return resized.crop((x, y, x + size[0], y + size[1]))

def panel(img: Image.Image, box):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=34, fill=(5, 9, 12, 190), outline=(255, 255, 255, 58), width=2)
    return Image.alpha_composite(img.convert("RGBA"), layer)

for idx, card in enumerate(cards, 1):
    img = panel(fit_crop(Image.open(SRC / f"{idx:02d}.png")), card["box"])
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(FONT_BOLD, card["title_size"])
    body_font = ImageFont.truetype(FONT_REG, card["body_size"])
    x = card["box"][0] + 34
    y = card["box"][1] + 30
    accent = (255, 219, 75, 255)
    white = (255, 255, 255, 255)
    draw.multiline_text((x + 3, y + 3), card["title"], font=title_font, fill=(0, 0, 0, 210), spacing=8)
    draw.multiline_text((x, y), card["title"], font=title_font, fill=accent, spacing=8)
    title_h = draw.multiline_textbbox((x, y), card["title"], font=title_font, spacing=8)[3] - y
    by = y + title_h + 25
    draw.multiline_text((x + 2, by + 2), card["body"], font=body_font, fill=(0, 0, 0, 195), spacing=11)
    draw.multiline_text((x, by), card["body"], font=body_font, fill=white, spacing=11)
    marker = f"{idx}/4"
    mf = ImageFont.truetype(FONT_BOLD, 28)
    mw = draw.textbbox((0, 0), marker, font=mf)[2]
    draw.rounded_rectangle((978 - mw, 1018, 1032, 1066), radius=16, fill=(5, 9, 12, 205))
    draw.text((1004 - mw, 1023), marker, font=mf, fill=white)
    img.convert("RGB").save(OUT / f"card-{idx:02d}.jpg", quality=96, subsampling=0)
