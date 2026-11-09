# Research: External repository references and Credits completeness

## Jira target

- **Resolution:** explicit user instruction in this conversation (2026-11-09): "Skip Jira — research doc only."
- No project key, site host, board id, sprint, or issuetype ids were resolved. No tickets exist or will be created from this document.
- Jira overlap check (skill step 4): skipped — no target project exists. N/A.

## Summary

The repository references six distinct external sources, of which four are external GitHub repositories. Three are already credited in the README Credits section; two are not: the skills CLI (`vercel-labs/skills`) that every install-on-demand integration depends on, and `gitleaks`, the optional credential scanner in the generated pre-commit hook. Both are documentation-only additions to the README Credits section; the ask is single-ticket scale, so no epic is proposed.

## Current state (evidence)

| External source | Referenced at | Credited |
|---|---|---|
| `cloudflare/security-audit-skill` | `README.md:118`; `docs/SECURITY_AUDIT.md:3,15`; template `SECURITY_AUDIT.md:3,15`; ADR-0006:38,95 | Yes (ADR-0006 line) |
| `addyosmani/agent-skills` | `README.md:119`; `docs/TASK_BREAKDOWN.md:5,13`; template `TASK_BREAKDOWN.md:5,13`; ADR-0007:91 | Yes (ADR-0007 line) |
| `emiliosheinz/agent-skills` | `README.md:119`; `docs/TASK_BREAKDOWN.md:6,14`; ADR-0007:92 | Yes (ADR-0007 line) |
| `vercel-labs/skills` (skills CLI) | `npx skills add` in `docs/SECURITY_AUDIT.md:15`, `docs/TASK_BREAKDOWN.md:13-14`, both templates; ADR-0006:38 ("skills CLI", unlinked) | **No** |
| `gitleaks/gitleaks` | generated `githooks/pre-commit.sh:10-12` (template `core/githooks/pre-commit.sh`) | **No** |
| `actions/checkout@v4`, `actions/setup-python@v5` | all three workflows (repo `.github/workflows/`, template `integrations/github/docs-check.yml`) | No — deliberate |
| `opencode.ai` config schema, `mcp.context7.com` | OpenCode adapter config template, Claude adapter `.mcp.json` template | No — deliberate |

## Gap analysis

- The two uncredited repositories are load-bearing: the skills CLI is the mechanism every ADR-0006/0007 install flow documents, and gitleaks is embedded in a generated hook. Both belong in Credits.
- GitHub Actions and schema/service URLs are standard plumbing and example endpoints, not upstream content or tooling the project builds on; crediting them would be noise. Documented here as deliberate exclusions.
- Credits live in the root `README.md` only; it is not a rendered template file, so no examples/golden ripple is required.

## Proposed design

Add two bullet lines to the README Credits section, ordered by integration (ADR-0006/0007 tooling, then generated-hook tooling):

1. `vercel-labs/skills` — the open skills CLI behind the documented `npx skills add` install flows (ADR-0006, ADR-0007).
2. `gitleaks` — optional staged-change credential scan in the generated Git pre-commit hook.

Rejected alternative: crediting GitHub Actions and schema URLs — standard infrastructure references, not sources the project derives from.

## Phased delivery plan

Single change, no epic and no ticket (Jira skipped per instruction):

1. Append the two credit lines to `README.md` (`## Credits`).
2. Gates: `agentic_bootstrap validate --target .`, `.agentic/bin/docs-check --strict`; commit and push to `BlasterSystems/main`.

## Risks and open questions

- New integrations must add their own credit line as part of the integration ADR; there is no automated enforcement (a docs-check rule could be added later if drift recurs).

## Jira overlap findings

Skipped per user instruction (no target project). N/A.
