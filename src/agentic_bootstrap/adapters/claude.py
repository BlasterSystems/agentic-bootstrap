from __future__ import annotations

import json

from ..model import GeneratedFile
from .base import AdapterContext


class ClaudeAdapter:
    name = "claude"

    def render(self, context: AdapterContext) -> dict[str, GeneratedFile]:
        templates = context.templates
        values = context.values
        files = {
            "CLAUDE.md": GeneratedFile.text(
                "CLAUDE.md", templates.render("adapters/claude/CLAUDE.md", values)
            ),
        }
        for skill in ("agentic-bootstrap", "architecture-decision", "docs-check", "semantic-versioning"):
            source = f"core/skills/{skill}/SKILL.md"
            target = f".claude/skills/{skill}/SKILL.md"
            files[target] = GeneratedFile.text(target, templates.render(source, values))
        if context.request.features.agents:
            target = ".claude/agents/architecture-reviewer.md"
            files[target] = GeneratedFile.text(
                target, templates.render("adapters/claude/agents/architecture-reviewer.md", values)
            )
        if context.request.features.mcp:
            target = ".mcp.json"
            config = {
                "mcpServers": {
                    "context7": {
                        "type": "http",
                        "url": "https://mcp.context7.com/mcp",
                    }
                }
            }
            files[target] = GeneratedFile.text(target, json.dumps(config, indent=2))
        return files
