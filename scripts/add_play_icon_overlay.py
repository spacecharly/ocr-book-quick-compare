#!/usr/bin/env python3
"""Add a centered YouTube-like play icon overlay on a cover image.

Usage:
    python scripts/add_play_icon_overlay.py \
      --input resources/imgs/capture-app-cover.png \
      --output resources/imgs/capture-app-cover.png

Requires Pillow (PIL).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def draw_play_overlay(cover: Image.Image, width_ratio: float = 0.22) -> Image.Image:
    """Return a copy of `cover` with a centered play icon overlay."""
    result = cover.convert("RGBA")

    icon_w = max(60, int(result.width * width_ratio))
    icon_h = max(40, int(icon_w * 0.68))

    icon = Image.new("RGBA", (icon_w, icon_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)

    radius = max(8, int(icon_h * 0.24))
    draw.rounded_rectangle(
        (0, 0, icon_w - 1, icon_h - 1),
        radius=radius,
        fill=(255, 0, 0, 240),
    )

    tri_w = max(12, int(icon_w * 0.24))
    tri_h = max(12, int(icon_h * 0.34))
    cx = icon_w // 2 + int(icon_w * 0.03)
    cy = icon_h // 2
    triangle = [
        (cx - tri_w // 2, cy - tri_h // 2),
        (cx - tri_w // 2, cy + tri_h // 2),
        (cx + tri_w // 2, cy),
    ]
    draw.polygon(triangle, fill=(255, 255, 255, 255))

    alpha = icon.getchannel("A")
    shadow = Image.new("RGBA", icon.size, (0, 0, 0, 150))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(8)))

    x = (result.width - icon_w) // 2
    y = (result.height - icon_h) // 2
    result.alpha_composite(shadow, (x + 8, y + 10))
    result.alpha_composite(icon, (x, y))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", help="Output image path (default: overwrite input)")
    parser.add_argument(
        "--width-ratio",
        type=float,
        default=0.22,
        help="Icon width ratio relative to image width (default: 0.22)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        parser.error(f"Input file does not exist: {input_path}")

    with Image.open(input_path) as src:
        out = draw_play_overlay(src, width_ratio=args.width_ratio)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out.save(output_path)

    print(f"Play icon overlay added: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

