from __future__ import annotations

import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import __version__
from .manifest import MANIFEST_PATH, Manifest, sha256_path
from .paths import UnsafePathError, assert_safe_root_parent, assert_safe_target_path
from .planner import Action, Operation, Plan


class ApplyError(RuntimeError):
    pass


@dataclass
class SavedPath:
    destination: Path
    backup: Path


def _exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _executable(path: Path) -> bool:
    return bool(os.lstat(path).st_mode & stat.S_IXUSR)


def _assert_expected(operation: Operation, destination: Path) -> None:
    if operation.action in {Action.CREATE, Action.PRUNE_MISSING}:
        if _exists(destination):
            raise ApplyError(f"stale plan: {operation.path} appeared after planning")
        return
    if operation.action in {
        Action.UPDATE_GENERATED,
        Action.REMOVE_OBSOLETE,
        Action.NO_CHANGE,
        Action.SKIP_UNMANAGED,
    }:
        if not destination.is_file() or destination.is_symlink():
            raise ApplyError(f"stale plan: destination type changed: {operation.path}")
        if operation.expected_hash and sha256_path(destination) != operation.expected_hash:
            raise ApplyError(f"stale plan: destination content changed: {operation.path}")
        if operation.expected_executable is not None and _executable(destination) != operation.expected_executable:
            raise ApplyError(f"stale plan: destination mode changed: {operation.path}")


def _save(destination: Path, backup_root: Path, relative: str) -> SavedPath:
    saved = backup_root / relative
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(destination, saved)
    return SavedPath(destination=destination, backup=saved)


def _restore(saved: SavedPath) -> None:
    if _exists(saved.destination):
        if saved.destination.is_dir() and not saved.destination.is_symlink():
            shutil.rmtree(saved.destination)
        else:
            saved.destination.unlink()
    saved.destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(saved.backup, saved.destination)


def _mkdir_tracked(path: Path, boundary_parent: Path, created_dirs: list[Path]) -> None:
    missing: list[Path] = []
    current = path
    while current != boundary_parent and not _exists(current):
        missing.append(current)
        current = current.parent
    if current.is_symlink() or (current.exists() and not current.is_dir()):
        raise ApplyError(f"unsafe directory component: {current}")
    for directory in reversed(missing):
        try:
            directory.mkdir()
            created_dirs.append(directory)
        except FileExistsError:
            if directory.is_symlink() or not directory.is_dir():
                raise ApplyError(f"directory changed during apply: {directory}")


def _preflight(plan: Plan, remove_obsolete: bool) -> None:
    root = plan.root
    assert_safe_root_parent(root)
    exists_now = root.exists() or root.is_symlink()
    if exists_now != plan.root_existed:
        raise ApplyError("stale plan: target existence changed after planning")
    if root.is_symlink():
        raise ApplyError("target root must not be a symlink")

    manifest_path = root / MANIFEST_PATH
    if plan.manifest_hash is None:
        if _exists(manifest_path):
            raise ApplyError("stale plan: ownership manifest appeared after planning")
    else:
        assert_safe_target_path(root, MANIFEST_PATH, allow_missing_leaf=False)
        if not manifest_path.is_file() or sha256_path(manifest_path) != plan.manifest_hash:
            raise ApplyError("stale plan: ownership manifest changed after planning")

    for operation in plan.operations:
        if operation.action in {Action.MANIFEST_CREATE, Action.MANIFEST_UPDATE, Action.CONFLICT}:
            continue
        if operation.path == MANIFEST_PATH:
            continue
        if operation.action == Action.REMOVE_OBSOLETE and not remove_obsolete:
            continue
        destination = assert_safe_target_path(root, operation.path)
        _assert_expected(operation, destination)


def _revalidate_passive_operations(plan: Plan) -> None:
    for operation in plan.operations:
        if operation.action not in {Action.NO_CHANGE, Action.SKIP_UNMANAGED, Action.PRUNE_MISSING}:
            continue
        if operation.path == MANIFEST_PATH:
            continue
        destination = assert_safe_target_path(plan.root, operation.path)
        _assert_expected(operation, destination)


