"""LanceDB 向量存储模块"""
import uuid
from pathlib import Path
from typing import Optional

import numpy as np

from .config import Config
from .storage import Project

TABLE_NAME = "github_stars"
VECTOR_SIZE = 384  # sentence-transformers all-MiniLM-L6-v2


class VectorStore:
    """LanceDB 向量存储"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db = None
        self._embedding_model = None

    def _get_db(self):
        """获取 LanceDB 连接"""
        if self._db is None:
            import lancedb

            self.db_path.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    def _get_table(self):
        """获取向量表，不存在则创建"""
        db = self._get_db()
        names = db.table_names()
        if TABLE_NAME not in names:
            import lancedb
            import pyarrow as pa

            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("project_id", pa.int32()),
                pa.field("full_name", pa.string()),
                pa.field("name", pa.string()),
                pa.field("description", pa.string()),
                pa.field("language", pa.string()),
                pa.field("topics", pa.string()),
                pa.field("html_url", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), VECTOR_SIZE)),
            ])
            db.create_table(TABLE_NAME, schema=schema)

            # 创建向量索引
            tbl = db.open_table(TABLE_NAME)
            tbl.create_index(
                vector_column_name="vector",
                index_type="HNSW",
            )
        return db.open_table(TABLE_NAME)

    def _get_embedding_model(self):
        """获取 embedding 模型 (延迟加载)"""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

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
        model = self._get_embedding_model()
        table = self._get_table()

        # 创建向量
        text = self._create_text(project)
        vector = model.encode(text).tolist()

        # 生成唯一 ID
        vector_id = str(uuid.uuid4())

        # 添加到 LanceDB
        table.add([{
            "id": vector_id,
            "project_id": project.id,
            "full_name": project.full_name,
            "name": project.name,
            "description": project.description or "",
            "language": project.language or "",
            "topics": project.topics or "",
            "html_url": project.html_url,
            "vector": vector,
        }])

        return vector_id

    async def search(
        self,
        query: str,
        limit: int = 5,
        language: Optional[str] = None,
    ) -> list[dict]:
        """向量搜索"""
        model = self._get_embedding_model()
        table = self._get_table()

        # 创建查询向量
        vector = model.encode(query).tolist()

        # 搜索
        results = table.search(vector, vector_column_name="vector").limit(limit).to_list()

        return [
            {
                "id": r["id"],
                "score": r.get("_score") or (1 - r["_distance"]) if "_distance" in r else None,
                "payload": {k: v for k, v in r.items() if k not in ("id", "vector", "_distance")},
            }
            for r in results
        ]

    async def delete_project(self, project_id: int) -> None:
        """删除项目"""
        table = self._get_table()
        table.delete(f"project_id = {project_id}")

    async def get_point_by_project_id(self, project_id: int) -> Optional[str]:
        """通过项目 ID 获取向量 ID"""
        table = self._get_table()
        results = table.search(
            [0.0] * VECTOR_SIZE,
            vector_column_name="vector",
        ).where(f"project_id = {project_id}").limit(1).to_list()

        if results:
            return results[0]["id"]
        return None

    def clear(self) -> None:
        """清空向量库"""
        db = self._get_db()
        names = db.table_names()
        if TABLE_NAME in names:
            db.drop_table(TABLE_NAME)


def create_vector_store(config: Config) -> VectorStore:
    """创建向量存储实例"""
    return VectorStore(config.vector_db_path)
