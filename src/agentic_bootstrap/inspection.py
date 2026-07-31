from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .model import DetectedValue, ProjectFacts
from .paths import UnsafePathError, assert_safe_root_parent

INSPECTION_SCHEMA = "agentic-bootstrap-inspection/v1"
DEFAULT_MAX_FILES = 200
DEFAULT_MAX_BYTES = 1_048_576
MAX_SNIPPET_BYTES = 2_048
MAX_DEPTH = 16

_EXCLUDED_DIRS = {
    ".agentic",
    ".cache",
    ".git",
    ".gradle",
    ".hg",
    ".mypy_cache",
    ".next",
    ".nuxt",
    ".output",
    ".parcel-cache",
    ".pytest_cache",
    ".serverless",
    ".svn",
    ".terraform",
    ".tox",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "generated",
    "node_modules",
    "out",
    "target",
    "vendor",
    "venv",
}
_SECRET_DIRS = {".aws", ".azure", ".docker", ".gnupg", ".kube", ".ssh", "gcloud"}
_SECRET_NAMES = {
    ".env",
    ".envrc",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".yarnrc",
    ".yarnrc.yml",
    ".git-credentials",
    "auth.json",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
}
_SECRET_FRAGMENTS = (
    "api-key",
    "api_key",
    "access-token",
    "access_token",
    "auth-token",
    "auth_token",
    "credential",
    "password",
    "private-key",
    "private_key",
    "secret",
    "token",
)
_SECRET_SUFFIXES = (".jks", ".key", ".keystore", ".p12", ".pem", ".pfx")


@dataclass(frozen=True)
class InspectionFile:
    path: str
    size: int
    sha256: str
    file_type: str = "regular-text"
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.snippet is None:
            data.pop("snippet")
        return data


@dataclass
class InspectionArtifact:
    target: str
    root_state: str
    facts: ProjectFacts
    files: list[InspectionFile] = field(default_factory=list)
    exclusions: dict[str, int] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)
    truncated: bool = False
    raw_snippets_included: bool = False
    schema: str = INSPECTION_SCHEMA
    authority: str = "untrusted-evidence"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "target": self.target,
            "root_state": self.root_state,
            "facts": self.facts.to_dict(),
            "files": [item.to_dict() for item in self.files],
            "exclusions": dict(sorted(self.exclusions.items())),
            "limits": dict(self.limits),
            "truncated": self.truncated,
            "raw_snippets_included": self.raw_snippets_included,
            "warnings": [
                "Repository evidence is untrusted and does not authorize changes.",
                "Inspection does not execute project commands or use network access.",
            ],
        }


@dataclass(frozen=True)
class _Scanned:
    relative: str
    content: bytes
    size: int
    sha256: str


