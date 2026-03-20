"""SQLite 存储模块"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select, update

from .groups.models import Group, ProjectGroup  # noqa: F401


class ChatMessage(SQLModel, table=True):
    """聊天消息表"""
    __tablename__ = "chat_messages"

    id: int = Field(primary_key=True)
    role: str = Field(index=True)  # "user" | "assistant" | "system" | "tool"
    content: str = ""
    tool_calls: str = ""  # JSON string
    tool_results: str = ""  # JSON string
    metadata: str = ""  # JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Project(SQLModel, table=True):
    """项目表"""
    __tablename__ = "projects"

    id: int = Field(primary_key=True)
    name: str = Field(index=True)
    full_name: str = Field(unique=True, index=True)
    description: Optional[str] = Field(default=None)
    html_url: str
    clone_url: str
    language: Optional[str] = Field(default=None)
    stargazers_count: int = 0
    forks_count: int = 0
    topics: str = ""  # JSON 字符串
    created_at: str = ""
    updated_at: str = ""
    owner_login: str
    owner_avatar_url: str = ""
    readme_content: Optional[str] = Field(default=None)

    # 同步状态
    synced_at: Optional[datetime] = Field(default=None)
    vector_id: Optional[str] = Field(default=None)

    # Gitea 备份状态
    backed_up_at: Optional[datetime] = Field(default=None)
    gitea_repo_url: Optional[str] = Field(default=None)

    # 关系
    group_associations: list["ProjectGroup"] = Relationship(back_populates="project")


class Storage:
    """SQLite 存储"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        # 确保目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self.engine)

    # ---- Chat Messages ----

    def save_chat_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tool_results: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> ChatMessage:
        """保存聊天消息"""
        import json
        msg = ChatMessage(
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls or [], ensure_ascii=False),
            tool_results=json.dumps(tool_results or [], ensure_ascii=False),
            metadata=json.dumps(metadata or {}, ensure_ascii=False),
        )
        with self.get_session() as session:
            session.add(msg)
            session.commit()
            session.refresh(msg)
            return msg

    def get_chat_messages(self, limit: int = 50) -> list[ChatMessage]:
        """获取最近的聊天消息"""
        import json
        with self.get_session() as session:
            statement = (
                select(ChatMessage)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            return list(reversed(session.exec(statement).all()))

    def clear_chat_messages(self) -> None:
        """清除所有聊天消息"""
        with self.get_session() as session:
            from sqlmodel import delete
            session.execute(delete(ChatMessage))
            session.commit()

    def get_session(self) -> Session:
        """获取数据库会话"""
        return Session(self.engine)

    def add_project(self, project: Project) -> Project:
        """添加或更新项目"""
        with self.get_session() as session:
            # 检查是否存在
            existing = session.get(Project, project.id)
            if existing:
                # 更新
                for key, value in model_to_dict(project).items():
                    if value is not None:
                        setattr(existing, key, value)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                session.add(project)
                session.commit()
                session.refresh(project)
                return project

    def get_project(self, project_id: int) -> Optional[Project]:
        """获取项目"""
        with self.get_session() as session:
            return session.get(Project, project_id)

    def get_project_by_full_name(self, full_name: str) -> Optional[Project]:
        """通过 full_name 获取项目"""
        with self.get_session() as session:
            statement = select(Project).where(Project.full_name == full_name)
            return session.exec(statement).first()

    def list_projects(
        self,
        limit: int = 100,
        offset: int = 0,
        language: Optional[str] = None,
    ) -> list[Project]:
        """列出项目"""
        with self.get_session() as session:
            statement = select(Project).order_by(Project.stargazers_count.desc())
            if language:
                statement = statement.where(Project.language == language)
            statement = statement.offset(offset).limit(limit)
            return list(session.exec(statement).all())

    def list_backed_up_projects(self) -> list[Project]:
        """列出已备份的项目"""
        with self.get_session() as session:
            statement = select(Project).where(Project.backed_up_at.isnot(None))
            return list(session.exec(statement).all())

    def update_sync_status(self, project_id: int, vector_id: str) -> None:
        """更新同步状态"""
        with self.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                project.synced_at = datetime.utcnow()
                project.vector_id = vector_id
                session.add(project)
                session.commit()

    def update_backup_status(
        self,
        project_id: int,
        gitea_repo_url: str,
    ) -> None:
        """更新备份状态"""
        with self.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                project.backed_up_at = datetime.utcnow()
                project.gitea_repo_url = gitea_repo_url
                session.add(project)
                session.commit()

    def count_projects(self) -> int:
        """统计项目数量"""
        with self.get_session() as session:
            return len(list(session.exec(select(Project))))

    def count_synced_projects(self) -> int:
        """统计已同步项目数量"""
        with self.get_session() as session:
            statement = select(Project).where(Project.synced_at.isnot(None))
            return len(list(session.exec(statement).all()))

    def count_backed_up_projects(self) -> int:
        """统计已备份项目数量"""
        with self.get_session() as session:
            statement = select(Project).where(Project.backed_up_at.isnot(None))
            return len(list(session.exec(statement).all()))

    def update_readme(self, project_id: int, readme_content: str) -> None:
        """更新项目的 README 内容"""
        with self.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                project.readme_content = readme_content
                session.add(project)
                session.commit()

    def mark_data_synced(self, project_id: int) -> None:
        """标记项目数据已同步"""
        with self.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                project.synced_at = datetime.utcnow()
                session.add(project)
                session.commit()

    def count_vectorized_projects(self) -> int:
        """统计已向量化的项目数量"""
        with self.get_session() as session:
            statement = select(Project).where(Project.vector_id.isnot(None))
            return len(list(session.exec(statement).all()))

    def count_readme_projects(self) -> int:
        """统计已同步 README 的项目数量"""
        with self.get_session() as session:
            statement = select(Project).where(Project.readme_content.isnot(None))
            return len(list(session.exec(statement).all()))

    def list_unvectorized_projects(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """列出未向量化的项目"""
        with self.get_session() as session:
            statement = (
                select(Project)
                .where(Project.vector_id.is_(None))
                .where(Project.readme_content.isnot(None))
                .offset(offset)
                .limit(limit)
            )
            return list(session.exec(statement).all())

    def mark_vectorized(self, project_id: int, vector_id: str) -> None:
        """标记项目已向量化"""
        with self.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                project.vector_id = vector_id
                session.add(project)
                session.commit()

    def reset_vectorized_marks(self) -> None:
        """重置所有项目的 vector_id（用于重建向量库）"""
        with self.get_session() as session:
            session.execute(
                update(Project).where(Project.vector_id.isnot(None)).values(vector_id=None)
            )
            session.commit()


def model_to_dict(model: Project) -> dict:
    """将 Project 模型转换为字典"""
    result = {}
    for key, value in model.model_dump().items():
        if key == "topics" and isinstance(value, list):
            result[key] = ",".join(value)
        else:
            result[key] = value
    return result


def project_from_repository(repo, readme_content: Optional[str] = None) -> Project:
    """从 Repository 创建 Project"""
    return Project(
        id=repo.id,
        name=repo.name,
        full_name=repo.full_name,
        description=repo.description,
        html_url=repo.html_url,
        clone_url=repo.clone_url,
        language=repo.language,
        stargazers_count=repo.stargazers_count,
        forks_count=repo.forks_count,
        topics=",".join(repo.topics) if repo.topics else "",
        created_at=repo.created_at,
        updated_at=repo.updated_at,
        owner_login=repo.owner_login,
        owner_avatar_url=repo.owner_avatar_url,
        readme_content=readme_content,
    )
