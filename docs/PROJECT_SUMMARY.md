# Agentic Bootstrap Project Summary

**Current release:** MVP 0.1.0  
**Status:** Implemented; acceptance is enforced by the test and validation suites.

## Objective

Bootstrap greenfield or existing software projects with provider-neutral instructions, progressive disclosure, ADRs, safe generated-file ownership, and native adapters for Claude Code, Codex, Pi, and OpenCode.

## MVP capabilities

- Typed Python core with a shell entry point.
- Portable `AGENTS.md` instruction source.
- Native adapter artifacts and capability-specific support documentation.
- Indexed ADRs, documentation catalog, shared skills, lifecycle, and validation.
- Semantic Versioning release guidance, changelog maintenance, release commits, and annotated Git tags.
- Dry-run, JSON plans, conflicts, manifests, rollback, and idempotency.
- Opt-in MCP, agents, GitHub workflows, scheduled audits, and Git hooks.
- Unit, integration, golden-tree, and platform contract tests.

The MVP intentionally exposes only `init`, `retrofit`, and `validate`. There is no version-migration or legacy-compatibility surface before the first release.

## Acceptance evidence

- The test suite passes on Python 3.11, 3.13, and 3.14.
- Repository and generated-project validators pass.
- Four platform contract diagnostics pass.
- Wheel build and isolated installed-CLI smoke pass.
- Independent hostile safety and final release-gate reviews pass with no remaining blockers.

## Source of truth

- Architecture: `docs/ARCHITECTURE.md`
- Decisions: `docs/adr/README.md`
- Platform evidence: `docs/PLATFORM_SUPPORT.md`
- Workflow: `docs/DEVELOPMENT_PROCESS.md`
