from __future__ import annotations

import json

from ..model import GeneratedFile
from .base import AdapterContext


class OpenCodeAdapter:
    name = "opencode"

    def render(self, context: AdapterContext) -> dict[str, GeneratedFile]:
        config: dict[str, object] = {
            "$schema": "https://opencode.ai/config.json",
            "permission": {
                "edit": "ask",
                "bash": "ask",
            },
        }
        if context.request.features.mcp:
            config["mcp"] = {
                "context7": {
                    "type": "remote",
                    "url": "https://mcp.context7.com/mcp",
                    "enabled": True,
                }
            }
        files: dict[str, GeneratedFile] = {
            "opencode.json": GeneratedFile.text("opencode.json", json.dumps(config, indent=2)),
        }
        for command in ("adr-new", "docs-check"):
            target = f".opencode/commands/{command}.md"
            files[target] = GeneratedFile.text(
                target,
                context.templates.render(f"adapters/opencode/commands/{command}.md", context.values),
            )
        if context.request.features.agents:
            target = ".opencode/agents/architecture-reviewer.md"
            files[target] = GeneratedFile.text(
                target,
                context.templates.render("adapters/opencode/agents/architecture-reviewer.md", context.values),
            )
        return files
