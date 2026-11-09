# Platform Support

Last verified: 2026-07-31.

| Platform | Version verified | Instructions | Skills | Config/MCP | Agents |
|---|---:|---|---|---|---|
| Claude Code | 2.1.170 | `CLAUDE.md` with imported portable core | `.claude/skills`, including advisory bootstrap | `.mcp.json` opt-in | `.claude/agents` opt-in |
| OpenAI Codex | 0.145.0 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | `.codex/config.toml` opt-in | `.codex/agents/*.toml` opt-in |
| Pi Coding Agent | 0.83.0 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | No built-in MCP | Requires separately reviewed extension/package |
| OpenCode | 1.2.27 | `AGENTS.md` | `.agents/skills`, including advisory bootstrap | `opencode.json` and native MCP | `.opencode/agents/*.md` opt-in |

## Support contract

Capabilities are classified independently as native, portable fallback, extension-based, unsupported, or unverified. Selecting a platform does not install credentials, models, third-party extensions, optional integrations, or user-scoped skills. The packaged/project-scoped `agentic-bootstrap` skill is advisory and stops before apply; pre-bootstrap loading is manual and not claimed as a portable installation contract. The external planning-and-task-breakdown and create-tickets skills are documented and installed on demand (ADR-0007); they are never generated, auto-installed, or manifest-owned.

## Contract validation

Tests validate official file locations and parse generated JSON/TOML. OpenCode tests use `opencode debug config`, `opencode debug skill`, and `opencode debug agent` when the CLI is installed. Provider-authenticated release smoke tests remain a release activity.

## Security defaults

No MCP server, Git hook, repository-host workflow, broad permission grant, or issue tracker is enabled without selection. Hooks never invoke an LLM or perform bootstrap mutation. OpenCode project configuration asks before edits and shell commands. Pi extension-based capabilities are never described as native. The external security-audit skill is documented and installed on demand (ADR-0006); it is never generated, auto-installed, or manifest-owned.
