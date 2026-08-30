#!/usr/bin/env python3
"""Safely restore runtime files to a legacy Codex plugin cache directory.

The script copies only the plugin's runtime files. Existing identical files are
left untouched, while conflicting files cause the operation to stop without
overwriting them.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


RUNTIME_PATHS = (".codex-plugin", "hooks", "scripts", "skills")
IGNORED_NAMES = {"__pycache__", ".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cache_root() -> Path:
    return (Path.home() / ".codex" / "plugins" / "cache").resolve()


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def runtime_files(source: Path):
    for relative_root in RUNTIME_PATHS:
        root = source / relative_root
        if not root.exists():
            continue
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(source)
            if any(part in IGNORED_NAMES for part in relative.parts):
                continue
            if candidate.suffix in IGNORED_SUFFIXES:
                continue
            yield candidate, relative


def restore(destination: Path) -> tuple[int, int]:
    source = plugin_root()
    destination = destination.expanduser().resolve()
    allowed_root = cache_root()

    if not is_inside(destination, allowed_root) or destination == allowed_root:
        raise ValueError(f"destination must be a version directory inside {allowed_root}")
    if destination == source:
        raise ValueError("destination cannot be the current plugin directory")

    planned: list[tuple[Path, Path]] = []
    unchanged = 0
    for source_file, relative in runtime_files(source):
        destination_file = destination / relative
        if destination_file.exists():
            if not destination_file.is_file() or not filecmp.cmp(
                source_file, destination_file, shallow=False
            ):
                raise FileExistsError(
                    f"conflicting file already exists; nothing was overwritten: {destination_file}"
                )
            unchanged += 1
        else:
            planned.append((source_file, destination_file))

    for source_file, destination_file in planned:
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)

    hook_script = destination / "scripts" / "thread_titler_hook.py"
    if not hook_script.is_file():
        raise RuntimeError(f"restored cache is missing {hook_script}")
    return len(planned), unchanged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore this plugin's runtime files to an old Codex cache path."
    )
    parser.add_argument(
        "destination",
        type=Path,
        help="Exact old version directory shown in the Codex hook error",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        copied, unchanged = restore(args.destination)
    except (FileExistsError, OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Compatibility cache restored: {copied} copied, {unchanged} already identical.")
    print("Restart or reopen the older Codex task and try again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
