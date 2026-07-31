# Agentic Bootstrap MVP Specification

## Scope

Agentic Bootstrap produces a portable project core and optional native adapters for Claude Code, OpenAI Codex, Pi Coding Agent, and OpenCode. The MVP supports greenfield initialization, retrofit, dry-run planning, and deterministic validation.

## Required core

Every generated project contains:

- `AGENTS.md`
- `.agentic/config.json`
- `.agentic/manifest.json` after apply
- `.agentic/bin/validate`
- `.agentic/bin/docs-check`
- `.agents/skills/agentic-bootstrap/SKILL.md`
- `.agents/skills/architecture-decision/SKILL.md`
- `.agents/skills/docs-check/SKILL.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_PROCESS.md`
- `docs/PLATFORM_SUPPORT.md`
- `docs/adr/README.md`
- `docs/adr/template.md`
- `tasks/task-template.md`

## Progressive disclosure

T0 loads portable instructions. T1 loads process and current task. T2 loads architecture and the ADR index. T3 loads matching Proposed or Accepted ADRs. T4 loads Rejected, Deprecated, or Superseded decisions and historical specifications only for audit or conflict resolution.

## Adapter contract

Adapters may emit only documented platform locations. They must not place platform tool syntax in the portable core. Optional capabilities must be truthfully classified when a platform requires an extension.

## Safety contract

- Inspection and dry-run perform no filesystem or Git configuration writes.
- Agent proposals cannot supply generated paths, content, modes, ownership, confirmations, or approvals.
- Agent-guided apply requires trusted-terminal recomputation, complete display, and direct human confirmation; `--yes` is rejected.
- Unmanaged destinations are conflicts unless byte-identical, in which case they remain unmanaged.
- Immutable manifest-owned files update only when content and mode are unmodified; designated mutable documentation seeds preserve user customization.
- Obsolete files require explicit removal.
- Apply stages output and attempts rollback after failure.
- Integrations and privileged behavior are opt-in.

## Validation contract

Generated JSON and TOML parse, executables pass syntax checks, no unresolved template token remains, ADR IDs and statuses are valid, every ADR is indexed, and portable instructions contain no adapter syntax.

## Command surface

The deterministic command surface exposes `init`, `retrofit`, read-only `inspect`, and `validate`. Agent-guided planning is additive flags on `init` and `retrofit`; there are no separate `plan` or `apply` commands. Version migration and backward-compatibility entry points remain deferred.

## Acceptance

The repository test suite and generated-project validators define executable acceptance. README output trees must match golden fixtures, and platform diagnostics run when the corresponding CLI is available.
