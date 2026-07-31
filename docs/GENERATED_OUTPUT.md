# Generated Output

This is the exact renderer output when all platforms and optional features are enabled. It is checked by `tests/golden/all-platforms/tree.txt`.

```text
.agentic/bin/docs-check
.agentic/bin/validate
.agentic/config.json
.agents/skills/architecture-decision/SKILL.md
.agents/skills/docs-check/SKILL.md
.agents/skills/semantic-versioning/SKILL.md
.claude/agents/architecture-reviewer.md
.claude/skills/architecture-decision/SKILL.md
.claude/skills/docs-check/SKILL.md
.claude/skills/semantic-versioning/SKILL.md
.codex/agents/architecture-reviewer.toml
.codex/config.toml
.githooks/pre-commit
.github/workflows/docs-check.yml
.mcp.json
.opencode/agents/architecture-reviewer.md
.opencode/commands/adr-new.md
.opencode/commands/docs-check.md
AGENTS.md
CLAUDE.md
docs/ARCHITECTURE.md
docs/DEVELOPMENT_PROCESS.md
docs/PLATFORM_SUPPORT.md
docs/README.md
docs/RELEASING.md
docs/adr/README.md
docs/adr/template.md
opencode.json
setup-hooks.sh
tasks/task-template.md
```

`.agentic/manifest.json` is written only after a successful apply and is not renderer output. New projects do not receive `.codex.md` or `.claude/claude.json`.
