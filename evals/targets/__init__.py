"""Target loader for evaluation runs."""

from __future__ import annotations

from evals.schemas import EvalTarget


def load_target(name: str) -> EvalTarget:
    if name == "v1":
        from evals.targets.v1 import V1Target

        return V1Target()
    raise ValueError(f"Unsupported eval target: {name!r}")
