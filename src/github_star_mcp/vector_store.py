"""Qdrant 向量存储模块"""
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .config import QdrantConfig
from .storage import Project

COLLECTION_NAME = "github_stars"


class VectorStore:
    """Qdrant 向量存储"""

    def __init__(self, config: QdrantConfig):
        self.config = config
        self._client: Optional[QdrantClient] = None
        self._embedding_model = None

    async def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(host=self.config.host, port=self.config.port)
            # 确保 collection 存在
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]
            if COLLECTION_NAME not in collection_names:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.config.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
        return self._client

    def _get_embedding_model(self):
        """获取 embedding 模型 (延迟加载)"""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            # 使用轻量级模型
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedding_model

    def _create_text(self, project: Project) -> str:
        """创建用于向量化的文本"""
        parts = [
            project.name,
            project.description or "",
            project.language or "",
            " ".join(project.topics.split(",")) if project.topics else "",
            project.readme_content or "",
        ]
        return " | ".join([p for p in parts if p])

    async def add_project(self, project: Project) -> str:
        """添加项目到向量库"""
        client = await self._get_client()
        model = self._get_embedding_model()

        # 创建向量
        text = self._create_text(project)
        vector = model.encode(text).tolist()

        # 生成唯一 ID
        point_id = str(uuid.uuid4())

        # 添加到 Qdrant
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "project_id": project.id,
                        "full_name": project.full_name,
                        "name": project.name,
                        "description": project.description,
                        "language": project.language,
                        "topics": project.topics,
                        "html_url": project.html_url,
                    },
                )
            ],
        )

        return point_id

    async def search(
        self,
        query: str,
        limit: int = 5,
        language: Optional[str] = None,
    ) -> list[dict]:
        """向量搜索"""
        client = await self._get_client()
        model = self._get_embedding_model()

        # 创建查询向量
        vector = model.encode(query).tolist()

        # 搜索
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=limit,
            query_filter=None,  # 可以添加过滤条件
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]

    async def delete_project(self, project_id: int) -> None:
        """删除项目"""
        client = await self._get_client()
        # 需要先查询找到对应的 point_id
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [{"key": "project_id", "match": {"value": project_id}}]
            },
        )
        if results[0]:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=[r.id for r in results[0]],
            )

    async def get_point_by_project_id(self, project_id: int) -> Optional[str]:
        """通过项目 ID 获取向量 ID"""
        client = await self._get_client()
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [{"key": "project_id", "match": {"value": project_id}}]
            },
            limit=1,
        )
        if results[0]:
            return results[0][0].id
        return None


def create_vector_store(config: QdrantConfig) -> VectorStore:
    """创建向量存储实例"""
    return VectorStore(config)
