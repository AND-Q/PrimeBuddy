"""v1 evaluation target wrapping StudyCopilotSupervisor and VectorStoreService."""

from __future__ import annotations

import re
import time
from bisect import bisect_right
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tracers.context import register_configure_hook

from evals.schemas import E2EResult, RetrievedChunk

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_408_DIR = PROJECT_ROOT / "data" / "408"

ROUTE_TO_SKILL = {
    "tutor": "explain-408",
    "planner": "study-plan",
    "mistake": "mistake-review",
    "report": "weekly-report",
    "general": "none",
}

FILE_TO_SUBJECT = {
    "operating_system.txt": "操作系统",
    "computer_network.txt": "计算机网络",
    "computer_organization.txt": "计算机组成原理",
    "data_structure.txt": "数据结构",
}

PAGE_MARKER_RE = re.compile(r"\[来源：[^，]+，第\s*(\d+)\s*页\]")


class _CallCounterHandler(BaseCallbackHandler):
    """Thread-safe LangChain callback counting LLM and tool calls across nested chains."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._seen_llm_runs: set[UUID] = set()
        self._seen_tool_runs: set[UUID] = set()
        self.model_calls: int = 0
        self.tool_calls: list[str] = []

    def _record_llm(self, run_id: UUID | None) -> None:
        with self._lock:
            if run_id is not None:
                if run_id in self._seen_llm_runs:
                    return
                self._seen_llm_runs.add(run_id)
            self.model_calls += 1

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._record_llm(run_id)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._record_llm(run_id)

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name") or kwargs.get("name") or "unknown_tool"
        with self._lock:
            if run_id in self._seen_tool_runs:
                return
            self._seen_tool_runs.add(run_id)
            self.tool_calls.append(str(name))


_call_counter_var: ContextVar[_CallCounterHandler | None] = ContextVar(
    "primebuddy_eval_call_counter",
    default=None,
)
register_configure_hook(_call_counter_var, inheritable=True)


@contextmanager
def track_calls():
    handler = _CallCounterHandler()
    token = _call_counter_var.set(handler)
    try:
        yield handler
    finally:
        _call_counter_var.reset(token)


class _SourcePageIndex:
    """Resolve v1 chunk page numbers from data/408/*.txt source markers."""

    def __init__(self, data_dir: Path = DATA_408_DIR) -> None:
        self._data_dir = data_dir
        self._cache: dict[str, tuple[str, list[int], list[int]]] = {}

    def _load(self, filename: str) -> tuple[str, list[int], list[int]] | None:
        if filename in self._cache:
            return self._cache[filename]
        path = self._data_dir / filename
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        positions: list[int] = []
        pages: list[int] = []
        for match in PAGE_MARKER_RE.finditer(text):
            positions.append(match.start())
            pages.append(int(match.group(1)))
        entry = (text, positions, pages)
        self._cache[filename] = entry
        return entry

    def resolve(self, content: str, source: str) -> tuple[str, list[int]]:
        filename = Path(source).name if source else ""
        subject = FILE_TO_SUBJECT.get(filename, "")
        resolved: list[int] = []

        loaded = self._load(filename) if filename else None
        if loaded is not None:
            text, positions, pages = loaded
            pos = text.find(content)
            if pos == -1 and len(content) > 80:
                pos = text.find(content[:80])
            if pos != -1 and positions:
                idx = bisect_right(positions, pos) - 1
                if idx >= 0:
                    resolved.append(pages[idx])

        for match in PAGE_MARKER_RE.finditer(content):
            page_num = int(match.group(1))
            if page_num not in resolved:
                resolved.append(page_num)

        return subject, resolved


class V1Target:
    """Evaluation adapter for the legacy StudyCopilotSupervisor + Chroma RAG."""

    name = "v1"

    def __init__(self) -> None:
        from utils.config_handler import rag_conf

        self.model_name = str(rag_conf["chat_model_name"])
        self.embedding_model_name = str(rag_conf["embedding_model_name"])
        self._supervisor = None
        self._vector_store_service = None
        self._page_index = _SourcePageIndex()

    def _get_supervisor(self):
        if self._supervisor is None:
            from agent.study_supervisor import StudyCopilotSupervisor

            self._supervisor = StudyCopilotSupervisor()
        return self._supervisor

    def _get_vector_store(self):
        if self._vector_store_service is None:
            from rag.vector_store import VectorStoreService

            self._vector_store_service = VectorStoreService()
        return self._vector_store_service

    def select_skill(self, query: str) -> str:
        route_result = self._get_supervisor().route(query)
        return ROUTE_TO_SKILL.get(route_result.route, "none")

    def retrieve(
        self,
        query: str,
        *,
        subject: str | None = None,
        k: int = 10,
    ) -> list[RetrievedChunk]:
        # v1 retriever does not filter by subject metadata; query Chroma directly.
        _ = subject
        retriever = self._get_vector_store().vector_store.as_retriever(search_kwargs={"k": k})
        docs = retriever.invoke(query)
        results: list[RetrievedChunk] = []
        for doc in docs:
            source = str(doc.metadata.get("source", ""))
            resolved_subject, pages = self._page_index.resolve(doc.page_content, source)
            results.append(
                RetrievedChunk(
                    content=doc.page_content,
                    subject=resolved_subject,
                    pages=pages,
                    source=Path(source).name if source else "",
                )
            )
        return results

    def run_e2e(self, query: str, *, user_id: str = "demo_user") -> E2EResult:
        supervisor = self._get_supervisor()
        selected_skill = ROUTE_TO_SKILL.get(supervisor.route(query).route, "none")
        start = time.perf_counter()
        try:
            with track_calls() as counter:
                answer = supervisor.execute(query, user_id=user_id)
            latency_s = time.perf_counter() - start
            return E2EResult(
                answer=answer,
                selected_skill=selected_skill,
                latency_s=latency_s,
                model_calls=counter.model_calls,
                tool_calls=list(counter.tool_calls),
            )
        except Exception as exc:
            latency_s = time.perf_counter() - start
            return E2EResult(
                answer="",
                selected_skill=selected_skill,
                latency_s=latency_s,
                model_calls=0,
                tool_calls=[],
                error=f"{type(exc).__name__}: {exc}",
            )
