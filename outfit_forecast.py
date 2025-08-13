import colorsys
import pandas as pd
from color_utils import closest_color_name  # your helper
from textwrap import dedent

def _hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))

def generate_color_combinations(condition: str, temperature: float, day_seed: int = 0):
    # Base hue by temp
    if temperature < 5:
        base = 240
    elif temperature < 15:
        base = 200
    elif temperature < 25:
        base = 40
    else:
        base = 0

    # Saturation/lightness by condition
    if "rain" in condition or "snow" in condition:
        sat, light = 30, 40
    elif "cloud" in condition:
        sat, light = 50, 60
    else:
        sat, light = 70, 70

    # Vary by day so combos aren’t identical across days
    shift = (day_seed % 90)  # 0..89
    h1a = (base + shift) % 360
    h1b = (h1a + 20) % 360

    h2a = (base + 40 + shift) % 360
    h2b = (h2a + 20) % 360

    pairs = []
    for (ha, hb) in [(h1a, h1b), (h2a, h2b)]:
        hex1 = _hsl_to_hex(ha, sat, light)
        hex2 = _hsl_to_hex(hb, sat, light)
        name1 = closest_color_name(hex1)
        name2 = closest_color_name(hex2)
        pairs.append(((hex1, name1), (hex2, name2)))
    return pairs  # two pairs

def generate_outfit_recommendations(df: pd.DataFrame, uv_hint=None):
    df = df.copy()
    df['day'] = df['datetime'].dt.date
    grouped = df.groupby('day')
    daily_outfits = []

    for idx, (day, group) in enumerate(grouped):
        avg_temp = float(group['temperature'].mean())
        common_condition = str(group['condition'].mode()[0]).lower()

        # Outfit logic
        if avg_temp < 5:
            outfit = "Heavy coat, scarf, boots"
        elif avg_temp < 15:
            outfit = "Sweater or jacket with jeans"
        elif avg_temp < 25:
            outfit = "Light shirt and chinos"
        else:
            outfit = "T-shirt and shorts"

        if "rain" in common_condition:
            outfit += ", and a rain jacket"
        elif "snow" in common_condition:
            outfit += ", and waterproof boots"

        # UV tweaks (optional)
        if uv_hint is not None:
            try:
                uv_val = float(uv_hint)
                if uv_val >= 6:
                    outfit += " UV high: consider a UPF long‑sleeve or a lightweight overshirt and a cap/hat."
                elif 3 <= uv_val < 6:
                    outfit += " UV moderate: a cap/hat and UV sunglasses are a good idea."
            except Exception:
                pass

        # Generate two color pairs; seed by day index so they vary
        color_combos = generate_color_combinations(common_condition, avg_temp, day_seed=idx * 17)

        # Build the color boxes HTML with NO leading indentation
        color_blocks = []
        for (hex1, name1), (hex2, name2) in color_combos:
            label = f"{name1} & {name2}"
            block = f"""<div style='margin-top:5px;'><span style='display:inline-block;width:20px;height:20px;background-color:{hex1};border:1px solid #000;margin-right:5px;'></span><span style='display:inline-block;width:20px;height:20px;background-color:{hex2};border:1px solid #000;margin-left:10px;'></span><span style='margin-left:10px;font-weight:bold;'>{label}</span></div>"""
            color_blocks.append(block)

        day_str = day.strftime("%A, %B %d")

        # Entire block also UNINDENTED (no tuple lines, no code fences)
        html = f"""<div style='margin-bottom:15px;padding:10px;border:1px solid #ddd;border-radius:5px;'>
        <b>📅 {day_str}</b><br>
        👕 Outfit: {outfit}<br>
        🎨 Colors:<br>{''.join(color_blocks)}</div>"""

        # Safety: ensure no stray leading spaces turn it into a code block
        daily_outfits.append(dedent(html))

    return daily_outfits




