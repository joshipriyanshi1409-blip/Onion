"""Create a deterministic synthetic fixture for end-to-end software demos, not model training."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "onion-demo.png"
WIDTH, HEIGHT = 1000, 700


def draw_onion(image: Image.Image, center: tuple[int, int], radius: int, colour: tuple[int, int, int], seed: int) -> None:
    x0, y0 = center[0] - radius, center[1] - radius
    x1, y1 = center[0] + radius, center[1] + radius
    px = image.load()
    cr, cg, cb = colour
    for y in range(max(0, y0), min(HEIGHT, y1 + 1)):
        for x in range(max(0, x0), min(WIDTH, x1 + 1)):
            nx = (x - center[0]) / radius
            ny = (y - center[1]) / radius
            distance = nx * nx * 0.92 + ny * ny
            if distance <= 1:
                # A warm, high-saturation papery surface with visible but subtle texture.
                shade = max(0.55, 1.07 - 0.35 * distance + 0.035 * math.sin((x + seed * 17) * 0.17) * math.cos(y * 0.13))
                ring = 1 - 0.045 * max(0, math.sin(math.sqrt(distance) * 22 + seed))
                px[x, y] = tuple(max(0, min(255, int(c * shade * ring))) for c in (cr, cg, cb))
    draw = ImageDraw.Draw(image)
    outline = tuple(max(0, int(c * 0.68)) for c in colour)
    draw.ellipse((x0, y0, x1, y1), outline=outline, width=2)
    # Dry neck and root scars are part of the visible bulb silhouette.
    draw.arc((center[0] - radius * 0.53, center[1] - radius * 0.56,
              center[0] + radius * 0.53, center[1] + radius * 0.75), 205, 330,
             fill=tuple(max(0, int(c * 0.72)) for c in colour), width=1)
    draw.ellipse((center[0] - 4, center[1] + radius - 8,
                  center[0] + 4, center[1] + radius - 2), fill=(102, 70, 46))


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), (238, 240, 236))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("DejaVuSans.ttf", 17)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        title_font = small_font = ImageFont.load_default()
    draw.text((30, 22), "PYAazScan  /  SYNTHETIC CV FIXTURE", fill=(66, 82, 72), font=title_font)
    draw.text((30, 49), "Illustration for pipeline testing only — not a field image or dataset", fill=(112, 122, 115), font=small_font)

    bulbs = [
        ((155, 187), 48, (183, 94, 43)),
        ((390, 187), 43, (195, 108, 47)),
        ((630, 187), 50, (175, 84, 42)),
        ((850, 187), 31, (203, 128, 54)),
        ((175, 430), 45, (192, 103, 48)),
        ((415, 430), 51, (177, 85, 47)),
        ((660, 430), 47, (191, 106, 49)),
        ((860, 430), 41, (185, 91, 45)),
    ]
    for index, (center, radius, colour) in enumerate(bulbs, start=1):
        draw_onion(image, center, radius, colour, index)

    draw = ImageDraw.Draw(image)
    # Sprout-like green growth, placed across the silhouette boundary for measurable visual evidence.
    sprout_center, sprout_r = bulbs[4][0], bulbs[4][1]
    top = sprout_center[1] - sprout_r + 8
    draw.line((sprout_center[0], top + 7, sprout_center[0] + 1, top - 32), fill=(45, 127, 58), width=7)
    draw.ellipse((sprout_center[0] - 23, top - 31, sprout_center[0] + 1, top - 19), fill=(64, 150, 69))
    draw.ellipse((sprout_center[0] + 1, top - 18, sprout_center[0] + 24, top - 7), fill=(49, 137, 58))
    draw.line((sprout_center[0] - 5, top - 20, sprout_center[0] + 3, top + 2), fill=(72, 162, 74), width=2)

    # A dark, soft-edged surface patch and a smaller damage mark exercise independent cues.
    cx, cy = bulbs[6][0]
    draw.ellipse((cx - 14, cy - 10, cx + 15, cy + 12), fill=(47, 29, 27))
    draw.ellipse((cx - 8, cy - 6, cx + 10, cy + 7), fill=(68, 36, 31))
    cx, cy = bulbs[7][0]
    draw.ellipse((cx - 11, cy - 9, cx + 2, cy - 3), fill=(48, 33, 28))
    draw.ellipse((cx + 7, cy + 4, cx + 12, cy + 9), fill=(45, 31, 27))

    # The solid blue square has a 50 mm physical side; it is deliberately unique in hue.
    marker_x, marker_y, marker_size = 883, 570, 75
    draw.rectangle((marker_x, marker_y, marker_x + marker_size, marker_y + marker_size), fill=(31, 103, 237))
    draw.rectangle((marker_x + 8, marker_y + 8, marker_x + marker_size - 8, marker_y + marker_size - 8), outline=(244, 247, 244), width=3)
    draw.text((marker_x - 26, marker_y + marker_size + 9), "50 mm reference", fill=(64, 82, 72), font=small_font)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
