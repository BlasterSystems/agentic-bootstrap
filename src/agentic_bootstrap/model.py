from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_PLATFORMS = ("claude", "codex", "pi", "opencode")


@dataclass(frozen=True)
class DetectedValue:
    value: Any
    evidence: str
    confidence: str = "high"
    confirmed: bool = False


@dataclass
class ProjectFacts:
    name: str
    description: str = ""
    languages: list[str] = field(default_factory=list)
    build_command: str | None = None
    test_command: str | None = None
    run_command: str | None = None
    ticket_prefix: str | None = None
    components: list[str] = field(default_factory=list)
    detection: dict[str, DetectedValue] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.name, str) or not self.name.strip():
            errors.append("project name must be a non-empty string")
        elif any(c in self.name for c in "\n\r\x00"):
            errors.append("project name contains control characters")
        if not isinstance(self.description, str):
            errors.append("project description must be a string")
        if self.ticket_prefix is not None:
            if not isinstance(self.ticket_prefix, str):
                errors.append("ticket prefix must be a string or null")
                prefix = ""
            else:
                prefix = self.ticket_prefix.strip()
            if not prefix or not prefix.replace("-", "").replace("_", "").isalnum():
                errors.append("ticket prefix must contain only letters, digits, '-' or '_'")
        for label, value in (
            ("build command", self.build_command),
            ("test command", self.test_command),
            ("run command", self.run_command),
        ):
            if value is not None and not isinstance(value, str):
                errors.append(f"{label} must be a string or null")
            elif value is not None and any(c in value for c in "\n\r\x00"):
                errors.append(f"{label} must be a single command line")
        return errors

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["detection"] = {key: asdict(value) for key, value in self.detection.items()}
        return data


@dataclass
class FeatureSelection:
    platforms: list[str] = field(default_factory=lambda: list(SUPPORTED_PLATFORMS))
    mcp: bool = False
    agents: bool = False
    github: bool = False
    scheduled_audit: bool = False
    hooks: bool = False

    def validate(self) -> list[str]:
        unknown = sorted(set(self.platforms) - set(SUPPORTED_PLATFORMS))
        return [f"unsupported platform: {name}" for name in unknown]

    def normalized_platforms(self) -> list[str]:
        return [name for name in SUPPORTED_PLATFORMS if name in set(self.platforms)]


@dataclass
class BootstrapRequest:
    target: Path
    mode: str
    facts: ProjectFacts
    features: FeatureSelection


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    content: bytes
    executable: bool = False
    mutable: bool = False

    @classmethod
    def text(
        cls,
        path: str,
        content: str,
        executable: bool = False,
        mutable: bool = False,
    ) -> "GeneratedFile":
        if not content.endswith("\n"):
            content += "\n"
        return cls(
            path=path,
            content=content.encode("utf-8"),
            executable=executable,
            mutable=mutable,
        )
