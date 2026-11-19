from functools import lru_cache
from threading import Lock
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService

_rag_service_lock = Lock()


@lru_cache(maxsize=1)
def _build_rag_service() -> RagSummarizeService:
    return RagSummarizeService()


def get_rag_service() -> RagSummarizeService:
    # 模型并行调用检索工具时，多个线程会同时首次进入这里；加锁保证只创建一个 Chroma 客户端
    with _rag_service_lock:
        return _build_rag_service()


@tool(description="从 PrimeBuddy 学习知识库中检索参考资料。第一阶段知识库聚焦 408 考研内容。")
def search_learning_knowledge(query: str) -> str:
    return get_rag_service().rag_summarize(query)
