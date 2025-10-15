"""Public entry points for the articles_parser package."""

# Re-export convenient entry points so that consumers can access them via
# ``import articles_parser as ap`` without having to dig into submodules.
from .pipeline import run_pipeline, run_local, try_failed

__all__ = ["run_pipeline", "run_local", "try_failed"]
