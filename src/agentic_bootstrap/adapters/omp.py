from __future__ import annotations

from ..model import GeneratedFile
from .base import AdapterContext


class OmpAdapter:
    name = "omp"

    def render(self, context: AdapterContext) -> dict[str, GeneratedFile]:
        # omp natively discovers standalone AGENTS.md and .agents/skills (agents
        # provider, project scope, one-level layout) and reads root mcp.json /
        # .mcp.json as MCP fallback files. The only generated omp-native artifact
        # is the sticky .omp/RULES.md invariant file; no .omp/AGENTS.md, native
        # skills, .omp/mcp.json, or hooks are generated.
        return {
            ".omp/RULES.md": GeneratedFile.text(
                ".omp/RULES.md",
                context.templates.render("adapters/omp/RULES.md", context.values),
            )
        }
