from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import __version__
from .apply import ApplyError, apply_plan
from .detection import detect_project
from .model import BootstrapRequest, FeatureSelection, ProjectFacts, SUPPORTED_PLATFORMS
from .planner import build_plan
from .renderer import render_project
from .validation import validate_rendered, validate_target


def _csv_platforms(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(SUPPORTED_PLATFORMS)
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def _load_answers(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("answers file root must be an object")
    _validate_answers(data)
    return data


def _validate_answers(data: dict[str, Any]) -> None:
    project = data.get("project", {})
    features = data.get("features", {})
    if not isinstance(project, dict) or not isinstance(features, dict):
        raise ValueError("answers project and features must be objects")
    for key in ("name", "description", "build_command", "test_command", "run_command", "ticket_prefix"):
        value = project.get(key)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"answers project.{key} must be a string or null")
    for key in ("mcp", "agents", "github", "scheduled_audit", "hooks"):
        value = features.get(key)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"answers features.{key} must be a boolean")
    platforms = features.get("platforms")
    if platforms is not None and not (
        isinstance(platforms, str)
        or (isinstance(platforms, list) and all(isinstance(item, str) for item in platforms))
    ):
        raise ValueError("answers features.platforms must be a string or array of strings")


def _answer(data: dict[str, Any], section: str, key: str, default: Any = None) -> Any:
    nested = data.get(section, {})
    return nested.get(key, default) if isinstance(nested, dict) else default


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def _request_from_args(args: argparse.Namespace) -> BootstrapRequest:
    target = Path(args.target).expanduser()
    answers = _load_answers(args.answers)
    detected = detect_project(target)

    name = args.name or _answer(answers, "project", "name") or detected.name
    description = args.description or _answer(answers, "project", "description") or detected.description
    build = args.build_command or _answer(answers, "project", "build_command", detected.build_command)
    test = args.test_command or _answer(answers, "project", "test_command", detected.test_command)
    run = args.run_command or _answer(answers, "project", "run_command", detected.run_command)
    ticket = args.ticket_prefix
    if ticket is None:
        explicit_ticket = _answer(answers, "project", "ticket_prefix")
        ticket = explicit_ticket if explicit_ticket is not None else (detected.ticket_prefix if not args.yes else None)
    if isinstance(ticket, str) and ticket.lower() in {"none", "null", ""}:
        ticket = None

    platforms_value = args.platform or _answer(answers, "features", "platforms", "all")
    if isinstance(platforms_value, list):
        platforms = [str(item).lower() for item in platforms_value]
    else:
        platforms = _csv_platforms(str(platforms_value))

    if not args.yes:
        name = _prompt("Project name", name)
        description = _prompt("Project description", description)
        build = _prompt("Build command (leave empty if not configured)", build or "") or None
        test = _prompt("Test command (leave empty if not configured)", test or "") or None
        run = _prompt("Run command (leave empty if not configured)", run or "") or None
        ticket_input = _prompt("Ticket prefix (use 'none' if not configured)", ticket or "none")
        ticket = None if ticket_input.lower() in {"none", "null", ""} else ticket_input
        selected = _prompt("Platforms (comma-separated)", ",".join(platforms))
        platforms = _csv_platforms(selected)

    facts = ProjectFacts(
        name=name,
        description=description,
        languages=detected.languages,
        build_command=build,
        test_command=test,
        run_command=run,
        ticket_prefix=ticket,
        components=detected.components,
        detection=detected.detection,
    )
    scheduled_audit = args.scheduled_audit or _answer(answers, "features", "scheduled_audit", False)
    features = FeatureSelection(
        platforms=platforms,
        mcp=args.mcp or _answer(answers, "features", "mcp", False),
        agents=args.agents or _answer(answers, "features", "agents", False),
        github=args.github or scheduled_audit or _answer(answers, "features", "github", False),
        scheduled_audit=scheduled_audit,
        hooks=args.hooks or _answer(answers, "features", "hooks", False),
    )
    errors = facts.validate() + features.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return BootstrapRequest(target=target, mode=args.command, facts=facts, features=features)


