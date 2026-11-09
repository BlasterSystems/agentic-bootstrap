# Platform Support

Last verified: 2026-11-09.

| Platform | Version verified | Instructions | Skills | Config/MCP | Agents |
|---|---:|---|---|---|---|
| Claude Code | 2.1.319 | `CLAUDE.md` with imported portable core | `.claude/skills`, including advisory bootstrap | `.mcp.json` opt-in | `.claude/agents` opt-in |
| OpenAI Codex | 0.167.0 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | `.codex/config.toml` opt-in | `.codex/agents/*.toml` opt-in |
| Pi Coding Agent | 0.84.4 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | No built-in MCP | Requires separately reviewed extension/package |
| OpenCode | 2.0.28 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | `opencode.json` and native MCP | `.opencode/agents/*.md` opt-in |
| OhMyPi (omp) | 18.18.3 | `AGENTS.md` portable core; no omp-native context generated | `.agents/skills` native (agents provider, default-on); `.claude/skills` also discovered | Root `mcp.json` / `.mcp.json` fallback | Sticky `.omp/RULES.md` invariants; no other `.omp/` artifacts |

Pi, OpenCode, and omp release channels are not npm-tracked versions and are verified against installed builds. Claude Code and Codex are verified against the npm-published latest versions (2.1.319 and 0.167.0) as of 2026-11-09.

OhMyPi (omp) is a selectable platform (ADR-0008): the adapter generates only the sticky `.omp/RULES.md` invariant file because omp natively discovers standalone `AGENTS.md` and `.agents/skills/<name>/SKILL.md` (the `agents` skill provider, project scope, one-level layout), reads root `mcp.json` / `.mcp.json` as MCP fallback files, and discovers standalone `CLAUDE.md` through its `claude-md` provider. When Claude Code and omp are both selected, identical `.claude/skills` and `.agents/skills` copies collapse during omp skill deduplication; prefer editing the `.agents/skills` copy or selecting `omp` alone, because omp ranks `.claude/skills` higher and would load a stale copy after a one-sided edit. The adapter generates only the sticky `.omp/RULES.md` invariant file (deterministic, manifest-owned); native context, native skills, `.omp/mcp.json`, and hooks are not generated.

## Support contract

Capabilities are classified independently as native, portable fallback, extension-based, unsupported, or unverified. Selecting a platform does not install credentials, models, third-party extensions, optional integrations, or user-scoped skills. The packaged/project-scoped `agentic-bootstrap` skill is advisory and stops before apply; pre-bootstrap loading is manual and not claimed as a portable installation contract. The external planning-and-task-breakdown and create-tickets skills are documented and installed on demand (ADR-0007); they are never generated, auto-installed, or manifest-owned.

## Contract validation

Tests validate official file locations and parse generated JSON/TOML. OpenCode tests use `opencode debug config`, `opencode debug skill`, and `opencode debug agent` when the CLI is installed. Provider-authenticated release smoke tests remain a release activity.

## Security defaults

No MCP server, Git hook, repository-host workflow, broad permission grant, or issue tracker is enabled without selection. Hooks never invoke an LLM or perform bootstrap mutation. OpenCode project configuration asks before edits and shell commands. Pi extension-based capabilities are never described as native. The external security-audit skill is documented and installed on demand (ADR-0006); it is never generated, auto-installed, or manifest-owned.