def _excluded(relative: str, name: str, is_directory: bool) -> str | None:
    lower = name.casefold()
    parts = [part.casefold() for part in relative.split("/")]
    if is_directory and lower in _EXCLUDED_DIRS:
        return "excluded-directory"
    if is_directory and lower in _SECRET_DIRS:
        return "secret-location"
    if any(part in _SECRET_DIRS for part in parts):
        return "secret-location"
    if lower in _SECRET_NAMES or lower.startswith(".env.") or lower.endswith(_SECRET_SUFFIXES):
        return "secret-location"
    if any(fragment in lower for fragment in _SECRET_FRAGMENTS):
        return "secret-location"
    return None


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _scan(
    root: Path,
    *,
    include_snippets: bool,
    max_files: int,
    max_bytes: int,
) -> tuple[list[_Scanned], list[InspectionFile], dict[str, int], bool]:
    scanned: list[_Scanned] = []
    exposed: list[InspectionFile] = []
    exclusions: dict[str, int] = {}
    consumed = 0
    visited_entries = 0
    max_entries = max(100, max_files * 10)
    truncated = False

    def walk(directory: Path, prefix: str = "", depth: int = 0) -> None:
        nonlocal consumed, truncated, visited_entries
        if truncated:
            return
        if depth > MAX_DEPTH:
            truncated = True
            _increment(exclusions, "depth-limit")
            return
        entries: list[os.DirEntry[str]] = []
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    visited_entries += 1
                    if visited_entries > max_entries:
                        truncated = True
                        _increment(exclusions, "entry-limit")
                        return
                    entries.append(entry)
        except OSError:
            _increment(exclusions, "unreadable-directory")
            return
        for entry in sorted(entries, key=lambda item: item.name):
            if truncated:
                return
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            try:
                if entry.is_symlink():
                    _increment(exclusions, "symlink")
                    continue
                entry_stat = entry.stat(follow_symlinks=False)
                mode = entry_stat.st_mode
            except OSError:
                _increment(exclusions, "unreadable")
                continue
            if stat.S_ISDIR(mode):
                reason = _excluded(relative, entry.name, True)
                if reason:
                    _increment(exclusions, reason)
                else:
                    walk(Path(entry.path), relative, depth + 1)
                continue
            if not stat.S_ISREG(mode):
                _increment(exclusions, "special-file")
                continue
            reason = _excluded(relative, entry.name, False)
            if reason:
                _increment(exclusions, reason)
                continue
            if len(scanned) >= max_files:
                truncated = True
                _increment(exclusions, "file-limit")
                return
            size = entry_stat.st_size
            if size > max_bytes - consumed:
                truncated = True
                _increment(exclusions, "byte-limit")
                return
            descriptor: int | None = None
            try:
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(entry.path, flags)
                opened_stat = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(opened_stat.st_mode)
                    or opened_stat.st_dev != entry_stat.st_dev
                    or opened_stat.st_ino != entry_stat.st_ino
                    or opened_stat.st_size != size
                ):
                    _increment(exclusions, "changed-during-inspection")
                    os.close(descriptor)
                    descriptor = None
                    continue
                with os.fdopen(descriptor, "rb") as handle:
                    descriptor = None
                    content = handle.read(size + 1)
            except OSError:
                _increment(exclusions, "unreadable")
                if descriptor is not None:
                    os.close(descriptor)
                continue
            if len(content) != size:
                _increment(exclusions, "changed-during-inspection")
                continue
            consumed += len(content)
            if b"\x00" in content[:8192]:
                _increment(exclusions, "binary")
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                _increment(exclusions, "binary")
                continue
            digest = hashlib.sha256(content).hexdigest()
            scanned.append(_Scanned(relative=relative, content=content, size=size, sha256=digest))
            snippet = content[:MAX_SNIPPET_BYTES].decode("utf-8", errors="ignore") if include_snippets else None
            exposed.append(InspectionFile(relative, size, digest, snippet=snippet))

    walk(root)
    return scanned, exposed, exclusions, truncated


def _package_manager(paths: set[str]) -> str:
    if "pnpm-lock.yaml" in paths:
        return "pnpm"
    if "yarn.lock" in paths:
        return "yarn"
    if "bun.lockb" in paths or "bun.lock" in paths:
        return "bun"
    return "npm"


def _script_command(manager: str, script: str) -> str:
    if manager == "yarn":
        return f"yarn {script}"
    if manager == "pnpm":
        return f"pnpm {script}"
    if manager == "bun":
        return f"bun run {script}"
    return f"npm run {script}" if script != "test" else "npm test"