def _plan_payload(plan, *, status: str, applied: bool, warnings: list[str], errors: list[str] | None = None) -> dict[str, Any]:
    return {
        "target": str(plan.root),
        "status": status,
        "applied": applied,
        "warnings": warnings,
        "errors": errors or [],
        "operations": [
            {"path": operation.path, "action": operation.action.value, "detail": operation.detail}
            for operation in plan.operations
        ],
    }


def _capability_warnings(request: BootstrapRequest) -> list[str]:
    warnings: list[str] = []
    if "pi" in request.features.platforms and request.features.mcp:
        warnings.append("Pi has no built-in MCP; no Pi MCP configuration is generated")
    if "pi" in request.features.platforms and request.features.agents:
        warnings.append("Pi has no built-in subagents; no Pi agent configuration is generated")
    return warnings


def _run_generation(args: argparse.Namespace) -> int:
    request = _request_from_args(args)
    json_mode = args.plan_format == "json"
    if json_mode and not (args.yes or args.dry_run):
        raise ValueError("--plan-format json requires --yes or --dry-run")

    desired = render_project(request)

    rendered_errors = validate_rendered(desired)
    if rendered_errors:
        if json_mode:
            print(json.dumps({"status": "invalid-render", "applied": False, "errors": rendered_errors}, indent=2))
        else:
            print("Rendered output is invalid:", file=sys.stderr)
            for error in rendered_errors:
                print(f"- {error}", file=sys.stderr)
        return 1

    plan = build_plan(
        request.target,
        desired,
        remove_obsolete=args.remove_obsolete,
    )
    warnings = _capability_warnings(request)
    if not json_mode:
        print(plan.format())
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    if plan.conflicts:
        if json_mode:
            print(json.dumps(_plan_payload(plan, status="conflict", applied=False, warnings=warnings), indent=2))
        print("Conflicts must be resolved manually; no files were changed.", file=sys.stderr)
        return 2
    if args.dry_run:
        if json_mode:
            print(json.dumps(_plan_payload(plan, status="dry-run", applied=False, warnings=warnings), indent=2))
        else:
            print("Dry run complete; no files were changed.")
        return 0
    if not args.yes:
        answer = input("Apply this plan? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled; no files were changed.")
            return 0
    try:
        apply_plan(
            plan,
            request.features.normalized_platforms(),
            remove_obsolete=args.remove_obsolete,
            validator=validate_target,
        )
    except ApplyError as exc:
        if json_mode:
            print(json.dumps(_plan_payload(plan, status="apply-failed", applied=False, warnings=warnings, errors=[str(exc)]), indent=2))
        print(str(exc), file=sys.stderr)
        return 1
    errors = validate_target(request.target)
    if errors:
        if json_mode:
            print(json.dumps(_plan_payload(plan, status="validation-failed", applied=False, warnings=warnings, errors=errors), indent=2))
        else:
            print("Validation failed without new changes:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
        return 1
    if json_mode:
        print(json.dumps(_plan_payload(plan, status="applied", applied=True, warnings=warnings), indent=2))
    else:
        print("Bootstrap applied successfully.")
        print("Post-apply validation passed.")
    return 0


def _add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", default=".")
    parser.add_argument("--platform", help="comma-separated list or 'all'")
    parser.add_argument("--name")
    parser.add_argument("--description")
    parser.add_argument("--build-command")
    parser.add_argument("--test-command")
    parser.add_argument("--run-command")
    parser.add_argument("--ticket-prefix")
    parser.add_argument("--answers", help="JSON file with project and feature answers")
    parser.add_argument("--mcp", action="store_true")
    parser.add_argument("--agents", action="store_true")
    parser.add_argument("--github", action="store_true")
    parser.add_argument("--scheduled-audit", action="store_true", help="add a weekly docs-check schedule; implies --github")
    parser.add_argument("--hooks", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--remove-obsolete", action="store_true")
    parser.add_argument("--plan-format", choices=("text", "json"), default="text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-bootstrap")
    parser.add_argument("--version", action="version", version=f"agentic-bootstrap {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "retrofit"):
        child = subparsers.add_parser(name)
        _add_generation_arguments(child)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--target", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        errors = validate_target(Path(args.target))
        if errors:
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("Validation passed.")
        return 0
    try:
        return _run_generation(args)
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
