from functools import lru_cache
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService


@lru_cache(maxsize=1)
def get_rag_service() -> RagSummarizeService:
    return RagSummarizeService()


@tool(description="从 PrimeBuddy 学习知识库中检索参考资料。第一阶段知识库聚焦 408 考研内容。")
def search_learning_knowledge(query: str) -> str:
    return get_rag_service().rag_summarize(query)
