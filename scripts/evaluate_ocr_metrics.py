#!/usr/bin/env python3
"""Compute OCR metrics (CER/WER) from predicted vs reference text files."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileMetrics:
    name: str
    cer: float
    wer: float
    char_errors: int
    char_ref_len: int
    word_errors: int
    word_ref_len: int


def levenshtein_distance(seq_a: list[str], seq_b: list[str]) -> int:
    if not seq_a:
        return len(seq_b)
    if not seq_b:
        return len(seq_a)

    prev = list(range(len(seq_b) + 1))
    for i, token_a in enumerate(seq_a, start=1):
        curr = [i] + [0] * len(seq_b)
        for j, token_b in enumerate(seq_b, start=1):
            cost = 0 if token_a == token_b else 1
            curr[j] = min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + cost,
            )
        prev = curr
    return prev[-1]


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def cer_and_counts(pred: str, ref: str) -> tuple[float, int, int]:
    ref_chars = list(ref)
    pred_chars = list(pred)
    errors = levenshtein_distance(ref_chars, pred_chars)
    denominator = max(1, len(ref_chars))
    return errors / denominator, errors, len(ref_chars)


def wer_and_counts(pred: str, ref: str) -> tuple[float, int, int]:
    ref_words = ref.split()
    pred_words = pred.split()
    errors = levenshtein_distance(ref_words, pred_words)
    denominator = max(1, len(ref_words))
    return errors / denominator, errors, len(ref_words)


def evaluate_pair(pred_file: Path, ref_file: Path) -> FileMetrics:
    pred_text = normalize_text(pred_file.read_text(encoding="utf-8", errors="ignore"))
    ref_text = normalize_text(ref_file.read_text(encoding="utf-8", errors="ignore"))

    cer, char_errors, char_ref_len = cer_and_counts(pred_text, ref_text)
    wer, word_errors, word_ref_len = wer_and_counts(pred_text, ref_text)
    return FileMetrics(
        name=pred_file.name,
        cer=cer,
        wer=wer,
        char_errors=char_errors,
        char_ref_len=char_ref_len,
        word_errors=word_errors,
        word_ref_len=word_ref_len,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate OCR quality with CER/WER.")
    parser.add_argument("--pred-dir", required=True, help="Directory containing OCR predicted .txt files.")
    parser.add_argument("--ref-dir", required=True, help="Directory containing corrected reference .txt files.")
    parser.add_argument("--top", type=int, default=10, help="Number of worst files to print.")
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    args = parser.parse_args()

    pred_dir = Path(args.pred_dir).resolve()
    ref_dir = Path(args.ref_dir).resolve()

    if not pred_dir.exists() or not ref_dir.exists():
        raise SystemExit("Both --pred-dir and --ref-dir must exist.")

    pred_files = sorted(pred_dir.glob("*.txt"), key=lambda p: p.name.casefold())
    if not pred_files:
        raise SystemExit(f"No .txt files found in {pred_dir}")

    metrics: list[FileMetrics] = []
    missing_refs: list[str] = []

    for pred_file in pred_files:
        ref_file = ref_dir / pred_file.name
        if not ref_file.exists():
            missing_refs.append(pred_file.name)
            continue
        metrics.append(evaluate_pair(pred_file, ref_file))

    if not metrics:
        raise SystemExit("No matching prediction/reference pairs found.")

    total_char_errors = sum(item.char_errors for item in metrics)
    total_char_ref = sum(item.char_ref_len for item in metrics)
    total_word_errors = sum(item.word_errors for item in metrics)
    total_word_ref = sum(item.word_ref_len for item in metrics)

    global_cer = total_char_errors / max(1, total_char_ref)
    global_wer = total_word_errors / max(1, total_word_ref)

    print(f"Matched files: {len(metrics)}")
    print(f"Missing references: {len(missing_refs)}")
    if missing_refs:
        print("Missing sample:", ", ".join(missing_refs[:5]))
    print(f"Global CER: {global_cer:.4f} ({global_cer * 100:.2f}%)")
    print(f"Global WER: {global_wer:.4f} ({global_wer * 100:.2f}%)")

    worst = sorted(metrics, key=lambda m: m.cer, reverse=True)[: max(1, args.top)]
    print("\nWorst CER files:")
    for item in worst:
        print(f"- {item.name}: CER={item.cer:.4f} WER={item.wer:.4f}")

    if args.output_json:
        payload = {
            "matched_files": len(metrics),
            "missing_references": missing_refs,
            "global": {
                "cer": global_cer,
                "wer": global_wer,
                "char_errors": total_char_errors,
                "char_reference_length": total_char_ref,
                "word_errors": total_word_errors,
                "word_reference_length": total_word_ref,
            },
            "files": [
                {
                    "name": item.name,
                    "cer": item.cer,
                    "wer": item.wer,
                    "char_errors": item.char_errors,
                    "char_reference_length": item.char_ref_len,
                    "word_errors": item.word_errors,
                    "word_reference_length": item.word_ref_len,
                }
                for item in metrics
            ],
        }
        Path(args.output_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"JSON report written: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