def apply_plan(
    plan: Plan,
    platforms: list[str],
    remove_obsolete: bool = False,
    validator: Callable[[Path], list[str]] | None = None,
) -> Manifest:
    if plan.conflicts:
        raise ApplyError("plan contains conflicts; no files were changed")
    try:
        _preflight(plan, remove_obsolete)
    except (UnsafePathError, OSError) as exc:
        raise ApplyError(f"unsafe or stale plan: {exc}") from exc

    root = plan.root
    data_changes = [
        operation
        for operation in plan.operations
        if operation.action in {
            Action.CREATE,
            Action.UPDATE_GENERATED,
            Action.PRUNE_MISSING,
        }
        or (operation.action == Action.REMOVE_OBSOLETE and remove_obsolete)
    ]
    manifest_change = any(
        operation.action in {Action.MANIFEST_CREATE, Action.MANIFEST_UPDATE}
        for operation in plan.operations
    )
    if not data_changes and not manifest_change:
        return plan.previous_manifest

    root_parent = root.parent
    stage_parent = root_parent
    while not stage_parent.exists() and stage_parent.parent != stage_parent:
        stage_parent = stage_parent.parent
    if stage_parent.is_symlink() or not stage_parent.is_dir():
        raise ApplyError(f"unsafe staging parent: {stage_parent}")
    stage = Path(tempfile.mkdtemp(prefix=".agentic-stage-", dir=stage_parent))
    backup = Path(tempfile.mkdtemp(prefix=".agentic-backup-", dir=stage_parent))
    created_files: list[Path] = []
    created_dirs: list[Path] = []
    saved_paths: list[SavedPath] = []

    try:
        _mkdir_tracked(root, stage_parent, created_dirs)

        for operation in plan.operations:
            if operation.action not in {Action.CREATE, Action.UPDATE_GENERATED}:
                continue
            assert operation.generated is not None
            staged = stage / operation.path
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(operation.generated.content)
            staged.chmod(0o755 if operation.generated.executable else 0o644)

        for operation in plan.operations:
            if operation.action in {Action.CREATE, Action.UPDATE_GENERATED}:
                assert operation.generated is not None
                destination = assert_safe_target_path(root, operation.path)
                _assert_expected(operation, destination)
                _mkdir_tracked(destination.parent, root.parent, created_dirs)
                destination = assert_safe_target_path(root, operation.path)
                _assert_expected(operation, destination)
                staged_path = stage / operation.path
                if operation.action == Action.CREATE:
                    try:
                        os.link(staged_path, destination, follow_symlinks=False)
                    except FileExistsError as exc:
                        raise ApplyError(f"stale plan: {operation.path} appeared during apply") from exc
                    staged_path.unlink()
                    created_files.append(destination)
                else:
                    saved_paths.append(_save(destination, backup, operation.path))
                    os.replace(staged_path, destination)
                destination.chmod(0o755 if operation.generated.executable else 0o644)
            elif operation.action == Action.REMOVE_OBSOLETE and remove_obsolete:
                destination = assert_safe_target_path(root, operation.path, allow_missing_leaf=False)
                _assert_expected(operation, destination)
                saved_paths.append(_save(destination, backup, operation.path))
                destination.unlink()

        _revalidate_passive_operations(plan)
        manifest = Manifest(generator_version=__version__, platforms=platforms)
        for operation in plan.operations:
            if operation.generated is not None and operation.action in {
                Action.CREATE,
                Action.UPDATE_GENERATED,
                Action.NO_CHANGE,
            }:
                destination = assert_safe_target_path(root, operation.path, allow_missing_leaf=False)
                if operation.action == Action.NO_CHANGE:
                    _assert_expected(operation, destination)
                manifest.files[operation.path] = {
                    "sha256": sha256_path(destination),
                    "executable": _executable(destination),
                    "mutable": operation.generated.mutable,
                }
            elif operation.action == Action.REMOVE_OBSOLETE and not remove_obsolete:
                previous = plan.previous_manifest.files.get(operation.path)
                if previous:
                    manifest.files[operation.path] = previous

        manifest_path = assert_safe_target_path(root, MANIFEST_PATH)
        _mkdir_tracked(manifest_path.parent, root.parent, created_dirs)
        manifest_tmp = stage / "manifest.json"
        manifest_tmp.write_bytes(manifest.to_bytes())
        if _exists(manifest_path):
            saved_paths.append(_save(manifest_path, backup, MANIFEST_PATH))
            os.replace(manifest_tmp, manifest_path)
        else:
            try:
                os.link(manifest_tmp, manifest_path, follow_symlinks=False)
            except FileExistsError as exc:
                raise ApplyError("stale plan: ownership manifest appeared during apply") from exc
            manifest_tmp.unlink()
            created_files.append(manifest_path)

        if validator:
            errors = validator(root)
            if errors:
                raise ApplyError("post-stage validation failed: " + "; ".join(errors))
        return manifest
    except Exception as exc:
        for destination in reversed(created_files):
            try:
                if _exists(destination):
                    destination.unlink()
            except OSError:
                pass
        for saved in reversed(saved_paths):
            try:
                _restore(saved)
            except OSError:
                pass
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        if isinstance(exc, ApplyError):
            raise
        raise ApplyError(f"apply failed and rollback was attempted: {exc}") from exc
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
