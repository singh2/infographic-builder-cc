#!/usr/bin/env python3
"""Stitch multiple PNG panel images into a single combined infographic.

Usage:
    python stitch.py --panels p1.png p2.png p3.png --output combined.png
    python stitch.py --panels p1.png p2.png --output combined.png --direction horizontal
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def stitch(panel_paths: list[str], output_path: str, direction: str = "vertical"):
    """Stack panel images into a single combined image."""
    if len(panel_paths) < 2:
        print("Error: Need at least 2 panel paths to stitch.", file=sys.stderr)
        sys.exit(1)

    try:
        images = [Image.open(p).convert("RGBA") for p in panel_paths]
    except FileNotFoundError as e:
        print(f"Error: Panel file not found: {e}", file=sys.stderr)
        sys.exit(1)

    if direction == "horizontal":
        total_width = sum(img.width for img in images)
        total_height = max(img.height for img in images)
        combined = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 255))
        x_offset = 0
        for img in images:
            combined.paste(img, (x_offset, 0))
            x_offset += img.width
    else:
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        combined = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 255))
        y_offset = 0
        for img in images:
            combined.paste(img, (0, y_offset))
            y_offset += img.height

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(out), "PNG")

    label = "vertically" if direction == "vertical" else "horizontally"
    print(
        f"Stitched {len(images)} panels {label} -> {output_path} ({total_width}x{total_height}px)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Stitch infographic panels into a combined image"
    )
    parser.add_argument(
        "--panels", nargs="+", required=True, help="Ordered list of panel PNG paths"
    )
    parser.add_argument(
        "--output", required=True, help="Output path for combined image"
    )
    parser.add_argument(
        "--direction",
        choices=["vertical", "horizontal"],
        default="vertical",
        help="Stack direction (default: vertical)",
    )
    args = parser.parse_args()
    stitch(args.panels, args.output, args.direction)


if __name__ == "__main__":
    main()
