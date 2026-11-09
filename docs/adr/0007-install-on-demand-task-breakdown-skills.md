# ADR-0007: Install-on-demand task-breakdown skills

- **Status:** Proposed
- **Date:** 2026-11-09
- **Decision owners:** Not assigned
- **Scope:** Generator architecture and documentation architecture
- **Tags:** planning, integrations, progressive-disclosure
- **Supersedes:** None
- **Superseded by:** None

## Context

Step 2 (Plan) of the development process breaks work into independently verifiable steps using `tasks/task-template.md` and, when a ticket prefix is configured, an optional ticket lifecycle with `PREFIX-<number>` identifiers. There is no skill that performs structured research-to-task breakdown, and nothing maps task output onto an external tracker.

Upstream MIT-licensed skills cover this: addyosmani/agent-skills `planning-and-task-breakdown` (dependency graph, vertical slices, ordered tasks, pluggable task list target — markdown by default, one tracker item per task when the project designates a tracker) and emiliosheinz/agent-skills `create-tickets` (spec-to-backlog tickets created verbatim in an external tracker). Integration must respect ADR-0001 and ADR-0003 and the tracker-neutrality invariant: rendered output for projects without a ticket prefix must not name specific trackers.

## Decision drivers

- The generated `tasks/` convention is deliberately tracker-neutral; a test asserts generated content avoids tracker product names when no ticket prefix is configured.
- Vendoring skill content into `.agents/skills/` would face the portable-token scan and add third-party content to the manifest; the ADR-0006 rationale applies unchanged.
- Tracker writes are external side effects; they must stay user-confirmed.
- Per-skill installs of planning-and-task-breakdown omit the upstream shared `references/` directory (upstream issue #361); the skill remains functional standalone.
- Generation must stay offline and deterministic.

## Considered options

### Option 1: Vendor both skills into `.agents/skills/`

Deterministic and offline, but adds third-party content to the manifest, risks portable-scan conflicts, and burdens every upstream update with a re-vendor. Rejected for the same reasons as ADR-0006 Option 1.

### Option 2: Integrate only planning-and-task-breakdown

Covers breakdown but leaves spec-to-backlog work undeserved; teams that plan in a tracker must bridge manually. Rejected as too narrow.

### Option 3: Install-on-demand documentation of both skills (selected)

Generated projects receive `docs/TASK_BREAKDOWN.md` documenting install, mode selection, task-list-target mapping, and side-effect boundaries. The skills stay unmanaged; the portable core stays tracker-neutral.

### Option 4: No integration

Step 2 wording and the task template remain; agents improvise breakdown structure and tracker mapping. Rejected.

## Decision

Adopt Option 3:

1. Step 2 (Plan) references the breakdown skill for multi-step or ambiguous work and points to `docs/TASK_BREAKDOWN.md`.
2. Task list target: with a configured ticket prefix, one tracker item per task using the `PREFIX-<number>` convention (ties into the section 8 ticket lifecycle); without one, the skill defaults `tasks/plan.md` and `tasks/todo.md`, coexisting with per-task files from `tasks/task-template.md`.
3. `create-tickets` is reserved for specification-to-backlog flows whose output leaves the repository, always with user confirmation before external tracker writes.
4. Never overwrite a plan or task list that still contains unchecked tasks for different work.

## Consequences

### Positive

- Structured breakdown and tracker mapping without vendoring or manifest ownership.
- Tracker-neutrality invariant preserved in all rendered output.
- Planning artifacts (`tasks/plan.md`, `tasks/todo.md`) survive session boundaries and compaction.

### Negative

- Install requires network access and CLI support; offline projects need a manual copy.
- No version pin; upstream wording changes between installs.
- Two overlapping conventions (per-task files versus `tasks/todo.md`) need the documented mapping to avoid duplication.

### Risks and mitigations

- Accidental bulk ticket creation: confirmation required before any external tracker write.
- Overwritten in-progress plans: the never-overwrite rule is documented and enforced by the skill itself.
- Upstream license or availability changes: revisit triggers below.

## Implementation and validation

1. Added `docs/TASK_BREAKDOWN.md` to the renderer core templates as a mutable seed.
2. Wired step 2 (Plan) triggers into the template and self-hosted `DEVELOPMENT_PROCESS.md`, indexed the document in both documentation indexes and the progressive-disclosure tiers, added the optional-feature note to platform support, and credited both upstream repositories.
3. Updated the golden all-platform tree and the generated-output catalog.
4. Gates: the unittest suite, `agentic_bootstrap validate --target .`, `.agentic/bin/validate`, `docs-check`, and the canonical all-platform dry-run preview must pass.

## Revisit triggers

- A tracker-neutral upstream skill emerges that supersedes both: consolidate.
- Teams request deeper ticket automation (automatic creation without confirmation): a new ADR is required; external writes stay confirmed.
- Upstream license changes away from MIT or the repositories become unavailable.

## References

- `docs/TASK_BREAKDOWN.md` — capability document (template and self-hosted copy)
- `docs/DEVELOPMENT_PROCESS.md` — step 2 trigger
- ADR-0006 — install-on-demand pattern precedent
- ADR-0003 — opt-in integrations and safe apply
- https://github.com/addyosmani/agent-skills — planning-and-task-breakdown
- https://github.com/emiliosheinz/agent-skills — create-tickets
