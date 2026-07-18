#!/usr/bin/env python3
"""Offline spell correction helper for OCR text files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from spellchecker import SpellChecker

TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ]+)*")


def preserve_case(original: str, corrected: str) -> str:
    if original.isupper():
        return corrected.upper()
    if original[:1].isupper():
        return corrected[:1].upper() + corrected[1:]
    return corrected


def correct_text(text: str, checker: SpellChecker) -> tuple[str, int]:
    changes = 0

    def _replace(match) -> str:
        nonlocal changes
        token = match.group(0)
        if len(token) <= 2 or token.isupper():
            return token

        lowered = token.casefold()
        if lowered not in checker.unknown([lowered]):
            return token

        suggestion = checker.correction(lowered)
        if not suggestion or suggestion == lowered:
            return token

        changes += 1
        return preserve_case(token, suggestion)

    return TOKEN_PATTERN.sub(_replace, text), changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply offline spell correction to OCR .txt files.")
    parser.add_argument("--input-dir", required=True, help="Folder containing .txt files to correct.")
    parser.add_argument("--language", default="fr", choices=["fr", "en", "it", "de"], help="Dictionary language.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.exists():
        raise SystemExit(f"Directory does not exist: {input_dir}")

    checker = SpellChecker(language=args.language, distance=1)
    files = sorted(input_dir.glob("*.txt"), key=lambda p: p.name.casefold())
    if not files:
        raise SystemExit(f"No .txt files found in {input_dir}")

    touched_files = 0
    total_changes = 0

    for path in files:
        original = path.read_text(encoding="utf-8", errors="ignore")
        corrected, changes = correct_text(original, checker)
        if changes <= 0:
            continue

        touched_files += 1
        total_changes += changes
        if args.dry_run:
            print(f"[DRY-RUN] {path.name}: {changes} candidate fixes")
            continue

        path.write_text(corrected, encoding="utf-8")
        print(f"[UPDATED] {path.name}: {changes} fixes")

    print(f"Processed files: {len(files)}")
    print(f"Touched files: {touched_files}")
    print(f"Total candidate fixes: {total_changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

