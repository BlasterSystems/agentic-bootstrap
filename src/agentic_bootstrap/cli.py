from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

from . import __version__
from .detection import detect_project
from .facade import PreparedBootstrap, apply_bootstrap, inspect_project, prepare_bootstrap
from .inspection import DEFAULT_MAX_BYTES, DEFAULT_MAX_FILES
from .model import BootstrapRequest, FeatureSelection, ProjectFacts, SUPPORTED_PLATFORMS
from .protocol import INTENT_SCHEMA, AgentIntent, ResultArtifact, intent_defaults
from .validation import validate_target


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


def _terminal_safe_text(value: str) -> str:
    """Escape terminal controls while preserving ordinary text and line layout."""
    rendered: list[str] = []
    unsafe_categories = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}
    for char in value:
        if char == "\n":
            rendered.append(char)
        elif unicodedata.category(char) in unsafe_categories:
            codepoint = ord(char)
            rendered.append(f"\\u{codepoint:04x}" if codepoint <= 0xFFFF else f"\\U{codepoint:08x}")
        else:
            rendered.append(char)
    return "".join(rendered)


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{_terminal_safe_text(default)}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def _prompt_bool(label: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{label}? [{suffix}]: ").strip().lower()
    if not value:
        return default
    if value in {"y", "yes"}:
        return True
    if value in {"n", "no"}:
        return False
    raise ValueError(f"{label} requires yes or no")


def _request_from_args(args: argparse.Namespace) -> BootstrapRequest:
    target = Path(args.target).expanduser()
    answers = _load_answers(args.answers)
    intent = AgentIntent.load(Path(args.agent_intent)) if args.agent_intent else None
    proposed_project, proposed_features = intent_defaults(intent)
    detected = inspect_project(target).facts if args.agent_guided else detect_project(target)

    def project_value(cli_value: Any, key: str, detected_value: Any) -> Any:
        if cli_value is not None:
            return cli_value
        if key in proposed_project:
            return proposed_project[key]
        return _answer(answers, "project", key, detected_value)

    name = project_value(args.name, "name", detected.name)
    description = project_value(args.description, "description", detected.description) or ""
    build = project_value(args.build_command, "build_command", detected.build_command)
    test = project_value(args.test_command, "test_command", detected.test_command)
    run = project_value(args.run_command, "run_command", detected.run_command)
    ticket = args.ticket_prefix
    if ticket is None:
        if "ticket_prefix" in proposed_project:
            ticket = proposed_project["ticket_prefix"]
        else:
            explicit_ticket = _answer(answers, "project", "ticket_prefix")
            ticket = explicit_ticket if explicit_ticket is not None else (detected.ticket_prefix if not args.yes else None)
    if isinstance(ticket, str) and ticket.lower() in {"none", "null", ""}:
        ticket = None

    platforms_value = args.platform or proposed_features.get("platforms") or _answer(
        answers, "features", "platforms", "all"
    )
    if isinstance(platforms_value, list):
        platforms = [str(item).lower() for item in platforms_value]
    else:
        platforms = _csv_platforms(str(platforms_value))

    scheduled_audit = bool(
        args.scheduled_audit
        or proposed_features.get("scheduled_audit", False)
        or _answer(answers, "features", "scheduled_audit", False)
    )
    proposed_selection = {
        "mcp": bool(args.mcp or proposed_features.get("mcp", False) or _answer(answers, "features", "mcp", False)),
        "agents": bool(args.agents or proposed_features.get("agents", False) or _answer(answers, "features", "agents", False)),
        "github": bool(
            args.github
            or scheduled_audit
            or proposed_features.get("github", False)
            or _answer(answers, "features", "github", False)
        ),
        "scheduled_audit": scheduled_audit,
        "hooks": bool(args.hooks or proposed_features.get("hooks", False) or _answer(answers, "features", "hooks", False)),
    }

    agent_preview = args.agent_guided and args.dry_run
    if not args.yes and not agent_preview:
        name = _prompt("Project name", name)
        description = _prompt("Project description", description)
        build = _prompt("Build command (leave empty if not configured)", build or "") or None
        test = _prompt("Test command (leave empty if not configured)", test or "") or None
        run = _prompt("Run command (leave empty if not configured)", run or "") or None
        ticket_input = _prompt("Ticket prefix (use 'none' if not configured)", ticket or "none")
        ticket = None if ticket_input.lower() in {"none", "null", ""} else ticket_input
        selected = _prompt("Platforms (comma-separated)", ",".join(platforms))
        platforms = _csv_platforms(selected)
        if args.agent_guided:
            proposed_selection = {
                "mcp": _prompt_bool("Enable MCP configuration", proposed_selection["mcp"]),
                "agents": _prompt_bool("Enable specialized agents", proposed_selection["agents"]),
                "github": _prompt_bool("Enable GitHub workflow", proposed_selection["github"]),
                "scheduled_audit": _prompt_bool(
                    "Enable scheduled documentation audit", proposed_selection["scheduled_audit"]
                ),
                "hooks": _prompt_bool("Enable Git hooks", proposed_selection["hooks"]),
            }
            if proposed_selection["scheduled_audit"]:
                proposed_selection["github"] = True
            if args.remove_obsolete:
                args.remove_obsolete = _prompt_bool("Allow removal of unchanged obsolete owned files", True)

    if args.agent_guided:
        AgentIntent.from_dict(
            {
                "schema": INTENT_SCHEMA,
                "project": {
                    "name": name,
                    "description": description,
                    "build_command": build,
                    "test_command": test,
                    "run_command": run,
                    "ticket_prefix": ticket,
                },
                "features": {"platforms": platforms, **proposed_selection},
            }
        )

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
    features = FeatureSelection(platforms=platforms, **proposed_selection)
    errors = facts.validate() + features.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return BootstrapRequest(target=target, mode=args.command, facts=facts, features=features)


def _legacy_plan_payload(
    prepared: PreparedBootstrap,
    *,
    status: str,
    applied: bool,
    warnings: list[str],
    errors: list[str] | None = None,
    rollback_status: str = "not-needed",
) -> dict[str, Any]:
    return {
        "target": str(prepared.plan.root),
        "status": status,
        "applied": applied,
        "warnings": warnings,
        "errors": errors or [],
        "rollback_status": rollback_status,
        "operations": [
            {"path": operation.path, "action": operation.action.value, "detail": operation.detail}
            for operation in prepared.plan.operations
        ],
    }


def _payload(
    prepared: PreparedBootstrap,
    args: argparse.Namespace,
    *,
    status: str,
    applied: bool,
    warnings: list[str],
    errors: list[str] | None = None,
    rollback_status: str = "not-needed",
) -> dict[str, Any]:
    if args.agent_guided:
        payload = prepared.payload(
            status=status,
            applied=applied,
            warnings=warnings,
            errors=errors,
            rollback_status=rollback_status,
        )
        payload["authority"] = "untrusted-preview" if args.dry_run else "trusted-terminal-recomputed"
        payload["human_handoff_required"] = args.dry_run
        return payload
    return _legacy_plan_payload(
        prepared,
        status=status,
        applied=applied,
        warnings=warnings,
        errors=errors,
        rollback_status=rollback_status,
    )


def _capability_warnings(request: BootstrapRequest) -> list[str]:
    warnings: list[str] = []
    if "pi" in request.features.platforms and request.features.mcp:
        warnings.append("Pi has no built-in MCP; no Pi MCP configuration is generated")
    if "pi" in request.features.platforms and request.features.agents:
        warnings.append("Pi has no built-in subagents; no Pi agent configuration is generated")
    return warnings


def _display_agent_review(prepared: PreparedBootstrap, warnings: list[str]) -> None:
    print("Agent-guided plan recomputed by the deterministic core.")
    print("Plan identifier provides integrity only; it does not identify or authorize an approver.")
    print("Complete canonical plan bound by the plan identifier:")
    print(json.dumps(prepared.artifact.to_dict(), indent=2, ensure_ascii=True, sort_keys=True))
    claim = prepared.document["manifest_claim"]
    if claim["present"]:
        print("WARNING: The existing manifest is a repository-supplied, unauthenticated ownership claim.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    diffs = prepared.review_diffs(include_existing_content=True)
    if diffs:
        print("Reviewable generated-file diffs:")
        for path, diff in sorted(diffs.items()):
            print(f"--- {_terminal_safe_text(path)} ---")
            safe_diff = _terminal_safe_text(diff)
            print(safe_diff, end="" if safe_diff.endswith("\n") else "\n")


def _validate_agent_arguments(args: argparse.Namespace) -> None:
    if args.agent_intent and not args.agent_guided:
        raise ValueError("--agent-intent requires --agent-guided")
    if args.expected_plan is not None and not args.agent_guided:
        raise ValueError("--expected-plan requires --agent-guided")
    if args.expected_plan is not None and (
        len(args.expected_plan) != 64 or any(char not in "0123456789abcdef" for char in args.expected_plan)
    ):
        raise ValueError("--expected-plan must be a lowercase 64-character SHA-256 identifier")
    if args.agent_guided and args.yes:
        raise ValueError("--yes is not allowed in agent-guided mode")
    if args.agent_guided and not args.dry_run:
        if args.plan_format == "json":
            raise ValueError("agent-guided apply requires trusted-terminal text display; JSON is preview-only")
        if args.expected_plan is None:
            raise ValueError("agent-guided apply requires --expected-plan from a reviewed dry-run")
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError("agent-guided apply requires an interactive trusted terminal")
    if args.expected_plan is not None and args.dry_run:
        raise ValueError("--expected-plan is only valid for agent-guided apply")
    if args.agent_intent and args.answers:
        raise ValueError("--agent-intent and --answers cannot be combined")


def _run_generation(args: argparse.Namespace) -> int:
    _validate_agent_arguments(args)
    request = _request_from_args(args)
    json_mode = args.plan_format == "json"
    if json_mode and not (args.yes or args.dry_run or args.agent_guided):
        raise ValueError("--plan-format json requires --yes, --dry-run, or --agent-guided")

    prepared = prepare_bootstrap(request, remove_obsolete=args.remove_obsolete)
    plan = prepared.plan
    warnings = _capability_warnings(request)

    if args.agent_guided and args.expected_plan and prepared.plan_id != args.expected_plan:
        raise ValueError(
            f"plan identifier mismatch: expected {args.expected_plan}, recomputed {prepared.plan_id}; review a new dry-run"
        )

    if not json_mode:
        if args.agent_guided:
            _display_agent_review(prepared, warnings)
        else:
            print(_terminal_safe_text(plan.format()))
            for warning in warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
    if plan.conflicts:
        if json_mode:
            print(json.dumps(_payload(prepared, args, status="conflict", applied=False, warnings=warnings), indent=2))
        print("Conflicts must be resolved manually; no files were changed.", file=sys.stderr)
        return 2
    if args.dry_run:
        if json_mode:
            print(json.dumps(_payload(prepared, args, status="dry-run", applied=False, warnings=warnings), indent=2))
        else:
            if args.agent_guided:
                print("Human handoff required: run the same command interactively with --expected-plan and this plan ID.")
            print("Dry run complete; no files were changed.")
        return 0

    if args.agent_guided:
        answer = input(f"Apply the complete recomputed plan {prepared.plan_id}? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled; no files were changed.")
            return 0
    elif not args.yes:
        answer = input("Apply this plan? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled; no files were changed.")
            return 0
    result = apply_bootstrap(prepared, expected_plan_id=prepared.plan_id)
    if not result.applied:
        if json_mode:
            print(
                json.dumps(
                    _payload(
                        prepared,
                        args,
                        status=result.status,
                        applied=False,
                        warnings=warnings,
                        errors=list(result.errors),
                        rollback_status=result.rollback_status,
                    ),
                    indent=2,
                )
            )
        if args.agent_guided:
            print("Deterministic result:")
            print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
        for error in result.errors:
            print(_terminal_safe_text(error), file=sys.stderr)
        return 1
    try:
        errors = validate_target(request.target)
    except Exception as exc:
        validation_result = ResultArtifact(
            target=str(request.target.expanduser().absolute()),
            status="validation-failed",
            applied=True,
            plan_id=prepared.plan_id,
            rollback_status=result.rollback_status,
            warnings=tuple(warnings),
            errors=(str(exc),),
        )
        if args.agent_guided:
            print("Deterministic result:")
            print(json.dumps(validation_result.to_dict(), ensure_ascii=True, sort_keys=True))
        print(f"error: {_terminal_safe_text(str(exc))}", file=sys.stderr)
        return 1
    if errors:
        validation_result = ResultArtifact(
            target=str(request.target.expanduser().absolute()),
            status="validation-failed",
            applied=True,
            plan_id=prepared.plan_id,
            rollback_status="not-needed",
            warnings=tuple(warnings),
            errors=tuple(errors),
        )
        if json_mode:
            print(
                json.dumps(
                    _payload(
                        prepared,
                        args,
                        status="validation-failed",
                        applied=True,
                        warnings=warnings,
                        errors=errors,
                    ),
                    indent=2,
                )
            )
        else:
            if args.agent_guided:
                print("Deterministic result:")
                print(json.dumps(validation_result.to_dict(), ensure_ascii=True, sort_keys=True))
            print("Validation failed after apply:", file=sys.stderr)
            for error in errors:
                print(f"- {_terminal_safe_text(error)}", file=sys.stderr)
        return 1
    if json_mode:
        print(json.dumps(_payload(prepared, args, status="applied", applied=True, warnings=warnings), indent=2))
    else:
        print("Bootstrap applied successfully.")
        print("Post-apply validation passed.")
        if args.agent_guided:
            print("Deterministic result:")
            print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0


def _run_inspect(args: argparse.Namespace) -> int:
    artifact = inspect_project(
        Path(args.target),
        include_snippets=args.include_snippets,
        max_files=args.max_files,
        max_bytes=args.max_bytes,
    )
    print(json.dumps(artifact.to_dict(), indent=2, ensure_ascii=True))
    return 0


def _add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", default=".", help="project directory to inspect or generate")
    parser.add_argument("--platform", help="comma-separated platforms or 'all'")
    parser.add_argument("--name", help="project name; defaults to detected directory metadata")
    parser.add_argument("--description", help="short project description")
    parser.add_argument("--build-command", help="authoritative project build command")
    parser.add_argument("--test-command", help="authoritative project test command")
    parser.add_argument("--run-command", help="authoritative project run command")
    parser.add_argument("--ticket-prefix", help="issue prefix, or 'none' when not configured")
    parser.add_argument(
        "--answers",
        metavar="FILE",
        help="load confirmed project and feature answers from JSON; see docs/ANSWERS.md",
    )
    parser.add_argument(
        "--agent-guided",
        action="store_true",
        help="use the LLM-advisory protocol; dry-run previews require a separate interactive human apply",
    )
    parser.add_argument(
        "--agent-intent",
        metavar="FILE",
        help="load an unverified schema-versioned agent proposal; requires --agent-guided",
    )
    parser.add_argument(
        "--expected-plan",
        metavar="SHA256",
        help="integrity-only plan identifier from a reviewed agent-guided dry-run",
    )
    parser.add_argument("--mcp", action="store_true", help="generate native MCP configuration where supported")
    parser.add_argument("--agents", action="store_true", help="generate specialized-agent definitions where supported")
    parser.add_argument("--github", action="store_true", help="generate the GitHub documentation-check workflow")
    parser.add_argument(
        "--scheduled-audit",
        action="store_true",
        help="add a weekly docs-check schedule; implies --github",
    )
    parser.add_argument("--hooks", action="store_true", help="generate opt-in Git hook files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan without creating the target or changing files",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="accept detected/default answers and apply without prompting in direct trusted-caller mode",
    )
    parser.add_argument(
        "--remove-obsolete",
        action="store_true",
        help="remove unchanged obsolete files previously owned by the manifest",
    )
    parser.add_argument(
        "--plan-format",
        choices=("text", "json"),
        default="text",
        help="render a human-readable or machine-readable plan",
    )


def build_parser() -> argparse.ArgumentParser:
    formatter = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(
        prog="agentic-bootstrap",
        description="Generate and validate provider-neutral coding-agent project instructions.",
        formatter_class=formatter,
    )
    parser.add_argument("--version", action="version", version=f"agentic-bootstrap {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser(
        "init",
        help="initialize a greenfield project",
        description="Plan or initialize a greenfield project.",
        formatter_class=formatter,
    )
    _add_generation_arguments(init)
    retrofit = subparsers.add_parser(
        "retrofit",
        help="add managed files to an existing project safely",
        description="Plan or apply an ownership-aware retrofit to an existing project.",
        formatter_class=formatter,
    )
    _add_generation_arguments(retrofit)
    inspect = subparsers.add_parser(
        "inspect",
        help="emit bounded read-only project evidence as JSON",
        formatter_class=formatter,
    )
    inspect.add_argument("--target", default=".", help="project directory to inspect")
    inspect.add_argument(
        "--include-snippets",
        action="store_true",
        help="include bounded raw UTF-8 snippets that may expose repository content",
    )
    inspect.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES, help="maximum regular text files")
    inspect.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="maximum bytes read")
    validate = subparsers.add_parser(
        "validate",
        help="validate a repository or generated project",
        formatter_class=formatter,
    )
    validate.add_argument("--target", default=".", help="project directory to validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            errors = validate_target(Path(args.target))
            if errors:
                for error in errors:
                    print(f"- {_terminal_safe_text(error)}", file=sys.stderr)
                return 1
            print("Validation passed.")
            return 0
        if args.command == "inspect":
            return _run_inspect(args)
        return _run_generation(args)
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        print(f"error: {_terminal_safe_text(str(exc))}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
