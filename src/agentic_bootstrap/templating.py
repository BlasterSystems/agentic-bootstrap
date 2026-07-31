from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class TemplateError(ValueError):
    pass


class TemplateEngine:
    def __init__(self, template_root: Path):
        self.template_root = template_root

    def read(self, relative_path: str) -> str:
        path = (self.template_root / relative_path).resolve()
        root = self.template_root.resolve()
        if root not in path.parents and path != root:
            raise TemplateError(f"template escapes root: {relative_path}")
        return path.read_text(encoding="utf-8")

    def render(self, relative_path: str, values: Mapping[str, str]) -> str:
        return self.render_text(self.read(relative_path), values, source=relative_path)

    @staticmethod
    def render_text(text: str, values: Mapping[str, str], source: str = "inline") -> str:
        missing = sorted({name for name in TOKEN.findall(text) if name not in values})
        if missing:
            raise TemplateError(f"unresolved template values in {source}: {', '.join(missing)}")
        rendered = TOKEN.sub(lambda match: values[match.group(1)], text)
        remaining = TOKEN.findall(rendered)
        if remaining:
            raise TemplateError(f"unresolved template values in {source}: {', '.join(sorted(set(remaining)))}")
        return rendered
