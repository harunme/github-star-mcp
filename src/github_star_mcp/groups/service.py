"""分组服务"""
from datetime import datetime
from typing import Optional, List

from sqlmodel import Session, SQLModel, select

from .models import Group, ProjectGroup


class GroupService:
    """分组服务"""

    def __init__(self, session: Session):
        self.session = session

    # ===== Group CRUD =====

    def create_group(
        self,
        name: str,
        description: Optional[str] = None,
        color: str = "#6366f1",
        icon: Optional[str] = None,
        is_auto: bool = False,
    ) -> Group:
        """创建分组"""
        group = Group(
            name=name,
            description=description,
            color=color,
            icon=icon,
            is_auto=is_auto,
        )
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def get_group(self, group_id: int) -> Optional[Group]:
        """获取分组"""
        return self.session.get(Group, group_id)

    def get_group_by_name(self, name: str) -> Optional[Group]:
        """通过名称获取分组"""
        statement = select(Group).where(Group.name == name)
        return self.session.exec(statement).first()

    def list_groups(self) -> List[Group]:
        """列出所有分组"""
        statement = select(Group).order_by(Group.created_at.desc())
        return list(self.session.exec(statement).all())

    def update_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Optional[Group]:
        """更新分组"""
        group = self.session.get(Group, group_id)
        if not group:
            return None

        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        if color is not None:
            group.color = color
        if icon is not None:
            group.icon = icon

        group.updated_at = datetime.utcnow()
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def delete_group(self, group_id: int) -> bool:
        """删除分组"""
        group = self.session.get(Group, group_id)
        if not group:
            return False

        # 删除关联
        statement = select(ProjectGroup).where(ProjectGroup.group_id == group_id)
        for pg in self.session.exec(statement).all():
            self.session.delete(pg)

        self.session.delete(group)
        self.session.commit()
        return True

    def count_projects_in_group(self, group_id: int) -> int:
        """统计分组中的项目数量"""
        statement = select(ProjectGroup).where(ProjectGroup.group_id == group_id)
        return len(list(self.session.exec(statement).all()))

    # ===== ProjectGroup 操作 =====

    def add_project_to_group(
        self,
        project_id: int,
        group_id: int,
        confidence: float = 1.0,
        is_primary: bool = False,
    ) -> ProjectGroup:
        """添加项目到分组"""
        # 检查是否已存在
        statement = select(ProjectGroup).where(
            ProjectGroup.project_id == project_id,
            ProjectGroup.group_id == group_id,
        )
        existing = self.session.exec(statement).first()

        if existing:
            existing.confidence = confidence
            existing.is_primary = is_primary
            self.session.add(existing)
            self.session.commit()
            return existing

        pg = ProjectGroup(
            project_id=project_id,
            group_id=group_id,
            confidence=confidence,
            is_primary=is_primary,
        )
        self.session.add(pg)
        self.session.commit()
        self.session.refresh(pg)
        return pg

    def remove_project_from_group(self, project_id: int, group_id: int) -> bool:
        """从分组移除项目"""
        statement = select(ProjectGroup).where(
            ProjectGroup.project_id == project_id,
            ProjectGroup.group_id == group_id,
        )
        pg = self.session.exec(statement).first()
        if not pg:
            return False

        self.session.delete(pg)
        self.session.commit()
        return True

    def get_project_groups(self, project_id: int) -> List[ProjectGroup]:
        """获取项目所属的分组"""
        statement = select(ProjectGroup).where(ProjectGroup.project_id == project_id)
        return list(self.session.exec(statement).all())

    def get_group_projects(
        self,
        group_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ProjectGroup]:
        """获取分组中的项目"""
        statement = (
            select(ProjectGroup)
            .where(ProjectGroup.group_id == group_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def get_groups_for_project(self, project_id: int) -> List[Group]:
        """获取项目所属的分组列表"""
        statement = (
            select(Group)
            .join(ProjectGroup, Group.id == ProjectGroup.group_id)
            .where(ProjectGroup.project_id == project_id)
        )
        return list(self.session.exec(statement).all())

    def batch_add_projects_to_group(
        self,
        project_ids: List[int],
        group_id: int,
        is_primary: bool = False,
    ) -> int:
        """批量添加项目到分组"""
        count = 0
        for project_id in project_ids:
            try:
                self.add_project_to_group(
                    project_id=project_id,
                    group_id=group_id,
                    is_primary=is_primary,
                )
                count += 1
            except Exception:
                continue
        return count

    def move_project_to_group(
        self,
        project_id: int,
        from_group_id: int,
        to_group_id: int,
    ) -> bool:
        """移动项目到另一个分组"""
        # 从原分组移除
        self.remove_project_from_group(project_id, from_group_id)
        # 添加到新分组
        self.add_project_to_group(project_id, to_group_id)
        return True

    def set_primary_group(self, project_id: int, group_id: int) -> bool:
        """设置项目的主分组"""
        # 取消其他主分组
        statement = select(ProjectGroup).where(ProjectGroup.project_id == project_id)
        for pg in self.session.exec(statement).all():
            pg.is_primary = False
            self.session.add(pg)

        # 设置新的主分组
        statement = select(ProjectGroup).where(
            ProjectGroup.project_id == project_id,
            ProjectGroup.group_id == group_id,
        )
        pg = self.session.exec(statement).first()
        if pg:
            pg.is_primary = True
            self.session.add(pg)
            self.session.commit()
            return True
        return False
