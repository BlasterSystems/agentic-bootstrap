from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .manifest import MANIFEST_PATH, Manifest, ManifestError, sha256_path
from .model import GeneratedFile
from .paths import UnsafePathError, assert_safe_target_path

TOKEN = re.compile(rb"\{\{[A-Z0-9_]+\}\}")
VALID_ADR_STATUSES = {"Proposed", "Accepted", "Rejected", "Deprecated", "Superseded"}
ADR_FILENAME = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
ADR_REFERENCE = re.compile(r"ADR-(\d{4})")
PORTABLE_FORBIDDEN = ("mcp__", "Task tool", ".claude/", ".codex/", ".opencode/", ".pi/")
REQUIRED_ADR_SECTIONS = (
    "## Context",
    "## Decision drivers",
    "## Considered options",
    "## Decision",
    "## Consequences",
    "## Implementation and validation",
    "## Revisit triggers",
    "## References",
)


def _validate_portable_text(relative: str, content: bytes) -> list[str]:
    errors: list[str] = []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return [f"{relative}: portable content must be UTF-8 text"]
    for token in PORTABLE_FORBIDDEN:
        if token in text:
            errors.append(f"{relative} contains platform-specific token: {token}")
    if relative.startswith(".agents/skills/") and relative.endswith("/SKILL.md"):
        skill_name = relative.split("/")[-2]
        if not text.startswith("---\n") or f"\nname: {skill_name}\n" not in text:
            errors.append(f"{relative}: skill front matter name must match its directory")
    return errors


