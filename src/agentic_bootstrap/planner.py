from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .manifest import MANIFEST_PATH, Manifest, ManifestError, sha256_bytes, sha256_path
from .model import GeneratedFile
from .paths import UnsafePathError, assert_safe_root_parent, assert_safe_target_path, normalize_relative_path


class Action(str, Enum):
    CREATE = "CREATE"
    UPDATE_GENERATED = "UPDATE_GENERATED"
    NO_CHANGE = "NO_CHANGE"
    SKIP_UNMANAGED = "SKIP_UNMANAGED"
    CONFLICT = "CONFLICT"
    REMOVE_OBSOLETE = "REMOVE_OBSOLETE"
    PRUNE_MISSING = "PRUNE_MISSING"
    MANIFEST_CREATE = "MANIFEST_CREATE"
    MANIFEST_UPDATE = "MANIFEST_UPDATE"


@dataclass(frozen=True)
class Operation:
    path: str
    action: Action
    generated: GeneratedFile | None = None
    detail: str = ""
    expected_hash: str | None = None
    expected_executable: bool | None = None


@dataclass
class Plan:
    root: Path
    operations: list[Operation]
    previous_manifest: Manifest
    manifest_hash: str | None
    root_existed: bool

    @property
    def conflicts(self) -> list[Operation]:
        return [operation for operation in self.operations if operation.action == Action.CONFLICT]

    @property
    def changes(self) -> list[Operation]:
        return [
            operation
            for operation in self.operations
            if operation.action in {
                Action.CREATE,
                Action.UPDATE_GENERATED,
                Action.REMOVE_OBSOLETE,
                Action.PRUNE_MISSING,
                Action.MANIFEST_CREATE,
                Action.MANIFEST_UPDATE,
            }
        ]

    def format(self) -> str:
        lines = [f"Plan for {self.root}:"]
        for operation in self.operations:
            suffix = f" — {operation.detail}" if operation.detail else ""
            lines.append(f"  {operation.action.value:18} {operation.path}{suffix}")
        counts: dict[Action, int] = {}
        for operation in self.operations:
            counts[operation.action] = counts.get(operation.action, 0) + 1
        summary = ", ".join(f"{action.value}={counts[action]}" for action in Action if action in counts)
        lines.append(f"Summary: {summary or 'no operations'}")
        return "\n".join(lines)


def _exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _is_executable(path: Path) -> bool:
    return bool(os.lstat(path).st_mode & stat.S_IXUSR)


