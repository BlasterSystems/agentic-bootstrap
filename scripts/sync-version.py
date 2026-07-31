#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentic_bootstrap import __version__  # noqa: E402


def _regular_file_stat(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"{path} does not exist") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{path} must be a regular file, not a symlink or other file type")
    return metadata


def synchronize(root: Path, version: str, *, check: bool) -> int:
    agentic = root / ".agentic"
    try:
        agentic_metadata = agentic.lstat()
    except FileNotFoundError:
        print(f"{agentic} does not exist", file=sys.stderr)
        return 1
    if not stat.S_ISDIR(agentic_metadata.st_mode):
        print(f"{agentic} must be a real directory", file=sys.stderr)
        return 1

    path = agentic / "config.json"
    try:
        original = _regular_file_stat(path)
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return 1

    current = data.get("generator_version")
    display_path = path.relative_to(root)
    if current == version:
        print(f"{display_path} is synchronized at {version}")
        return 0
    if check:
        print(f"{display_path} has {current!r}; expected {version!r}", file=sys.stderr)
        return 1

    data["generator_version"] = version
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=agentic,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(stat.S_IMODE(original.st_mode))

        # Recheck immediately before replacement. If a concurrent actor swaps the
        # destination, abort instead of treating the new path as repository state.
        _regular_file_stat(path)
        os.replace(temporary, path)
        temporary = None
    except (ValueError, OSError) as exc:
        print(f"cannot update {path}: {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    print(f"updated {display_path} to {version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize repository-derived version metadata with agentic_bootstrap.__version__."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without changing files",
    )
    args = parser.parse_args()
    return synchronize(ROOT, __version__, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