def validate_rendered(files: dict[str, GeneratedFile]) -> list[str]:
    errors: list[str] = []
    for relative, generated in files.items():
        if TOKEN.search(generated.content):
            errors.append(f"{relative}: unresolved template token")
        if relative == "AGENTS.md" or relative.startswith(".agents/skills/"):
            errors.extend(_validate_portable_text(relative, generated.content))
        if relative.endswith(".json"):
            try:
                json.loads(generated.content)
            except json.JSONDecodeError as exc:
                errors.append(f"{relative}: invalid JSON: {exc}")
        elif relative.endswith(".toml"):
            try:
                tomllib.loads(generated.content.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                errors.append(f"{relative}: invalid TOML: {exc}")
    if "AGENTS.md" not in files:
        errors.append("AGENTS.md is required")
    return errors


def _owned_paths(root: Path, errors: list[str]) -> dict[str, dict[str, object]] | None:
    manifest_path = root / MANIFEST_PATH
    if not manifest_path.exists() and not manifest_path.is_symlink():
        return None
    try:
        manifest = Manifest.load(root)
    except (ManifestError, OSError) as exc:
        errors.append(str(exc))
        return {}
    owned: dict[str, dict[str, object]] = dict(manifest.files)
    owned[MANIFEST_PATH] = {}
    return owned


def validate_target(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.expanduser().resolve()
    if not (root / "AGENTS.md").is_file() or (root / "AGENTS.md").is_symlink():
        errors.append("AGENTS.md must be a real file")

    owned = _owned_paths(root, errors)
    if owned is None:
        candidates = [path for path in root.rglob("*") if path.is_file()]
    else:
        candidates = []
        for relative, metadata in sorted(owned.items()):
            try:
                path = assert_safe_target_path(root, relative, allow_missing_leaf=False)
            except UnsafePathError as exc:
                errors.append(str(exc))
                continue
            if path.is_file():
                candidates.append(path)
                mutable = metadata.get("mutable", False)
                expected_hash = metadata.get("sha256")
                if not mutable and expected_hash and sha256_path(path) != expected_hash:
                    errors.append(f"manifest-owned file content changed: {relative}")
                expected_exec = metadata.get("executable")
                if not mutable and isinstance(expected_exec, bool) and bool(path.stat().st_mode & 0o100) != expected_exec:
                    errors.append(f"manifest-owned file mode changed: {relative}")
            else:
                errors.append(f"manifest-owned path is missing or not a file: {relative}")

    for path in candidates:
        relative_parts = path.relative_to(root).parts
        if owned is None and relative_parts and relative_parts[0] == ".pi-subagents":
            continue
        if owned is None and any(
            part in {".git", "templates", "node_modules", ".venv", "__pycache__"}
            for part in relative_parts
        ):
            continue
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_bytes()
        except OSError as exc:
            errors.append(f"{relative}: cannot read: {exc}")
            continue
        if TOKEN.search(content):
            errors.append(f"{relative}: unresolved template token")
        if relative == "AGENTS.md" or relative.startswith(".agents/skills/"):
            errors.extend(_validate_portable_text(relative, content))
        if path.suffix == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                errors.append(f"{relative}: invalid JSON: {exc}")
        elif path.suffix == ".toml":
            try:
                tomllib.loads(content.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                errors.append(f"{relative}: invalid TOML: {exc}")

    errors.extend(_validate_adrs(root))
    return errors


def _field(text: str, name: str) -> str | None:
    match = re.search(rf"^- \*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _parse_index(index: str) -> tuple[dict[str, tuple[str, str | None]], list[str]]:
    rows: dict[str, tuple[str, str | None]] = {}
    errors: list[str] = []
    for line in index.splitlines():
        if not line.lstrip().startswith("|") or "ADR-" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = ADR_REFERENCE.search(cells[0])
        if not match:
            continue
        adr_id = match.group(1)
        status = cells[1]
        link_match = re.search(r"\(([^)]+\.md)\)", cells[0])
        link = link_match.group(1) if link_match else None
        if adr_id in rows:
            errors.append(f"ADR index contains duplicate ADR-{adr_id}")
        rows[adr_id] = (status, link)
    return rows, errors


def _references(value: str | None) -> set[str]:
    if value in {None, "None", "—", "-"}:
        return set()
    return set(ADR_REFERENCE.findall(value or ""))


def _validate_adrs(root: Path) -> list[str]:
    errors: list[str] = []
    adr_dir = root / "docs/adr"
    index_path = adr_dir / "README.md"
    if not index_path.is_file():
        return ["docs/adr/README.md is required"]
    index_rows, index_errors = _parse_index(index_path.read_text(encoding="utf-8"))
    errors.extend(index_errors)

    records: dict[str, tuple[Path, str, str, set[str], set[str]]] = {}
    for path in sorted(adr_dir.glob("*.md")):
        if path.name in {"README.md", "template.md"}:
            continue
        match = ADR_FILENAME.match(path.name)
        if not match:
            errors.append(f"{path.relative_to(root)}: expected NNNN-short-title.md")
            continue
        adr_id = match.group(1)
        if adr_id in records:
            errors.append(f"duplicate ADR id: {adr_id}")
            continue
        text = path.read_text(encoding="utf-8")
        status = _field(text, "Status") or ""
        supersedes = _references(_field(text, "Supersedes"))
        superseded_by = _references(_field(text, "Superseded by"))
        records[adr_id] = (path, text, status, supersedes, superseded_by)
        if not text.startswith(f"# ADR-{adr_id}:"):
            errors.append(f"{path.relative_to(root)}: heading ID does not match filename")
        if status not in VALID_ADR_STATUSES:
            errors.append(f"{path.relative_to(root)}: invalid or missing Status")
        for section in REQUIRED_ADR_SECTIONS:
            if section not in text:
                errors.append(f"{path.relative_to(root)}: missing {section}")

    for adr_id, (path, _text, status, supersedes, superseded_by) in records.items():
        index_row = index_rows.get(adr_id)
        if not index_row:
            errors.append(f"{path.relative_to(root)}: missing from ADR index")
        else:
            index_status, link = index_row
            if index_status != status:
                errors.append(f"ADR-{adr_id}: index status {index_status!r} does not match file status {status!r}")
            if link and link != path.name:
                errors.append(f"ADR-{adr_id}: index link {link!r} does not match {path.name!r}")
        for reference in supersedes | superseded_by:
            if reference not in records:
                errors.append(f"ADR-{adr_id}: references missing ADR-{reference}")
        if status == "Superseded" and not superseded_by:
            errors.append(f"{path.relative_to(root)}: missing Superseded by link")
        if superseded_by and status != "Superseded":
            errors.append(f"ADR-{adr_id}: Superseded by requires status Superseded")
        for replacement in superseded_by:
            replacement_record = records.get(replacement)
            if replacement_record is None:
                continue
            replacement_status = replacement_record[2]
            if replacement_status != "Accepted":
                errors.append(f"ADR-{adr_id}: replacement ADR-{replacement} must be Accepted")
            if adr_id not in replacement_record[3]:
                errors.append(f"ADR-{adr_id}: replacement ADR-{replacement} does not reciprocally supersede it")
        if status == "Accepted":
            for previous in supersedes:
                previous_record = records.get(previous)
                if previous_record is None:
                    continue
                previous_status = previous_record[2]
                if previous_status != "Superseded":
                    errors.append(f"ADR-{adr_id}: superseded ADR-{previous} must have status Superseded")
                if adr_id not in previous_record[4]:
                    errors.append(f"ADR-{adr_id}: superseded ADR-{previous} does not link back")

    for adr_id, (_status, link) in index_rows.items():
        if adr_id not in records:
            errors.append(f"ADR index references missing ADR-{adr_id}")
        elif link and not (adr_dir / link).is_file():
            errors.append(f"ADR-{adr_id}: index link target does not exist: {link}")
    return errors
