#!/usr/bin/env python3
"""Initialize a local OCR fine-tuning workspace from existing scanned pages."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable

IMAGE_EXTENSIONS = {".jpg", ".jpeg"}


def has_pair(image_path: Path) -> bool:
    return image_path.suffix.lower() in IMAGE_EXTENSIONS and image_path.with_suffix(".txt").exists()


def iter_paired_images(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return []
    return sorted(
        (p for p in directory.iterdir() if p.is_file() and has_pair(p)),
        key=lambda p: (p.stat().st_mtime, p.name.casefold()),
    )


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines).strip()
    path.write_text(f"{content}\n" if content else "", encoding="utf-8")


def build_workspace_readme(root: Path) -> str:
    return f"""# OCR Training Workspace

This workspace is initialized for book-specific OCR experiments.

## Folders

- `dataset/raw_pages/`: optional unedited page copies
- `dataset/ground_truth/pages/`: page images + corrected `.txt` pairs
- `dataset/ground_truth/lines/`: optional line-level crops/labels for PaddleOCR `rec`
- `splits/`: manifest files (`train.txt`, `val.txt`, `test.txt`)
- `eval/baseline/`: prediction/reference pairs to compute CER/WER baseline
- `models/`: checkpoints and exported models
- `notes/`: manual notes and experiment logs

## Quick start

1. Copy selected page/image pairs to `dataset/ground_truth/pages/`.
2. Update `splits/train.txt`, `splits/val.txt`, `splits/test.txt` with relative page names.
3. Build baseline metrics before training:

```bash
python scripts/evaluate_ocr_metrics.py \
  --pred-dir {root}/eval/baseline/pred \
  --ref-dir {root}/eval/baseline/ref
```

4. Use `docs/ocr_training_go_no_go_checklist.md` before and after each training round.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create OCR training workspace and starter manifests.")
    parser.add_argument("--workspace", default="ocr-training", help="Workspace directory to create.")
    parser.add_argument("--images-dir", default="images", help="Directory containing active image/text pairs.")
    parser.add_argument("--done-dir", default="images/check-done", help="Directory containing validated image/text pairs.")
    parser.add_argument("--sample-pages", type=int, default=80, help="How many pages to sample into candidate manifest.")
    parser.add_argument("--seed", type=int, default=1976, help="Sampling seed for reproducibility.")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    images_dir = Path(args.images_dir).resolve()
    done_dir = Path(args.done_dir).resolve()

    folders = [
        root / "dataset" / "raw_pages",
        root / "dataset" / "ground_truth" / "pages",
        root / "dataset" / "ground_truth" / "lines",
        root / "splits",
        root / "eval" / "baseline" / "pred",
        root / "eval" / "baseline" / "ref",
        root / "models",
        root / "notes",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    paired_pages = list(iter_paired_images(images_dir)) + list(iter_paired_images(done_dir))
    unique_names = sorted({p.name for p in paired_pages}, key=str.casefold)

    random.seed(args.seed)
    sampled = unique_names[:]
    random.shuffle(sampled)
    sampled = sampled[: max(0, min(args.sample_pages, len(sampled)))]

    write_lines(root / "splits" / "candidate_pages.txt", sampled)
    write_lines(root / "splits" / "train.txt", [])
    write_lines(root / "splits" / "val.txt", [])
    write_lines(root / "splits" / "test.txt", [])
    (root / "README.md").write_text(build_workspace_readme(root), encoding="utf-8")

    print(f"Workspace ready: {root}")
    print(f"Detected paired pages: {len(unique_names)}")
    print(f"Candidate sample written: {root / 'splits' / 'candidate_pages.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

