# Research: Full OhMyPi (omp) harness support

## Jira target

- **Resolution:** explicit user instruction in this conversation (2026-11-09): "Skip Jira — research doc only."
- No project key, site host, board id, sprint, or issuetype ids were resolved; none are recorded. No tickets exist or will be created from this document.
- Jira overlap check (skill step 4): skipped — no target project exists. N/A.

## Summary

agentic-bootstrap supports four platforms as first-class adapters (`claude`, `codex`, `pi`, `opencode`). OhMyPi (omp) is not one of them, yet omp consumes the scaffold's portable core natively today: it discovers standalone `AGENTS.md` and `.agents/skills/<name>/SKILL.md` by default and reads root `mcp.json` / `.mcp.json` as MCP fallback. "Fully supporting omp" therefore means (a) adding `omp` as a selectable platform with a Pi-style no-op adapter, (b) deciding whether to emit any omp-native artifacts (sticky `RULES.md`; `.omp/AGENTS.md` is rejected), (c) contract tests and platform documentation, and (d) an ADR. No generated-file surface changes for omp, so golden tree and examples stay byte-stable except support docs.

## Current state (evidence)

Generator (repo source):

- `SUPPORTED_PLATFORMS = ("claude", "codex", "pi", "opencode")` — `src/agentic_bootstrap/model.py:7`; unknown platforms are rejected by `FeatureSelection.validate` (`model.py:73`).
- Adapter registry `ADAPTERS` — `src/agentic_bootstrap/adapters/__init__.py:8-13`; `Adapter` protocol renders `dict[str, GeneratedFile]` (`adapters/base.py:10-16`).
- Pi precedent: `PiAdapter.render` returns `{}` with a comment stating Pi natively discovers `AGENTS.md` and `.agents/skills` and receives no settings/MCP/subagent config (`adapters/pi.py:6-10`).
- Packaged skills always render to `.agents/skills/<skill>/SKILL.md` — `renderer.py:87-91`; platform mirrors for Claude go to `.claude/skills` (`adapters/claude.py:20-23`).
- MCP/agents capability matrix per platform: `effective_by_platform` limits native MCP/agents to `{"claude","codex","opencode"}` — `renderer.py:123-129`; Pi is excluded.
- Platform support rows are generated per request — `renderer.py:174-178` (`_platform_rows`).
- Portable-neutrality invariant: `PORTABLE_FORBIDDEN = ("mcp__", "Task tool", ".claude/", ".codex/", ".opencode/", ".pi/")` scanned over `AGENTS.md` and `.agents/skills/**` — `src/agentic_bootstrap/validation.py:13` and `templates/core/bin/validate.py:99-111`; mirrored in `tests/unit/test_renderer.py:60-65`.
- Platform contract tests live in `tests/contracts/test_platforms.py` (per-platform render assertions; CLI-backed tests where the CLI is installed).
- Repository platform doc now documents omp as a portable-core consumer with verified version 18.18.3 — `docs/PLATFORM_SUPPORT.md:11-15` (added 2026-11-09); README documents supported harnesses — `README.md:34-43`.

omp harness (evidence from bundled harness docs, `omp://skills.md`, `omp://context-files.md`, `omp://mcp-config.md`, `omp://hooks.md`; provider priorities and defaults are as reported there):

