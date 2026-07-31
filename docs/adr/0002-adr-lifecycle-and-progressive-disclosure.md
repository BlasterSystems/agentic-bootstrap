# ADR-0002: ADR lifecycle and progressive disclosure

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Agentic Bootstrap maintainers
- **Scope:** Documentation architecture
- **Tags:** adr, context, progressive-disclosure
- **Supersedes:** None
- **Superseded by:** None

## Context

The framework told projects to create ADRs but generated no directory, template, index, lifecycle, or validation. Loading every historical decision would also waste context and surface superseded guidance.

## Decision drivers

- Durable architectural rationale
- Bounded model context
- Discoverable current and historical decisions
- Cross-platform documentation behavior

## Considered options

### Keep decisions in task files

This is lightweight but makes long-term rationale difficult to discover after tasks close.

### Load every ADR as mandatory instructions

This maximizes visibility but wastes context and increases conflicts with superseded decisions.

### Indexed ADRs with lazy loading

A small index identifies status and scope. Agents load only records relevant to the current task and use superseded records only for history.

## Decision

Generate `docs/adr/README.md` and `docs/adr/template.md`. Use four-digit IDs and statuses Proposed, Accepted, Rejected, Deprecated, and Superseded. Read the index before individual ADRs and load decisions by scope or tag.

## Consequences

### Positive

- Architectural rationale survives task completion.
- Context use remains bounded.
- Supersession history remains explicit.

### Negative

- Maintainers must update the index.
- ADR triage adds process for high-impact work.

### Risks and mitigations

- Excessive ADR creation is limited by explicit qualification criteria.
- Stale indexes are caught by validation.

## Implementation and validation

Add templates, shared ADR skill, workflow checks, unique-ID/status/index validation, and task fields for architecture impact.

## Revisit triggers

Revisit if an external decision-record system becomes authoritative or repository scale requires generated indexes.

## References

- `AGENTS.md`
- `docs/DEVELOPMENT_PROCESS.md`
