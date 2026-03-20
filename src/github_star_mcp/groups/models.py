"""分组数据模型"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from ..storage import Project


class Group(SQLModel, table=True):
    """分组表"""
    __tablename__ = "groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    color: str = Field(default="#6366f1")
    icon: Optional[str] = Field(default=None)
    is_auto: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # 关系
    projects: List["ProjectGroup"] = Relationship(back_populates="group")


class ProjectGroup(SQLModel, table=True):
    """项目-分组关联表"""
    __tablename__ = "project_groups"

    project_id: int = Field(foreign_key="projects.id", primary_key=True)
    group_id: int = Field(foreign_key="groups.id", primary_key=True)
    confidence: float = Field(default=1.0)
    is_primary: bool = Field(default=False)
    added_at: datetime = Field(default_factory=datetime.utcnow)

    # 关系
    project: Optional["Project"] = Relationship(back_populates="group_associations")
    group: Optional[Group] = Relationship(back_populates="projects")
