from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .model import DetectedValue, ProjectFacts


def _package_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
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


def _detect_ticket_prefix(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s", "-100"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    matches = re.findall(r"\b([A-Z][A-Z0-9_]{1,15})-[0-9]+\b", result.stdout)
    if not matches:
        return None
    counts: dict[str, int] = {}
    for match in matches:
        counts[match] = counts.get(match, 0) + 1
    return sorted(counts, key=lambda item: (-counts[item], item))[0]


def detect_project(root: Path) -> ProjectFacts:
    root = root.resolve()
    facts = ProjectFacts(name=root.name, description=f"Software project {root.name}")
    languages: list[str] = []
    components: list[str] = []

    package_json = root / "package.json"
    if package_json.is_file():
        manager = _package_manager(root)
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            package = {}
        scripts = package.get("scripts", {}) if isinstance(package.get("scripts", {}), dict) else {}
        is_typescript = (
            (root / "tsconfig.json").exists()
            or next(root.glob("*.ts"), None) is not None
            or next(root.glob("src/**/*.ts"), None) is not None
        )
        languages.append("TypeScript" if is_typescript else "JavaScript")
        components.append("node")
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
        facts.detection["node"] = DetectedValue(
            value=True,
            evidence="package.json",
            confirmed=False,
        )

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        languages.append("Python")
        components.append("python")
        pyproject_text = ""
        if (root / "pyproject.toml").is_file():
            try:
                pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
            except OSError:
                pass
        if "[build-system]" in pyproject_text:
            facts.build_command = facts.build_command or "python -m build"
        if (
            "[tool.pytest" in pyproject_text
            or (root / "pytest.ini").exists()
            or (root / "conftest.py").exists()
        ):
            facts.test_command = facts.test_command or "python -m pytest"
        facts.detection["python"] = DetectedValue(True, "pyproject.toml or requirements.txt")

    if (root / "go.mod").exists():
        languages.append("Go")
        components.append("go")
        facts.build_command = facts.build_command or "go build ./..."
        facts.test_command = facts.test_command or "go test ./..."
        facts.detection["go"] = DetectedValue(True, "go.mod")

    if (root / "Cargo.toml").exists():
        languages.append("Rust")
        components.append("rust")
        facts.build_command = facts.build_command or "cargo build"
        facts.test_command = facts.test_command or "cargo test"
        facts.detection["rust"] = DetectedValue(True, "Cargo.toml")

    sln = next(iter(root.glob("*.sln")), None)
    csproj = next(iter(root.glob("*.csproj")), None)
    if sln or csproj:
        languages.append("C#")
        components.append("dotnet")
        facts.build_command = facts.build_command or "dotnet build"
        facts.test_command = facts.test_command or "dotnet test"
        facts.detection["dotnet"] = DetectedValue(True, (sln or csproj).name)

    if (root / "pom.xml").exists() or (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        languages.append("Java/Kotlin")
        components.append("jvm")
        if (root / "pom.xml").exists():
            facts.build_command = facts.build_command or "mvn package"
            facts.test_command = facts.test_command or "mvn test"
        else:
            wrapper = "./gradlew" if (root / "gradlew").exists() else "gradle"
            facts.build_command = facts.build_command or f"{wrapper} build"
            facts.test_command = facts.test_command or f"{wrapper} test"
        facts.detection["jvm"] = DetectedValue(True, "pom.xml or Gradle build file")

    facts.languages = list(dict.fromkeys(languages))
    facts.components = list(dict.fromkeys(components))
    prefix = _detect_ticket_prefix(root)
    if prefix:
        facts.ticket_prefix = prefix
        facts.detection["ticket_prefix"] = DetectedValue(prefix, "dominant pattern in last 100 commit subjects", "medium")
    return facts
