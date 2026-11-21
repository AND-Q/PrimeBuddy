"""Data schemas and target protocol for PrimeBuddy evaluations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SkillSelectionCase:
    id: str
    query: str
    expected_any: list[str]
    category: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalCase:
    id: str
    query: str
    subject: str
    gold_pages: list[int]
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    subject: str
    pages: list[int]
    source: str = ""


@dataclass(frozen=True)
class E2EResult:
    answer: str
    selected_skill: str
    latency_s: float
    model_calls: int
    tool_calls: list[str] = field(default_factory=list)
    error: str | None = None


class EvalTarget(Protocol):
    name: str
    model_name: str
    embedding_model_name: str

    def select_skill(self, query: str) -> str:
        """Return the skill name chosen for query (or 'none')."""

    def retrieve(
        self,
        query: str,
        *,
        subject: str | None = None,
        k: int = 10,
    ) -> list[RetrievedChunk]:
        """Return top-k retrieved chunks with resolved subject and page numbers."""

    def run_e2e(self, query: str, *, user_id: str = "demo_user") -> E2EResult:
        """Run a full end-to-end turn and report latency, model calls, and tools."""
