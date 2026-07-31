# ADR-0001: Portable core and platform adapters

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Agentic Bootstrap maintainers
- **Scope:** Generator architecture
- **Tags:** portability, adapters, instructions
- **Supersedes:** None
- **Superseded by:** None

## Context

The v1 framework used Claude-specific files and syntax as if they were portable to every coding agent. Codex and Pi received only symlinked instructions, and platform-native configuration was missing or incorrect.

## Decision drivers

- Truthful support claims
- One durable project knowledge core
- Native platform discovery paths
- Low documentation drift
- Capability-specific fallback behavior

## Considered options

### Keep Claude as the canonical implementation

This minimizes change but continues to leak Claude-specific tools and configuration into other platforms.

### Generate independent complete projects per platform

This gives native control but duplicates workflow and architecture knowledge, creating drift.

### Portable core plus adapters

A provider-neutral core owns instructions, tasks, ADRs, and deterministic checks. Adapters add only native platform artifacts.

## Decision

Use a portable core centered on a real `AGENTS.md`, with separate Claude, Codex, Pi, and OpenCode adapters. Render shared skills from one source into the locations each platform supports.

## Consequences

### Positive

- Support claims map to official capabilities.
- Portable workflow changes are implemented once.
- Platform-specific configuration can evolve independently.

### Negative

- Adapter contract testing is required.
- Some skill files are rendered into more than one location.

### Risks and mitigations

- Platform documentation can change; record tested versions and run release smoke tests.
- Adapter duplication can drift; render from canonical templates and compare golden fixtures.

## Implementation and validation

Implement typed core rendering and adapter modules. Validate JSON/TOML, official paths, portable instruction content, and CLI discovery diagnostics.

## Revisit triggers

Revisit if the platforms converge on a complete shared configuration standard or stop supporting `AGENTS.md`/Agent Skills.

## References

- `docs/ARCHITECTURE.md`
- `docs/PLATFORM_SUPPORT.md`
