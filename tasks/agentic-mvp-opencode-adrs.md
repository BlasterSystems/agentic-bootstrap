# Task: Implement provider-neutral MVP, OpenCode, and ADRs

## Objective

Implement all planned MVP stages and acceptance criteria for Claude Code, Codex, Pi, OpenCode, ADRs, progressive disclosure, safe generation, retrofit, tests, and documentation.

## Acceptance criteria

- [x] Portable core and four native adapters
- [x] ADR template, index, lifecycle, skill, and progressive disclosure
- [x] Dry-run, conflict planning, manifest ownership, rollback, and idempotency
- [x] Optional MCP, agents, GitHub, and hooks
- [x] MVP command surface is limited to init, retrofit, and validate
- [x] Unit, integration, golden, and platform contract tests implemented
- [x] All tests and validators pass
- [x] Independent review completed

## Architecture impact

- **ADR required:** Yes
- **Relevant ADRs:** ADR-0001, ADR-0002, ADR-0003

## Validation evidence

- Python 3.11, 3.13, and 3.14: 46/46 tests passed on each runtime.
- Repository package validator and local entrypoint validator passed.
- Minimal and all-platform generated examples passed standalone validation.
- Claude, Codex, Pi, and OpenCode adapter contract diagnostics passed.
- Wheel build, isolated install, packaged-template check, and JSON dry-run smoke passed.
- Hostile confinement, stale-plan, rollback, retrofit, manifest, mutable ADR index, and supersession tests passed.
- Final independent release-gate review: PASS with no remaining blockers.
