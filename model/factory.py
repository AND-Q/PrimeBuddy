import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import ChatOpenAI
from utils.config_handler import rag_conf


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        api_key = os.getenv("MY_API_KEY")
        base_url = os.getenv("MY_BASE_URL")
        if not api_key or not base_url:
            raise RuntimeError("缺少 MY_API_KEY 或 MY_BASE_URL，调用模型专家前需要先配置环境变量。")

        return ChatOpenAI(
            model=rag_conf["chat_model_name"],
            api_key=api_key,
            base_url=base_url,
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        if not os.getenv("DASHSCOPE_API_KEY"):
            raise RuntimeError("缺少 DASHSCOPE_API_KEY，调用 RAG 知识库检索前需要先配置环境变量。")

        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    return ChatModelFactory().generator()


@lru_cache(maxsize=1)
def get_embed_model() -> Embeddings:
    return EmbeddingsFactory().generator()
