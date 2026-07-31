from .base import Adapter, AdapterContext
from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .opencode import OpenCodeAdapter
from .pi import PiAdapter

ADAPTERS = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
    "pi": PiAdapter(),
    "opencode": OpenCodeAdapter(),
}

__all__ = ["ADAPTERS", "Adapter", "AdapterContext"]
