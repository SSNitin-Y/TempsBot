# color_utils.py
from webcolors import CSS3_HEX_TO_NAMES, hex_to_rgb
import re

_HEX_RE = re.compile(r'^#?[0-9A-Fa-f]{6}$')

def _clean_hex(s: str) -> str:
    """Trim, normalize case, and ensure leading # for a 6‑digit hex."""
    if not isinstance(s, str):
        raise ValueError("hex must be a string")
    s = s.strip()  # <-- fixes the failing test with spaces
    # Allow forms like 'ff0000' or '#FF0000'
    if s.startswith('#'):
        core = s[1:]
    else:
        core = s
    if not _HEX_RE.match('#' + core):
        raise ValueError(f"'{s}' is not a valid 6‑digit hex color.")
    return '#' + core.lower()

def closest_color_name(hex_code: str) -> str:
    """
    Return a CSS3 color name closest to the given hex (6‑digit).
    Accepts inputs like '  #FF0000 ' or 'ff0000'.
    """
    h = _clean_hex(hex_code)

    # Exact match fast path
    if h in CSS3_HEX_TO_NAMES:
        return CSS3_HEX_TO_NAMES[h]

    # Otherwise, compute nearest by Euclidean distance in RGB
    r, g, b = hex_to_rgb(h)
    min_dist, best_name = float('inf'), None
    for hex_val, name in CSS3_HEX_TO_NAMES.items():
        r2, g2, b2 = hex_to_rgb(hex_val)
        dist = (r - r2)**2 + (g - g2)**2 + (b - b2)**2
        if dist < min_dist:
            min_dist, best_name = dist, name
    return best_name or h
