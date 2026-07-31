from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..model import BootstrapRequest, GeneratedFile
from ..templating import TemplateEngine


@dataclass(frozen=True)
class AdapterContext:
    request: BootstrapRequest
    templates: TemplateEngine
    values: dict[str, str]


class Adapter(Protocol):
    name: str

    def render(self, context: AdapterContext) -> dict[str, GeneratedFile]: ...
