from __future__ import annotations

import json

from ..model import GeneratedFile
from .base import AdapterContext


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


class CodexAdapter:
    name = "codex"

    def render(self, context: AdapterContext) -> dict[str, GeneratedFile]:
        files: dict[str, GeneratedFile] = {}
        sections: list[str] = []
        if context.request.features.agents:
            sections.extend(["[agents]", "enabled = true", "max_concurrent_threads_per_session = 4", ""])
            target = ".codex/agents/architecture-reviewer.toml"
            files[target] = GeneratedFile.text(
                target,
                context.templates.render("adapters/codex/agents/architecture-reviewer.toml", context.values),
            )
        if context.request.features.mcp:
            sections.extend(
                [
                    "[mcp_servers.context7]",
                    f"url = {_toml_string('https://mcp.context7.com/mcp')}",
                    "",
                ]
            )
        if sections:
            target = ".codex/config.toml"
            files[target] = GeneratedFile.text(target, "\n".join(sections).rstrip())
        return files
