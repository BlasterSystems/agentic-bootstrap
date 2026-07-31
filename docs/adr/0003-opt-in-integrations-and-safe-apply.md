# ADR-0003: Opt-in integrations and safe apply

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Agentic Bootstrap maintainers
- **Scope:** Security and generation
- **Tags:** safety, manifest, integrations, retrofit
- **Supersedes:** None
- **Superseded by:** None

## Context

V1 enabled MCP servers and broad permissions by default, changed Git hook configuration, and lacked dry-run, ownership, rollback, and reliable idempotency. Retrofit safety could not be proven.

## Decision drivers

- Preserve user-owned files and Git configuration
- Explicit consent for networked or privileged integrations
- Repeatable generation
- Recoverability after partial failure

## Considered options

### Continue skip-if-present Bash writes

This is simple but cannot distinguish generated files from user modifications or support safe upgrades.

### Always overwrite generated paths after confirmation

This is predictable but can destroy unmanaged or edited configuration.

### Ownership manifest and transactional plan

Record generated hashes, classify each operation, stage and validate output, and roll back on apply failure.

## Decision

Use `.agentic/manifest.json` for ownership, modes, mutability policy, and hashes. Classify operations as create, generated update, unchanged, unmanaged skip, conflict, stale-claim pruning, or obsolete removal. Abort on conflicts and revalidate stale plans immediately before apply. Mutable documentation seeds are preserved after customization while structural validation remains enforced. Make MCP, agents, GitHub workflows, scheduled audits, and hooks explicit flags.

## Consequences

### Positive

- Retrofit preserves unmanaged content.
- Dry-run and machine-readable plans support review and automation.
- Repeated apply is deterministic.

### Negative

- Apply and rollback logic are more complex.
- Obsolete generated resources require explicit removal.

### Risks and mitigations

- Filesystem operations cannot be globally atomic; use staging, backups, ordered replacement, and rollback tests.
- Manifest loss makes files unmanaged; default to conflict rather than overwrite.

## Implementation and validation

Add planning, manifest, staged apply, rollback, conflict, idempotency, dry-run, and custom-hook-path tests on macOS and Ubuntu.

## Revisit triggers

Revisit if the generator moves to a packaging system with native transactional ownership.

## References

- `docs/ARCHITECTURE.md`
- `tests/integration/`
