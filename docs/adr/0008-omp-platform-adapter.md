# ADR-0008: OMP platform adapter

- **Status:** Proposed
- **Date:** 2026-11-09
- **Decision owners:** Not assigned
- **Scope:** Generator architecture and platform support
- **Tags:** platforms, omp, adapters, portability
- **Supersedes:** None
- **Superseded by:** None

## Context

OhMyPi (omp) consumes the scaffold's portable core natively: it discovers standalone `AGENTS.md` and `.agents/skills/<name>/SKILL.md` by default, reads root `mcp.json` / `.mcp.json` as MCP fallback files, and discovers standalone `CLAUDE.md`. Despite this, omp is not a selectable platform: `SUPPORTED_PLATFORMS` rejects it, there is no adapter, no generated platform row, and no contract test exercising an omp-shaped request. The research document `tasks/research-omp-support.md` records the full evidence base and gap analysis.

## Decision drivers

- omp needs no platform-specific files beyond the portable core, matching the existing Pi adapter precedent (empty render).
- Platform support is a durable, integration-level decision requiring an ADR per the development process.
- omp ranks `.claude/skills` above `.agents/skills` during skill deduplication; projects selecting both must avoid stale-copy precedence.
- The portable core must stay free of omp-specific paths: `.omp/` joins the forbidden portable tokens.
- omp-native artifacts (`.omp/AGENTS.md`, `.omp/mcp.json`, hooks) remain ungenerated; generating them expands ownership and trust surface without demonstrated need.
- Generation must stay offline and deterministic; omp version cadence must not be encoded in templates.

## Considered options

### Option 1: Minimal native adapter (selected)

Add `omp` to `SUPPORTED_PLATFORMS` with an adapter that renders only the sticky `.omp/RULES.md` invariant file. omp's native discovery covers everything else the portable core provides. Minimal surface; the invariant file is the only generated-file addition.

### Option 2: Generate omp-native artifacts

Emit `.omp/AGENTS.md` and/or `.omp/mcp.json`. `.omp/AGENTS.md` would shadow the standalone `AGENTS.md` (omp native priority 100 versus 10) and duplicate mutable-seed content with drift risk. The sticky `.omp/RULES.md` invariant file was accepted separately on 2026-11-09 and is part of this decision; native skills, native MCP config, and hooks remain rejected.

### Option 3: Do nothing

omp remains an undocumented, unselectable consumer; platform rows and contract tests never exercise it, and support claims stay unverified. Rejected.

## Decision

Adopt Option 1: omp becomes the fifth supported platform with a minimal adapter that emits only the sticky `.omp/RULES.md` invariant file (owner-approved 2026-11-09).

1. `SUPPORTED_PLATFORMS` gains `"omp"`; MCP/agents `effective_by_platform` excludes omp (already, by set membership).
2. `adapters/omp.py` renders exactly one omp-native artifact: the sticky `.omp/RULES.md` invariant file. The platform row describes native portable-core consumption, the root `mcp.json` fallback, and the sticky rules.
3. `.omp/` joins `PORTABLE_FORBIDDEN` in both validators and the mirrored test token list.
4. A contract test asserts an omp-only request renders the portable core, exactly the `.omp/RULES.md` artifact, and no root `.mcp.json`.
5. Support docs and README describe omp as selectable and document the skill-precedence caveat for `claude,omp` combinations.
6. A live smoke against installed omp (18.18.3 at authoring time) updates the verified-version column.

## Consequences

### Positive

- omp users get first-class selection, validation, manifest ownership, and retrofit semantics for free.
- One new generated file (`.omp/RULES.md`): golden tree, examples, and ownership model updated accordingly.
- Portable-core neutrality now explicitly covers omp paths.

### Negative

- omp-specific capabilities (native skills, native context file, hooks) remain unreachable through the generator.
- Support claims rely on omp's documented discovery behavior; the live smoke uses `omp skill list` plus session evidence and is re-run per verification.

### Risks and mitigations

- Skill-source split-brain for `claude,omp` projects: documented in the platform support notes; revisit if users hit stale-copy loads.
- omp behavior changes across versions: contract tests assert layout, not versions; verified versions are re-dated per check.

## Implementation and validation

1. Platform, adapter, sticky `.omp/RULES.md`, registry, platform rows, neutrality tokens, contract tests, and docs landed on `feat/omp-platform-support`.
2. Gates: the unittest suite (including the new omp contract test), `agentic_bootstrap validate --target .`, `.agentic/bin/validate` (ADR structural checks), `docs-check`, the canonical all-platform dry-run preview, and both example refreshes.
3. Live omp smoke recorded in `docs/PLATFORM_SUPPORT.md` with CLI version and date.

## Revisit triggers

- omp ships an introspection command enabling scripted discovery smoke.
- Users report stale-copy skill loads in `claude,omp` projects: revisit skill mirroring or precedence guidance.
- omp changes discovery defaults (providers, layout, priorities): re-verify and update the support row.

## References

- `tasks/research-omp-support.md` — research and gap analysis
- ADR-0001 — portable core and platform adapters
- ADR-0003 — opt-in integrations and safe apply
- ADR-0005 — agent-guided bootstrap and hook/LLM boundary
- omp harness docs: skills, context files, MCP config (bundled `omp://` documentation)
