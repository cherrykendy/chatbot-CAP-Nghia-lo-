#!/usr/bin/env python3
"""Rename references from 'AI CAP' to 'ai-cap' across the repo."""
from __future__ import annotations

import argparse
import difflib
import re
from pathlib import Path
from typing import Iterator, Sequence

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "venv",
    "__pycache__",
}

ALLOWED_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".json",
    ".yml",
    ".yaml",
    ".md",
    ".sh",
    ".bat",
    ".ini",
    ".toml",
}

ALLOWED_BASENAMES = {
    "Dockerfile",
}

ALLOWED_PREFIXES = (
    ".env",
)

ALLOWED_SPECIAL_DIRS = {
    (".github", "workflows"),
}

REPLACEMENTS: Sequence[tuple[re.Pattern[str], str]] = (
    (re.compile(r"/AI[ _-]?CAP/", flags=re.IGNORECASE), "/ai-cap/"),
    (re.compile(r"\\AI[ _-]?CAP\\", flags=re.IGNORECASE), r"\\ai-cap\\"),
    (re.compile(r"AI%20CAP", flags=re.IGNORECASE), "ai-cap"),
)


def iter_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if not is_allowed_file(path):
            continue
        yield path


def is_allowed_file(path: Path) -> bool:
    if path.name in ALLOWED_BASENAMES:
        return True
    if path.suffix in ALLOWED_SUFFIXES:
        return True
    if any(path.name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return True
    for special in ALLOWED_SPECIAL_DIRS:
        if path.parts[: len(special)] == special:
            return True
    return False


def apply_replacements(text: str) -> tuple[str, bool]:
    modified = False
    for pattern, replacement in REPLACEMENTS:
        new_text, count = pattern.subn(replacement, text)
        if count:
            modified = True
            text = new_text
    return text, modified


def preview_diff(original: str, updated: str, path: Path) -> str:
    diff = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile=str(path),
        tofile=str(path),
        lineterm="",
    )
    return "\n".join(diff)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply changes in-place instead of dry-run preview",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists():
        parser.error(f"Root path {root} does not exist")

    any_changes = False
    for path in iter_files(root):
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated, modified = apply_replacements(original)
        if not modified:
            continue
        any_changes = True
        diff = preview_diff(original, updated, path)
        print(f"--- {path}")
        if diff:
            print(diff)
        if args.write:
            path.write_text(updated, encoding="utf-8")
    if not any_changes:
        print("No matches found.")
    elif args.write:
        print("Done. Changes written.")
    else:
        print("Dry-run complete. Re-run with --write to apply changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