- Standalone `AGENTS.md` is discovered walking from cwd to the repository root (`agents-md` provider, priority 10, default-on) — `omp://context-files.md`.
- `.agents/skills/<name>/SKILL.md` is discovered by the `agents` skill provider (priority 70), project scope enabled by default, one-level non-recursive layout — exactly the scaffold's layout (`omp://skills.md`).
- `.claude/skills` is discovered by the `claude` provider (priority 80) when the directory exists; identical same-named skill copies collapse silently during deduplication, differing copies get namespaced — `omp://skills.md`.
- Root `mcp.json` / `.mcp.json` are MCP fallback files (lowest MCP priority) — `omp://mcp-config.md`.
- omp-native surfaces the generator does not touch: `.omp/AGENTS.md` (native context, priority 100), `.omp/RULES.md` (sticky always-apply rule), `.omp/skills/` (native provider, requires `description`), `.omp/mcp.json`, and JS/TS hook factories under `.omp/hooks/pre|post/` — `omp://context-files.md`, `omp://skills.md`, `omp://mcp-config.md`, `omp://hooks.md`.
- omp slash commands `/skill:<name>` are auto-registered from discovered skills; no command files are needed — `omp://skills.md`.
- Installed omp version on this workstation: 18.18.3 (`omp --version`, 2026-11-09).

What works today without any code change: an omp session in a scaffolded project loads `AGENTS.md` (T0 progressive disclosure), all four packaged skills from `.agents/skills`, optional root `.mcp.json`, and `CLAUDE.md` (via `claude-md`, when the Claude adapter was selected).

## Gap analysis

| Capability | omp behavior | Generator today | Gap |
|---|---|---|---|
| Platform selection | Reads portable core by default | `omp` rejected as unknown platform (`model.py:73`) | Not selectable; no `--platform omp` |
| Adapter artifacts | Needs none beyond portable core | No omp adapter | Add Pi-style adapter |
| Support matrix | Documented as consumer only (`docs/PLATFORM_SUPPORT.md:11`) | Not a generated platform row | Row + template wording |
| Contract tests | Layout expectations documented by omp | No omp contract test | Add render-level test; CLI smoke manual |
| Native extras | `.omp/RULES.md` sticky rules exist | Not generated | Optional, decision-gated |
| Native MCP | Root `.mcp.json` fallback works | `--mcp` writes root `.mcp.json` via Claude adapter | None for MCP itself |
| Version pinning | omp moves fast (18.18.3 today) | Platform docs carry verified versions | Keep verified-version column current |

## Proposed design

**Decision:** add `omp` as a fifth supported platform with a Pi-style adapter that renders no platform-specific files, and keep omp-native artifacts out of the initial scope except a decision-gated sticky `RULES.md`.

