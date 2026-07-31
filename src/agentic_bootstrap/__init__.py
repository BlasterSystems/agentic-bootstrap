"""Provider-neutral deterministic bootstrap with an optional agent-guided facade."""

__version__ = "0.1.0"

from .facade import apply_bootstrap, inspect_project, prepare_bootstrap  # noqa: E402

__all__ = ["__version__", "apply_bootstrap", "inspect_project", "prepare_bootstrap"]
