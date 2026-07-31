from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from . import __version__
from .manifest import MANIFEST_PATH, sha256_bytes
from .model import BootstrapRequest, GeneratedFile, SUPPORTED_PLATFORMS
from .paths import UnsafePathError, assert_safe_root_parent, normalize_relative_path
from .planner import Action, Plan

INTENT_SCHEMA = "agentic-bootstrap-intent/v1"
PLAN_SCHEMA = "agentic-bootstrap-plan/v1"
RESULT_SCHEMA = "agentic-bootstrap-result/v1"
PLAN_DOMAIN = b"agentic-bootstrap-plan/v1\x00"

_PROJECT_KEYS = {
    "name",
    "description",
    "build_command",
    "test_command",
    "run_command",
    "ticket_prefix",
}
_FEATURE_KEYS = {"platforms", "mcp", "agents", "github", "scheduled_audit", "hooks"}
_FORBIDDEN_FIELD_NAMES = {
    "path",
    "paths",
    "content",
    "contents",
    "patch",
    "patches",
    "mode",
    "mutable",
    "manifest",
    "credentials",
    "confirmed",
    "authorized",
    "approval",
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {', '.join(unknown)}")
    forbidden = sorted(set(data) & _FORBIDDEN_FIELD_NAMES)
    if forbidden:
        raise ValueError(f"{label} contains forbidden fields: {', '.join(forbidden)}")


def _bounded_text(
    value: Any,
    label: str,
    *,
    maximum: int,
    nullable: bool = False,
    markdown_safe: bool = False,
    command: bool = False,
) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string" + (" or null" if nullable else ""))
    if not value.strip() and not nullable:
        raise ValueError(f"{label} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{label} exceeds {maximum} characters")
    if value != unicodedata.normalize("NFC", value):
        raise ValueError(f"{label} must use NFC Unicode normalization")
    unsafe_categories = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}
    if any(unicodedata.category(char) in unsafe_categories for char in value):
        raise ValueError(f"{label} contains control, format, private-use, or line-separator characters")
    if "{{" in value or "}}" in value:
        raise ValueError(f"{label} contains template delimiters")
    if markdown_safe and any(token in value for token in ("`", "<", ">", "[", "]", "**", "#")):
        raise ValueError(f"{label} contains Markdown delimiters")
    if command and "`" in value:
        raise ValueError(f"{label} contains a Markdown command delimiter")
    return value


