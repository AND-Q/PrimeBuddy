"""Evaluation metric helpers shared across v1 and v2 targets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from evals.schemas import E2EResult, RetrievalCase, RetrievedChunk, SkillSelectionCase


@dataclass(frozen=True)
class SkillRecord:
    case: SkillSelectionCase
    predicted: str
    correct: bool


@dataclass(frozen=True)
class RetrievalRecord:
    case: RetrievalCase
    chunks: list[RetrievedChunk]
    hit_at_5: bool
    first_hit_rank: int | None
    rr_at_10: float


@dataclass(frozen=True)
class E2ERecord:
    case: SkillSelectionCase
    result: E2EResult


def percentile(values: Sequence[float], p: float) -> float:
    """Compute percentile p (0..100) using linear interpolation."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    idx = (len(ordered) - 1) * (p / 100.0)
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)


def is_chunk_hit(
    chunk: RetrievedChunk,
    *,
    subject: str | None,
    gold_pages: Sequence[int],
) -> bool:
    if subject and chunk.subject != subject:
        return False
    gold_set = set(gold_pages)
    return any(page in gold_set for page in chunk.pages)


def evaluate_retrieval_case(
    case: RetrievalCase,
    chunks: list[RetrievedChunk],
) -> RetrievalRecord:
    first_hit_rank: int | None = None
    for rank, chunk in enumerate(chunks[:10], start=1):
        if is_chunk_hit(chunk, subject=case.subject, gold_pages=case.gold_pages):
            first_hit_rank = rank
            break

    hit_at_5 = first_hit_rank is not None and first_hit_rank <= 5
    rr_at_10 = (1.0 / first_hit_rank) if first_hit_rank is not None else 0.0
    return RetrievalRecord(
        case=case,
        chunks=chunks[:10],
        hit_at_5=hit_at_5,
        first_hit_rank=first_hit_rank,
        rr_at_10=rr_at_10,
    )


def compute_skill_metrics(records: Sequence[SkillRecord]) -> dict:
    total = len(records)
    correct = sum(1 for r in records if r.correct)

    by_category: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[SkillRecord]] = defaultdict(list)
    for r in records:
        grouped[r.case.category].append(r)
    for cat, items in sorted(grouped.items()):
        cat_ok = sum(1 for i in items if i.correct)
        by_category[cat] = {
            "total": len(items),
            "correct": cat_ok,
            "accuracy": (cat_ok / len(items)) if items else 0.0,
        }

    colloquial = [r for r in records if "colloquial_review" in r.case.tags]
    col_ok = sum(1 for r in colloquial if r.correct)

    return {
        "total": total,
        "correct": correct,
        "accuracy": (correct / total) if total else 0.0,
        "colloquial_total": len(colloquial),
        "colloquial_correct": col_ok,
        "colloquial_accuracy": (col_ok / len(colloquial)) if colloquial else 0.0,
        "by_category": by_category,
    }


def compute_retrieval_metrics(records: Sequence[RetrievalRecord]) -> dict:
    total = len(records)
    hits_5 = sum(1 for r in records if r.hit_at_5)
    hits_10 = sum(1 for r in records if r.first_hit_rank is not None)
    mrr_10 = (sum(r.rr_at_10 for r in records) / total) if total else 0.0

    by_subject: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[RetrievalRecord]] = defaultdict(list)
    for r in records:
        grouped[r.case.subject].append(r)
    for subj, items in sorted(grouped.items()):
        n = len(items)
        s_h5 = sum(1 for i in items if i.hit_at_5)
        s_h10 = sum(1 for i in items if i.first_hit_rank is not None)
        s_mrr = sum(i.rr_at_10 for i in items) / n if n else 0.0
        by_subject[subj] = {
            "total": n,
            "hits_at_5": s_h5,
            "recall_at_5": s_h5 / n if n else 0.0,
            "hits_at_10": s_h10,
            "recall_at_10": s_h10 / n if n else 0.0,
            "mrr_at_10": s_mrr,
        }

    return {
        "total": total,
        "hits_at_5": hits_5,
        "recall_at_5": (hits_5 / total) if total else 0.0,
        "hits_at_10": hits_10,
        "recall_at_10": (hits_10 / total) if total else 0.0,
        "mrr_at_10": mrr_10,
        "by_subject": by_subject,
    }


def compute_e2e_metrics(records: Sequence[E2ERecord]) -> dict:
    total = len(records)
    latencies = [r.result.latency_s for r in records]
    model_calls = [r.result.model_calls for r in records]
    tool_counts = [len(r.result.tool_calls) for r in records]
    errors = sum(1 for r in records if r.result.error)

    by_category: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[E2ERecord]] = defaultdict(list)
    for r in records:
        grouped[r.case.category].append(r)
    for cat, items in sorted(grouped.items()):
        cat_lat = [i.result.latency_s for i in items]
        cat_calls = [i.result.model_calls for i in items]
        cat_tools = [len(i.result.tool_calls) for i in items]
        by_category[cat] = {
            "total": len(items),
            "p50_latency_s": percentile(cat_lat, 50),
            "avg_latency_s": sum(cat_lat) / len(cat_lat),
            "avg_model_calls": sum(cat_calls) / len(cat_calls),
            "avg_tool_calls": sum(cat_tools) / len(cat_tools),
        }

    return {
        "total": total,
        "errors": errors,
        "p50_latency_s": percentile(latencies, 50),
        "p95_latency_s": percentile(latencies, 95),
        "avg_latency_s": (sum(latencies) / total) if total else 0.0,
        "avg_model_calls": (sum(model_calls) / total) if total else 0.0,
        "min_model_calls": min(model_calls) if model_calls else 0,
        "max_model_calls": max(model_calls) if model_calls else 0,
        "avg_tool_calls": (sum(tool_counts) / total) if total else 0.0,
        "by_category": by_category,
    }
