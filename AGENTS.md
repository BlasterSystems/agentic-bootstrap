# agentic-bootstrap Project Instructions

## Objective

Build and maintain a provider-neutral bootstrap that prepares greenfield and existing software projects for AI-assisted development through portable instructions, progressive disclosure, ADRs, deterministic validation, and explicit platform adapters.

## Commands

```bash
# Tests
PYTHONPATH=src python3 -m unittest discover -s tests -v

# Validate this repository
PYTHONPATH=src python3 -m agentic_bootstrap validate --target .

# Preview an all-platform project in a canonical temporary directory
(
  set -e
  preview_target="$(mktemp -d)"
  trap 'rmdir "$preview_target"' EXIT
  preview_target="$(cd "$preview_target" && pwd -P)"
  scripts/agentic-bootstrap.sh init --platform all --dry-run --yes --target "$preview_target"
)
```

## Working Rules

1. Read `docs/DEVELOPMENT_PROCESS.md` before implementation work.
2. Keep portable core content free of platform-specific tool syntax.
3. Treat integrations, permissions, hooks, MCP, and specialized agents as opt-in.
4. Never overwrite unmanaged files during retrofit.
5. Render structured formats through serializers, not unescaped substitution.
6. Add tests for generation, retrofit, idempotency, conflicts, and platform contracts.
7. Update support evidence and ADRs when capabilities or architecture change.
8. For versions, releases, or tags, read `docs/RELEASING.md` and use the `semantic-versioning` skill.

## Progressive Disclosure

| Tier | Content | Load when |
|---|---|---|
| T0 | This file | Always |
| T1 | `docs/README.md`, `docs/DEVELOPMENT_PROCESS.md`, current task | Starting implementation |
| T2 | `docs/ARCHITECTURE.md`, `docs/adr/README.md` | Architecture or rationale is relevant |
| T3 | Matching Proposed or Accepted ADRs, `docs/PLATFORM_SUPPORT.md`, or `docs/RELEASING.md` | The current scope, decision, platform, or release requires them |
| T4 | Rejected, Deprecated, or Superseded ADRs; historical specifications | Historical or full-framework investigation |

Read the ADR index before individual ADRs. Load only records relevant to the current decision.
