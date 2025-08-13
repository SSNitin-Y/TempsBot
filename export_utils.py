# export_utils.py
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


def color_grid_image(sections, width=900, sw=28, gap=8):
    """
    sections: list of {"date": str, "outfit": str, "pairs": [(hex1, hex2, label), ...]}
    Returns PNG bytes for a color grid of the 5-day plan.
    """
    font = ImageFont.load_default()

    # Count rows: one for headers per section + per pair
    rows = sum((len(s.get("pairs", [])) or 1) + 1 for s in sections)
    row_h = sw + 14
    height = 20 + rows * row_h + 20
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)

    y = 20
    for sec in sections:
        date = sec.get("date", "")
        outfit = sec.get("outfit", "")

        d.text((20, y), date, fill=(20, 20, 20), font=font)
        y += row_h // 2
        d.text((20, y), f"Outfit: {outfit}", fill=(60, 60, 60), font=font)
        y += row_h // 2

        pairs = sec.get("pairs", [])
        if not pairs:
            y += row_h // 2
        for (h1, h2, label) in pairs:
            # swatches
            d.rectangle([20, y, 20 + sw, y + sw], fill=h1)
            d.rectangle([20 + sw + gap, y, 20 + sw + gap + sw, y + sw], fill=h2)
            d.text((20 + sw * 2 + gap * 2 + 10, y + 6), label, fill=(20, 20, 20), font=font)
            y += row_h
        y += 8

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