1. `model.py`: `SUPPORTED_PLATFORMS += ("omp",)`; `effective_by_platform` excludes omp from native MCP/agents (join Pi's exclusion set) — `renderer.py:123-129`.
2. New `src/agentic_bootstrap/adapters/omp.py`: `OmpAdapter`, `name = "omp"`, `render` returns `{}` with a comment documenting omp's native discovery (AGENTS.md, `.agents/skills`, root `.mcp.json` fallback); register in `adapters/__init__.py` and `_platform_rows` (`renderer.py:174-178`).
3. Do **not** generate `.omp/AGENTS.md`: it would shadow the standalone `AGENTS.md` (priority 100 vs 10) and duplicate mutable-seed content with drift risk; omp's containment collapse only dedups identical files. Rejected alternative.
4. Decision-gated option: generate `.omp/RULES.md` with a handful of deterministic invariants (e.g. "never weaken security controls to make a task pass", "agent-guided bootstrap stops after preview"). Sticky rules persist across long conversations, which plain `AGENTS.md` context does not guarantee. Gate: separate story, owner decision, kept free of LLM-authored content (ADR-0005 hook/LLM principle).
5. Neutrality hardening: add `.omp/` to `PORTABLE_FORBIDDEN` in `validation.py` and the rendered `templates/core/bin/validate.py`, plus the mirrored test list (`tests/unit/test_renderer.py:63`), so core docs never embed omp-specific paths.
6. Contract test: `tests/contracts/test_platforms.py::test_omp_core_is_native` asserting (a) `render_project(request(root, ["omp"]))` produces the portable core with **no** omp-specific files, (b) `.agents/skills` set unchanged, (c) `docs/PLATFORM_SUPPORT.md` support text mentions omp as native-core. CLI-backed discovery smoke is manual until an omp introspection command is identified `[INFERENCE: none verified — omp docs list no `debug skill` equivalent]`.
7. Docs: template `docs/PLATFORM_SUPPORT.md` wording gains omp in the portable-core paragraph and platform row; repository doc row flips from "consumer" to selectable; README supported-harnesses wording updated.
8. ADR-0008 (Proposed → owner acceptance): platform-support change is durable and integration-level — required by the process (step 3) and consistent with ADR-0001.

**Rejected alternatives:** shipping an omp extension package or plugin (supply-chain + ownership burden, contradicts opt-in/manifest principles); generating `.omp/AGENTS.md` (shadowing/drift, above); doing nothing (omp remains an undocumented second-class consumer and platform rows/tests never exercise it).

## Phased delivery plan (epic + stories)

**Epic: Full OhMyPi (omp) platform support** — goal: omp becomes a selectable, tested, documented platform with zero regression to the other four.

Ordered by contract risk, not glossiness:

1. **Story 1 (P1) — omp platform + adapter + ADR-0008.** ADR-0008 Proposed; `SUPPORTED_PLATFORMS`, adapter, registry, platform rows, `effective_by_platform` exclusion, neutrality token (`.omp/`) in both validators and test list; renderer/contract tests; examples refresh; golden tree unchanged (omp adds no files). *Acceptance:* `init --platform omp --dry-run` renders the portable core with no omp-specific files; `--platform all` includes omp; `agentic_bootstrap validate` passes with a planted `.omp/` token in a core doc; unittest suite green.
2. **Story 2 (P2) — support matrix and template docs.** Generated `docs/PLATFORM_SUPPORT.md` platform row for omp; repository doc row flips to selectable; README wording; `docs/GENERATED_OUTPUT.md` unchanged. *Acceptance:* docs-check clean; docs state omp consumes the portable core natively and name what is not generated.
3. **Story 3 (P2, decision-gated) — sticky `.omp/RULES.md`.** Only if the owner accepts the invariant-file idea; opt-in with omp selection; deterministic content only. *Acceptance:* retrofit/apply ownership rules apply; content has no LLM-authored or platform-specific tool syntax beyond omp paths; tests cover idempotency.
4. **Story 4 (P3) — live omp smoke.** Manual verification on installed omp 18.18.3: session in a freshly scaffolded `--platform omp` project loads `AGENTS.md`, all four skills (`omp` skill list or session evidence), and root `.mcp.json` when `--mcp`. Record CLI version + date in `docs/PLATFORM_SUPPORT.md`. *Acceptance:* support-matrix row updated with evidence.

## Risks and open questions

- **Skill-source split-brain (omp-specific):** omp ranks `.claude/skills` (priority 80) above `.agents/skills` (70). A project selecting `claude,omp` ships identical copies today, so they collapse — but if a user edits only the `.agents/skills` copy (mutable seed), omp silently loads the stale `.claude/skills` copy. Mitigation: document the precedence in the omp platform row; possible follow-up to prefer omp users select `omp` alone or to stop mirroring skills when both are selected. Open question for the owner.
- **Version cadence:** omp releases fast; contract tests must assert layout, not version numbers. Verified-version claims must be re-dated per check (platform-doc convention already does this).
- **No CLI introspection command verified** for omp skill/config discovery `[INFERENCE]`; Story 4 must first identify the right probe (docs list `/extensions`, `omp skill list --json` for manual skills) before scripting the smoke.
- **Hooks out of scope:** omp hooks are JS/TS extension factories, not shell scripts; wiring deterministic validation into a `tool_call` hook is a separate decision and must respect ADR-0005 (no LLM in hooks, no bootstrap mutation).

## Jira overlap findings

Skipped per user instruction (no target project). If the epic is filed later, check for overlaps against `project = <KEY> AND issuetype = Epic` and text searches for "omp", "harness", "platform support" before creating anything.
