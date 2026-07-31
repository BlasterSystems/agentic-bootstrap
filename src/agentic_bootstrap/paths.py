from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath


class UnsafePathError(ValueError):
    pass


def normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise UnsafePathError(f"unsafe generated path: {value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise UnsafePathError(f"unsafe generated path: {value!r}")
    normalized = pure.as_posix()
    if normalized != value:
        raise UnsafePathError(f"non-normalized generated path: {value!r}")
    return normalized


def assert_safe_target_path(
    root: Path,
    relative: str,
    *,
    allow_missing_leaf: bool = True,
    allow_leaf_symlink: bool = False,
) -> Path:
    relative = normalize_relative_path(relative)
    root = root.resolve()
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError(f"path escapes target: {relative}") from exc

    current = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        is_leaf = index == len(parts) - 1
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            if is_leaf and not allow_missing_leaf:
                raise UnsafePathError(f"required path is missing: {relative}")
            continue
        except OSError as exc:
            raise UnsafePathError(f"cannot inspect {current}: {exc}") from exc
        if stat.S_ISLNK(mode):
            if is_leaf and allow_leaf_symlink:
                continue
            raise UnsafePathError(f"symlinked path component is not allowed: {current}")
        if not is_leaf and not stat.S_ISDIR(mode):
            raise UnsafePathError(f"non-directory path component: {current}")
    return candidate


def assert_safe_root_parent(root: Path) -> None:
    """Reject symlink ancestors between the nearest existing parent and the target."""
    absolute = root.absolute()
    current = absolute
    missing: list[Path] = []
    while not current.exists() and not current.is_symlink():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    if current.is_symlink():
        raise UnsafePathError(f"target ancestor is a symlink: {current}")
    # Existing ancestors above the nearest existing parent are outside generator control.
    # Every created component is checked again immediately before use.
    for path in reversed(missing):
        if path.exists() and path.is_symlink():
            raise UnsafePathError(f"target ancestor became a symlink: {path}")
