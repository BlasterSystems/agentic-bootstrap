from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .paths import UnsafePathError, normalize_relative_path

MANIFEST_PATH = ".agentic/manifest.json"
MANIFEST_SCHEMA = "agentic-bootstrap-manifest/v1"


class ManifestError(ValueError):
    pass


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


@dataclass
class Manifest:
    generator_version: str = __version__
    platforms: list[str] = field(default_factory=list)
    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    updated_at: str = ""
    schema: str = MANIFEST_SCHEMA

    @classmethod
    def load(cls, root: Path) -> "Manifest":
        path = root / MANIFEST_PATH
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"invalid ownership manifest: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema") != MANIFEST_SCHEMA:
            raise ManifestError("existing .agentic/manifest.json is not an owned v1 manifest")
        raw_files = data.get("files")
        if not isinstance(raw_files, dict):
            raise ManifestError("manifest files must be an object")
        files: dict[str, dict[str, Any]] = {}
        for relative, metadata in raw_files.items():
            try:
                normalized = normalize_relative_path(relative)
            except UnsafePathError as exc:
                raise ManifestError(str(exc)) from exc
            if normalized == MANIFEST_PATH:
                raise ManifestError("manifest must not claim ownership of itself")
            if not isinstance(metadata, dict):
                raise ManifestError(f"manifest metadata must be an object: {relative}")
            digest = metadata.get("sha256")
            executable = metadata.get("executable")
            mutable = metadata.get("mutable", False)
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or not isinstance(executable, bool)
                or not isinstance(mutable, bool)
            ):
                raise ManifestError(f"invalid manifest metadata: {relative}")
            files[normalized] = {
                "sha256": digest,
                "executable": executable,
                "mutable": mutable,
            }
        platforms = data.get("platforms", [])
        if not isinstance(platforms, list) or not all(isinstance(item, str) for item in platforms):
            raise ManifestError("manifest platforms must be an array of strings")
        return cls(
            generator_version=str(data.get("generator_version", "unknown")),
            platforms=platforms,
            files=files,
            updated_at=str(data.get("updated_at", "")),
            schema=MANIFEST_SCHEMA,
        )

    def to_bytes(self) -> bytes:
        self.updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        data = {
            "schema": MANIFEST_SCHEMA,
            "generator_version": self.generator_version,
            "platforms": self.platforms,
            "updated_at": self.updated_at,
            "files": dict(sorted(self.files.items())),
        }
        return (json.dumps(data, indent=2, sort_keys=False) + "\n").encode("utf-8")