def build_plan(
    root: Path,
    desired: dict[str, GeneratedFile],
    *,
    remove_obsolete: bool = False,
) -> Plan:
    root = Path(os.path.normpath(str(root.expanduser().absolute())))
    operations: list[Operation] = []
    root_existed = root.exists() or root.is_symlink()

    try:
        assert_safe_root_parent(root)
    except UnsafePathError as exc:
        empty = Manifest()
        return Plan(root, [Operation(".", Action.CONFLICT, detail=str(exc))], empty, None, root_existed)

    normalized_desired: dict[str, GeneratedFile] = {}
    for relative, generated in desired.items():
        try:
            normalized = normalize_relative_path(relative)
        except UnsafePathError as exc:
            operations.append(Operation(str(relative), Action.CONFLICT, generated, str(exc)))
            continue
        if normalized == MANIFEST_PATH:
            operations.append(Operation(normalized, Action.CONFLICT, generated, "manifest is managed internally"))
            continue
        normalized_desired[normalized] = generated

    manifest_path = root / MANIFEST_PATH
    manifest_hash: str | None = None
    manifest = Manifest()
    manifest_metadata_changed = False
    manifest_error: str | None = None
    if _exists(manifest_path):
        try:
            assert_safe_target_path(root, MANIFEST_PATH, allow_missing_leaf=False)
            if not stat.S_ISREG(os.lstat(manifest_path).st_mode):
                raise ManifestError("ownership manifest must be a regular file")
            manifest_hash = sha256_path(manifest_path)
            manifest = Manifest.load(root)
        except (UnsafePathError, ManifestError, OSError) as exc:
            manifest_error = str(exc)
            operations.append(Operation(MANIFEST_PATH, Action.CONFLICT, detail=manifest_error))

    for relative, generated in sorted(normalized_desired.items()):
        try:
            path = assert_safe_target_path(root, relative)
        except UnsafePathError as exc:
            operations.append(Operation(relative, Action.CONFLICT, generated, str(exc)))
            continue
        previous = manifest.files.get(relative)
        if not _exists(path):
            operations.append(Operation(relative, Action.CREATE, generated))
            continue
        try:
            destination_mode = os.lstat(path).st_mode
        except OSError as exc:
            operations.append(Operation(relative, Action.CONFLICT, generated, f"cannot inspect destination: {exc}"))
            continue
        if stat.S_ISLNK(destination_mode):
            operations.append(Operation(relative, Action.CONFLICT, generated, "symlink destination is unmanaged"))
            continue
        if not stat.S_ISREG(destination_mode):
            operations.append(Operation(relative, Action.CONFLICT, generated, "destination is not a regular file"))
            continue
        try:
            current_hash = sha256_path(path)
        except OSError as exc:
            operations.append(Operation(relative, Action.CONFLICT, generated, f"cannot read destination: {exc}"))
            continue
        desired_hash = sha256_bytes(generated.content)
        if previous and bool(previous.get("mutable", False)) != generated.mutable:
            manifest_metadata_changed = True
        if (
            previous
            and previous.get("mutable", False)
            and current_hash != previous.get("sha256")
        ):
            operations.append(
                Operation(
                    relative,
                    Action.NO_CHANGE,
                    generated,
                    "mutable generated seed was customized and is preserved",
                    expected_hash=current_hash,
                    expected_executable=_is_executable(path),
                )
            )
            continue
        if current_hash == desired_hash:
            if previous:
                if _is_executable(path) != generated.executable:
                    operations.append(
                        Operation(
                            relative,
                            Action.UPDATE_GENERATED,
                            generated,
                            "executable mode drift",
                            expected_hash=current_hash,
                            expected_executable=_is_executable(path),
                        )
                    )
                else:
                    operations.append(
                        Operation(
                            relative,
                            Action.NO_CHANGE,
                            generated,
                            "owned generated file",
                            expected_hash=current_hash,
                            expected_executable=_is_executable(path),
                        )
                    )
            else:
                operations.append(
                    Operation(
                        relative,
                        Action.SKIP_UNMANAGED,
                        generated,
                        "identical unmanaged file remains user-owned",
                        expected_hash=current_hash,
                        expected_executable=_is_executable(path),
                    )
                )
            continue
        if previous:
            if current_hash == previous.get("sha256") and _is_executable(path) == previous.get("executable"):
                operations.append(
                    Operation(
                        relative,
                        Action.UPDATE_GENERATED,
                        generated,
                        expected_hash=current_hash,
                        expected_executable=_is_executable(path),
                    )
                )
            else:
                operations.append(Operation(relative, Action.CONFLICT, generated, "generated file content or mode was modified"))
        else:
            operations.append(Operation(relative, Action.CONFLICT, generated, "unmanaged destination exists"))

    if not manifest_error:
        for relative in sorted(set(manifest.files) - set(normalized_desired)):
            try:
                path = assert_safe_target_path(root, relative)
            except UnsafePathError as exc:
                operations.append(Operation(relative, Action.CONFLICT, None, str(exc)))
                continue
            if not _exists(path):
                operations.append(Operation(relative, Action.PRUNE_MISSING, None, "remove stale manifest claim"))
                continue
            previous = manifest.files[relative]
            if path.is_file() and not path.is_symlink() and sha256_path(path) == previous.get("sha256") and _is_executable(path) == previous.get("executable"):
                operations.append(
                    Operation(
                        relative,
                        Action.REMOVE_OBSOLETE,
                        None,
                        "requires --remove-obsolete",
                        expected_hash=previous.get("sha256"),
                        expected_executable=previous.get("executable"),
                    )
                )
            else:
                operations.append(Operation(relative, Action.CONFLICT, None, "obsolete generated path was modified"))

    content_changes = any(
        operation.action in {
            Action.CREATE,
            Action.UPDATE_GENERATED,
            Action.PRUNE_MISSING,
        }
        for operation in operations
    ) or manifest_metadata_changed or (
        remove_obsolete
        and any(operation.action == Action.REMOVE_OBSOLETE for operation in operations)
    )
    if manifest_error:
        pass
    elif manifest_hash is None:
        operations.append(Operation(MANIFEST_PATH, Action.MANIFEST_CREATE))
    elif content_changes:
        operations.append(Operation(MANIFEST_PATH, Action.MANIFEST_UPDATE))
    else:
        operations.append(Operation(MANIFEST_PATH, Action.NO_CHANGE, detail="owned manifest"))

    return Plan(
        root=root,
        operations=operations,
        previous_manifest=manifest,
        manifest_hash=manifest_hash,
        root_existed=root_existed,
    )
