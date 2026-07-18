from __future__ import annotations

from datetime import datetime
from pathlib import Path


def timestamp_slug(now: datetime | None = None) -> str:
    """Return a millisecond timestamp suitable for filenames."""
    ts = now or datetime.now()
    return ts.strftime("%Y%m%d-%H%M%S-%f")[:-3]


def build_capture_paths(output_dir: Path, mode: str, now: datetime | None = None) -> list[Path]:
    """Build destination image paths for one-page or two-page capture mode."""
    slug = timestamp_slug(now)
    if mode == "two_pages":
        return [output_dir / f"{slug}-left.jpg", output_dir / f"{slug}-right.jpg"]
    return [output_dir / f"{slug}.jpg"]


def split_two_pages(frame):
    """Split a frame vertically in the middle and return (left, right)."""
    height, width = frame.shape[:2]
    midpoint = width // 2
    left = frame[:, :midpoint]
    right = frame[:, midpoint:width]
    return left, right


def draw_alignment_overlay(frame, enabled: bool):
    """Draw a visible center alignment line to help with two-page framing."""
    if not enabled:
        return frame

    import cv2

    preview = frame.copy()
    height, width = preview.shape[:2]
    midpoint = width // 2
    cv2.line(preview, (midpoint, 0), (midpoint, height), (0, 255, 0), 2)
    return preview


