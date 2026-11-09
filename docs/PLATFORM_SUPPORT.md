# Platform Support

Last verified: 2026-11-09.

| Platform | Version verified | Instructions | Skills | Config/MCP | Agents |
|---|---:|---|---|---|---|
| Claude Code | 2.1.220 | `CLAUDE.md` with imported portable core | `.claude/skills`, including advisory bootstrap | `.mcp.json` opt-in | `.claude/agents` opt-in |
| OpenAI Codex | 0.145.0 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | `.codex/config.toml` opt-in | `.codex/agents/*.toml` opt-in |
| Pi Coding Agent | 0.84.4 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | No built-in MCP | Requires separately reviewed extension/package |
| OpenCode | 2.0.28 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | `opencode.json` and native MCP | `.opencode/agents/*.md` opt-in |
| OhMyPi (omp) | 18.18.3 | `AGENTS.md` standalone discovery; native `.omp/AGENTS.md` not generated | `.agents/skills` native (agents provider, default-on); `.claude/skills` also discovered | Root `mcp.json` / `.mcp.json` fallback | No adapter artifacts; omp hooks/plugins not generated |

Upstream releases newer than the verified versions were published as of 2026-11-09 for Claude Code (2.1.319) and Codex (0.167.0); they have not yet been verified against this repository's contract tests. Pi, OpenCode, and omp release channels are not npm-tracked versions and are verified against installed builds.

OhMyPi (omp) is consumed through the portable core and is not a selectable adapter: omp discovers standalone `AGENTS.md` and `.agents/skills/<name>/SKILL.md` by default (the `agents` skill provider, project scope, one-level layout), reads root `mcp.json` / `.mcp.json` as MCP fallback files, and discovers standalone `CLAUDE.md` through its `claude-md` provider. Identical `.claude/skills` and `.agents/skills` copies collapse silently during omp skill deduplication. No `.omp/` artifacts (native context file, sticky `RULES.md`, `.omp/mcp.json`, hooks) are generated.

## Support contract

Capabilities are classified independently as native, portable fallback, extension-based, unsupported, or unverified. Selecting a platform does not install credentials, models, third-party extensions, optional integrations, or user-scoped skills. The packaged/project-scoped `agentic-bootstrap` skill is advisory and stops before apply; pre-bootstrap loading is manual and not claimed as a portable installation contract. The external planning-and-task-breakdown and create-tickets skills are documented and installed on demand (ADR-0007); they are never generated, auto-installed, or manifest-owned.

## Contract validation

Tests validate official file locations and parse generated JSON/TOML. OpenCode tests use `opencode debug config`, `opencode debug skill`, and `opencode debug agent` when the CLI is installed. Provider-authenticated release smoke tests remain a release activity.

## Security defaults

No MCP server, Git hook, repository-host workflow, broad permission grant, or issue tracker is enabled without selection. Hooks never invoke an LLM or perform bootstrap mutation. OpenCode project configuration asks before edits and shell commands. Pi extension-based capabilities are never described as native. The external security-audit skill is documented and installed on demand (ADR-0006); it is never generated, auto-installed, or manifest-owned.