@dataclass(frozen=True)
class AgentIntent:
    """Untrusted LLM proposal. Values are never human confirmations."""

    project: dict[str, str | None] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    schema: str = INTENT_SCHEMA
    authority: str = "unverified-proposal"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentIntent":
        if not isinstance(data, Mapping):
            raise ValueError("agent intent root must be an object")
        _reject_unknown(data, {"schema", "authority", "project", "features"}, "agent intent")
        if data.get("schema") != INTENT_SCHEMA:
            raise ValueError(f"agent intent schema must be {INTENT_SCHEMA!r}")
        if data.get("authority", "unverified-proposal") != "unverified-proposal":
            raise ValueError("agent intent authority must be 'unverified-proposal'")
        raw_project = data.get("project", {})
        raw_features = data.get("features", {})
        if not isinstance(raw_project, Mapping) or not isinstance(raw_features, Mapping):
            raise ValueError("agent intent project and features must be objects")
        _reject_unknown(raw_project, _PROJECT_KEYS, "agent intent project")
        _reject_unknown(raw_features, _FEATURE_KEYS, "agent intent features")

        project: dict[str, str | None] = {}
        specs = {
            "name": (200, False, True, False),
            "description": (2000, True, True, False),
            "build_command": (1000, True, False, True),
            "test_command": (1000, True, False, True),
            "run_command": (1000, True, False, True),
            "ticket_prefix": (64, True, True, False),
        }
        for key, (maximum, nullable, markdown_safe, command) in specs.items():
            if key in raw_project:
                project[key] = _bounded_text(
                    raw_project[key],
                    f"agent intent project.{key}",
                    maximum=maximum,
                    nullable=nullable,
                    markdown_safe=markdown_safe,
                    command=command,
                )

        features: dict[str, Any] = {}
        if "platforms" in raw_features:
            platforms = raw_features["platforms"]
            if not isinstance(platforms, list) or not platforms or not all(isinstance(item, str) for item in platforms):
                raise ValueError("agent intent features.platforms must be a non-empty array of strings")
            if len(platforms) != len(set(platforms)):
                raise ValueError("agent intent features.platforms must not contain duplicates")
            unknown = sorted(set(platforms) - set(SUPPORTED_PLATFORMS))
            if unknown:
                raise ValueError(f"unsupported platform: {', '.join(unknown)}")
            features["platforms"] = [name for name in SUPPORTED_PLATFORMS if name in platforms]
        for key in _FEATURE_KEYS - {"platforms"}:
            if key in raw_features:
                value = raw_features[key]
                if not isinstance(value, bool):
                    raise ValueError(f"agent intent features.{key} must be a boolean")
                features[key] = value
        if features.get("scheduled_audit") and features.get("github") is False:
            raise ValueError("scheduled_audit requires github")
        return cls(project=project, features=features)

    @classmethod
    def load(cls, path: Path) -> "AgentIntent":
        maximum = 65_536
        source = path.expanduser().absolute()
        source_stat = os.lstat(source)
        if stat.S_ISLNK(source_stat.st_mode) or not stat.S_ISREG(source_stat.st_mode):
            raise ValueError("agent intent must be a real regular file")
        if source_stat.st_size > maximum:
            raise ValueError(f"agent intent exceeds {maximum} bytes")
        descriptor: int | None = None
        try:
            descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != source_stat.st_dev
                or opened.st_ino != source_stat.st_ino
                or opened.st_size != source_stat.st_size
            ):
                raise ValueError("agent intent changed while it was being read")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = None
                content = handle.read(maximum + 1)
        finally:
            if descriptor is not None:
                os.close(descriptor)
        if len(content) > maximum:
            raise ValueError(f"agent intent exceeds {maximum} bytes")
        data = json.loads(content.decode("utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "project": dict(sorted(self.project.items())),
            "features": dict(sorted(self.features.items())),
        }


def request_payload(request: BootstrapRequest) -> dict[str, Any]:
    return {
        "mode": request.mode,
        "project": {
            "name": request.facts.name,
            "description": request.facts.description,
            "languages": list(request.facts.languages),
            "components": list(request.facts.components),
            "build_command": request.facts.build_command,
            "test_command": request.facts.test_command,
            "run_command": request.facts.run_command,
            "ticket_prefix": request.facts.ticket_prefix,
        },
        "features": {
            "platforms": request.features.normalized_platforms(),
            "mcp": request.features.mcp,
            "agents": request.features.agents,
            "github": request.features.github,
            "scheduled_audit": request.features.scheduled_audit,
            "hooks": request.features.hooks,
        },
    }


def intent_defaults(intent: AgentIntent | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if intent is None:
        return {}, {}
    return dict(intent.project), dict(intent.features)


def _path_state(root: Path, relative: str) -> dict[str, Any]:
    try:
        assert_safe_root_parent(root)
        normalized = normalize_relative_path(relative)
    except UnsafePathError as exc:
        return {"state": "unsafe-path", "error": str(exc)}
    try:
        root_mode = os.lstat(root).st_mode
    except FileNotFoundError:
        return {"state": "missing"}
    if stat.S_ISLNK(root_mode):
        return {"state": "root-symlink"}
    if not stat.S_ISDIR(root_mode):
        return {"state": "root-not-directory"}
    path = root
    parts = normalized.split("/")
    for index, part in enumerate(parts):
        path = path / part
        leaf = index == len(parts) - 1
        try:
            path_stat = os.lstat(path)
            mode = path_stat.st_mode
        except FileNotFoundError:
            return {"state": "missing"}
        except OSError as exc:
            return {"state": "unreadable", "error": type(exc).__name__}
        if stat.S_ISLNK(mode):
            return {"state": "symlink" if leaf else "parent-symlink", "mode": stat.S_IMODE(mode)}
        if not leaf and not stat.S_ISDIR(mode):
            return {"state": "parent-not-directory", "mode": stat.S_IMODE(mode)}
    if stat.S_ISREG(mode):
        descriptor: int | None = None
        try:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != path_stat.st_dev
                or opened.st_ino != path_stat.st_ino
            ):
                os.close(descriptor)
                descriptor = None
                return {"state": "changed-type"}
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = None
                digest = sha256_bytes(handle.read())
        except OSError as exc:
            if descriptor is not None:
                os.close(descriptor)
            return {"state": "unreadable-regular", "mode": stat.S_IMODE(mode), "error": type(exc).__name__}
        return {"state": "regular", "sha256": digest, "mode": stat.S_IMODE(mode)}
    if stat.S_ISDIR(mode):
        return {"state": "directory", "mode": stat.S_IMODE(mode)}
    return {"state": "special", "mode": stat.S_IMODE(mode)}


def _root_state(root: Path) -> dict[str, Any]:
    try:
        assert_safe_root_parent(root)
        mode = os.lstat(root).st_mode
    except UnsafePathError as exc:
        return {"state": "unsafe-ancestor", "error": str(exc)}
    except FileNotFoundError:
        return {"state": "missing"}
    if stat.S_ISLNK(mode):
        return {"state": "symlink", "mode": stat.S_IMODE(mode)}
    if stat.S_ISDIR(mode):
        return {"state": "directory", "mode": stat.S_IMODE(mode)}
    if stat.S_ISREG(mode):
        return {"state": "regular", "mode": stat.S_IMODE(mode)}
    return {"state": "special", "mode": stat.S_IMODE(mode)}


def _resulting_ownership(plan: Plan, desired: Mapping[str, GeneratedFile], remove_obsolete: bool) -> dict[str, Any]:
    result: dict[str, Any] = {}
    by_path = {operation.path: operation for operation in plan.operations}
    for relative, generated in sorted(desired.items()):
        operation = by_path.get(relative)
        if operation is None or operation.action in {Action.CONFLICT, Action.SKIP_UNMANAGED}:
            continue
        if operation.action == Action.NO_CHANGE and operation.expected_hash:
            digest = operation.expected_hash
            executable = bool(operation.expected_executable)
        else:
            digest = sha256_bytes(generated.content)
            executable = generated.executable
        result[relative] = {
            "sha256": digest,
            "executable": executable,
            "mutable": generated.mutable,
        }
    if not remove_obsolete:
        for operation in plan.operations:
            if operation.action == Action.REMOVE_OBSOLETE and operation.path in plan.previous_manifest.files:
                result[operation.path] = dict(plan.previous_manifest.files[operation.path])
    return dict(sorted(result.items()))


def plan_document(
    request: BootstrapRequest,
    desired: Mapping[str, GeneratedFile],
    plan: Plan,
    *,
    remove_obsolete: bool,
) -> dict[str, Any]:
    root = Path(os.path.normpath(str(plan.root.expanduser().absolute())))
    desired_entries = []
    for relative, generated in sorted(desired.items()):
        normalized = normalize_relative_path(relative)
        desired_entries.append(
            {
                "path": normalized,
                "sha256": sha256_bytes(generated.content),
                "executable": generated.executable,
                "mutable": generated.mutable,
            }
        )
    operations = []
    observed: dict[str, Any] = {}
    for operation in plan.operations:
        operations.append(
            {
                "path": operation.path,
                "action": operation.action.value,
                "detail": operation.detail,
                "expected_sha256": operation.expected_hash,
                "expected_executable": operation.expected_executable,
            }
        )
        if operation.path != MANIFEST_PATH and operation.path != ".":
            observed[operation.path] = _path_state(root, operation.path)
    observed[MANIFEST_PATH] = _path_state(root, MANIFEST_PATH)
    return {
        "schema": PLAN_SCHEMA,
        "generator_version": __version__,
        "target": str(root),
        "target_root": _root_state(root),
        "request": request_payload(request),
        "desired": desired_entries,
        "observed": dict(sorted(observed.items())),
        "operations": operations,
        "resulting_ownership": _resulting_ownership(plan, desired, remove_obsolete),
        "remove_obsolete": remove_obsolete,
        "manifest_claim": {
            "present": plan.manifest_hash is not None,
            "sha256": plan.manifest_hash,
            "provenance": "repository-supplied-unauthenticated-claim" if plan.manifest_hash else "missing",
        },
    }


def plan_identifier(document: Mapping[str, Any]) -> str:
    if document.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"plan schema must be {PLAN_SCHEMA!r}")
    return hashlib.sha256(PLAN_DOMAIN + canonical_json_bytes(document)).hexdigest()


