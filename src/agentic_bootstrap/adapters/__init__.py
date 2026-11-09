from .base import Adapter, AdapterContext
from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .omp import OmpAdapter
from .opencode import OpenCodeAdapter
from .pi import PiAdapter

ADAPTERS = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
    "omp": OmpAdapter(),
    "pi": PiAdapter(),
    "opencode": OpenCodeAdapter(),
}

__all__ = ["ADAPTERS", "Adapter", "AdapterContext"]