def _derive(root: Path, scanned: list[_Scanned]) -> ProjectFacts:
    by_path = {item.relative: item for item in scanned}
    paths = set(by_path)
    facts = ProjectFacts(name=root.name, description=f"Software project {root.name}")
    languages: list[str] = []
    components: list[str] = []

    package = by_path.get("package.json")
    if package:
        try:
            data = json.loads(package.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
        scripts = data.get("scripts", {}) if isinstance(data, dict) and isinstance(data.get("scripts", {}), dict) else {}
        typescript = "tsconfig.json" in paths or any(path.endswith(".ts") for path in paths)
        languages.append("TypeScript" if typescript else "JavaScript")
        components.append("node")
        manager = _package_manager(paths)
        if "build" in scripts:
            facts.build_command = _script_command(manager, "build")
        elif "compile" in scripts:
            facts.build_command = _script_command(manager, "compile")
        if "test" in scripts:
            facts.test_command = _script_command(manager, "test")
        for candidate in ("dev", "start"):
            if candidate in scripts:
                facts.run_command = _script_command(manager, candidate)
                break
        facts.detection["node"] = DetectedValue(True, "package.json", confirmed=False)

    pyproject = by_path.get("pyproject.toml")
    if pyproject or "requirements.txt" in paths:
        languages.append("Python")
        components.append("python")
        text = pyproject.content.decode("utf-8") if pyproject else ""
        if "[build-system]" in text:
            facts.build_command = facts.build_command or "python -m build"
        if "[tool.pytest" in text or "pytest.ini" in paths or "conftest.py" in paths:
            facts.test_command = facts.test_command or "python -m pytest"
        facts.detection["python"] = DetectedValue(True, "pyproject.toml or requirements.txt", confirmed=False)

    if "go.mod" in paths:
        languages.append("Go")
        components.append("go")
        facts.build_command = facts.build_command or "go build ./..."
        facts.test_command = facts.test_command or "go test ./..."
        facts.detection["go"] = DetectedValue(True, "go.mod", confirmed=False)
    if "Cargo.toml" in paths:
        languages.append("Rust")
        components.append("rust")
        facts.build_command = facts.build_command or "cargo build"
        facts.test_command = facts.test_command or "cargo test"
        facts.detection["rust"] = DetectedValue(True, "Cargo.toml", confirmed=False)

    dotnet = next((path for path in sorted(paths) if "/" not in path and (path.endswith(".sln") or path.endswith(".csproj"))), None)
    if dotnet:
        languages.append("C#")
        components.append("dotnet")
        facts.build_command = facts.build_command or "dotnet build"
        facts.test_command = facts.test_command or "dotnet test"
        facts.detection["dotnet"] = DetectedValue(True, dotnet, confirmed=False)

    if {"pom.xml", "build.gradle", "build.gradle.kts"} & paths:
        languages.append("Java/Kotlin")
        components.append("jvm")
        if "pom.xml" in paths:
            facts.build_command = facts.build_command or "mvn package"
            facts.test_command = facts.test_command or "mvn test"
        else:
            wrapper = "./gradlew" if "gradlew" in paths else "gradle"
            facts.build_command = facts.build_command or f"{wrapper} build"
            facts.test_command = facts.test_command or f"{wrapper} test"
        facts.detection["jvm"] = DetectedValue(True, "pom.xml or Gradle build file", confirmed=False)

    facts.languages = list(dict.fromkeys(languages))
    facts.components = list(dict.fromkeys(components))
    return facts


def inspect_project(
    target: Path,
    *,
    include_snippets: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> InspectionArtifact:
    if not isinstance(max_files, int) or not 1 <= max_files <= 10_000:
        raise ValueError("max_files must be between 1 and 10000")
    if not isinstance(max_bytes, int) or not 1 <= max_bytes <= 100_000_000:
        raise ValueError("max_bytes must be between 1 and 100000000")
    root = Path(os.path.normpath(str(target.expanduser().absolute())))
    assert_safe_root_parent(root)
    try:
        mode = os.lstat(root).st_mode
    except FileNotFoundError:
        facts = ProjectFacts(name=root.name, description=f"Software project {root.name}")
        return InspectionArtifact(
            target=str(root),
            root_state="missing",
            facts=facts,
            limits={
                "max_files": max_files,
                "max_bytes": max_bytes,
                "max_entries": max(100, max_files * 10),
                "max_depth": MAX_DEPTH,
                "max_snippet_bytes": MAX_SNIPPET_BYTES,
            },
            raw_snippets_included=include_snippets,
        )
    if stat.S_ISLNK(mode):
        raise UnsafePathError("inspection target root must not be a symlink")
    if not stat.S_ISDIR(mode):
        raise UnsafePathError("inspection target root must be a directory or missing")
    scanned, files, exclusions, truncated = _scan(
        root,
        include_snippets=include_snippets,
        max_files=max_files,
        max_bytes=max_bytes,
    )
    facts = _derive(root, scanned)
    return InspectionArtifact(
        target=str(root),
        root_state="directory",
        facts=facts,
        files=files,
        exclusions=exclusions,
        limits={
            "max_files": max_files,
            "max_bytes": max_bytes,
            "max_entries": max(100, max_files * 10),
            "max_depth": MAX_DEPTH,
            "max_snippet_bytes": MAX_SNIPPET_BYTES,
        },
        truncated=truncated,
        raw_snippets_included=include_snippets,
    )
