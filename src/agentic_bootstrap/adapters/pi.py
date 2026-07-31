from __future__ import annotations

from ..model import GeneratedFile
from .base import AdapterContext


class PiAdapter:
    name = "pi"

    def render(self, context: AdapterContext) -> dict[str, GeneratedFile]:
        # Pi natively discovers AGENTS.md and .agents/skills. It intentionally
        # receives no project settings, MCP, or subagent configuration by default.
        return {}