@dataclass(frozen=True)
class PlanArtifact:
    document: dict[str, Any]
    identifier: str
    schema: str = PLAN_SCHEMA
    authority: str = "deterministic-plan"

    @classmethod
    def create(cls, document: dict[str, Any]) -> "PlanArtifact":
        if document.get("schema") != PLAN_SCHEMA:
            raise ValueError(f"plan schema must be {PLAN_SCHEMA!r}")
        return cls(document=document, identifier=plan_identifier(document))

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.document,
            "plan_id": self.identifier,
            "authority": self.authority,
            "plan_id_semantics": "integrity-only-not-identity-or-authorization",
        }


@dataclass(frozen=True)
class ResultArtifact:
    target: str
    status: str
    applied: bool
    plan_id: str
    rollback_status: str = "not-needed"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    schema: str = RESULT_SCHEMA
    authority: str = "deterministic-result"

    def __post_init__(self) -> None:
        allowed = {"applied", "apply-failed", "validation-failed"}
        if self.status not in allowed:
            raise ValueError(f"unsupported result status: {self.status}")
        if self.rollback_status not in {"not-needed", "succeeded", "failed"}:
            raise ValueError(f"unsupported rollback status: {self.rollback_status}")
        if len(self.plan_id) != 64 or any(char not in "0123456789abcdef" for char in self.plan_id):
            raise ValueError("result plan_id must be a lowercase SHA-256 identifier")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "target": self.target,
            "status": self.status,
            "applied": self.applied,
            "plan_id": self.plan_id,
            "plan_id_semantics": "integrity-only-not-identity-or-authorization",
            "rollback_status": self.rollback_status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }
