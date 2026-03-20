"""多 Embedder 支持抽象层"""
from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np


class Embedder(ABC):
    """Embedding 抽象基类"""

    @abstractmethod
    async def encode(self, texts: List[str]) -> List[List[float]]:
        """将文本编码为向量"""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """获取向量维度"""
        pass


class SentenceTransformersEmbedder(Embedder):
    """Sentence Transformers Embedder"""

    def __init__(self, model: str = "all-MiniLM-L6-v2", device: Optional[str] = None):
        self.model_name = model
        self._model = None
        self._dimension: Optional[int] = None
        self.device = device

    def _get_model(self):
        """懒加载模型"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def get_dimension(self) -> int:
        if self._dimension is None:
            model = self._get_model()
            self._dimension = model.get_sentence_embedding_dimension()
        return self._dimension or 384

    async def encode(self, texts: List[str]) -> List[List[float]]:
        """同步编码，使用线程池避免阻塞"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        model = self._get_model()

        def _encode():
            return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            embeddings = await loop.run_in_executor(executor, _encode)

        return embeddings.tolist()


class OpenAIEmbedder(Embedder):
    """OpenAI Embedder"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None
        # text-embedding-3-small: 1536, text-embedding-3-large: 3072
        if "3-small" in model:
            self._dimension = dimensions or 1536
        elif "3-large" in model:
            self._dimension = dimensions or 3072
        elif "ada" in model:
            self._dimension = dimensions or 1536
        else:
            self._dimension = dimensions or 1536

    def _get_client(self):
        """懒加载 OpenAI 客户端"""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def get_dimension(self) -> int:
        return self._dimension

    async def encode(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]


class CohereEmbedder(Embedder):
    """Cohere Embedder"""

    def __init__(
        self,
        api_key: str,
        model: str = "embed-english-v3.0",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.cohere.ai"
        self._client = None
        # embed-english-v3.0: 1024, embed-english-v2.0: 4096
        if "v3.0" in model:
            self._dimension = 1024
        else:
            self._dimension = 4096

    def _get_client(self):
        """懒加载 Cohere 客户端"""
        if self._client is None:
            import cohere
            self._client = cohere.AsyncClient(self.api_key, beta_version="v2")
        return self._client

    def get_dimension(self) -> int:
        return self._dimension

    async def encode(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = await client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document",
        )
        return response.embeddings


class OllamaEmbedder(Embedder):
    """Ollama Embedder"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self.base_url = base_url
        self.model = model
        self._client = None
        # nomic-embed-text: 768
        self._dimension = 768

    def _get_client(self):
        """懒加载 Ollama 客户端"""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        return self._client

    def get_dimension(self) -> int:
        return self._dimension

    async def encode(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = await client.post("/api/embeddings", json={
            "model": self.model,
            "prompt": texts[0] if len(texts) == 1 else texts,
        })

        if response.status_code != 200:
            raise Exception(f"Ollama embedding failed: {response.text}")

        data = response.json()
        if len(texts) == 1:
            return [data["embedding"]]
        else:
            # Ollama doesn't support batch, encode individually
            results = []
            for text in texts:
                resp = await client.post("/api/embeddings", json={
                    "model": self.model,
                    "prompt": text,
                })
                results.append(resp.json()["embedding"])
            return results


def create_embedder(
    provider: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> Embedder:
    """根据配置创建 Embedder 实例"""
    match provider:
        case "sentence-transformers":
            return SentenceTransformersEmbedder(
                model=model or "all-MiniLM-L6-v2",
                **kwargs,
            )
        case "openai":
            return OpenAIEmbedder(
                api_key=api_key or "",
                model=model or "text-embedding-3-small",
                base_url=base_url,
            )
        case "cohere":
            return CohereEmbedder(
                api_key=api_key or "",
                model=model or "embed-english-v3.0",
                base_url=base_url,
            )
        case "ollama":
            return OllamaEmbedder(
                base_url=base_url or "http://localhost:11434",
                model=model or "nomic-embed-text",
            )
        case _:
            raise ValueError(f"Unknown embedder provider: {provider}")
