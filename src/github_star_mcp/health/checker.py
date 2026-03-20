"""仓库健康检测模块"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Session, SQLModel, select

from ..storage import Project, Storage


class HealthIssue(str, Enum):
    """健康问题类型"""
    STALE_REPO = "stale_repo"  # 长期未更新
    HIGH_ISSUE_COUNT = "high_issue_count"  # Issue 积压
    MISSING_README = "missing_readme"  # 文档缺失
    ARCHIVED = "archived"  # 已归档
    NO_TOPICS = "no_topics"  # 无话题标签
    LOW_STARS = "low_stars"  # Star 数很低


@dataclass
class HealthReport:
    """健康报告"""
    project_id: int
    project_name: str
    full_name: str
    score: float  # 0-100, 100 为最健康
    issues: List[HealthIssue]
    recommendations: List[str]
    details: dict

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "full_name": self.full_name,
            "score": self.score,
            "issues": [i.value for i in self.issues],
            "recommendations": self.recommendations,
            "details": self.details,
        }


@dataclass
class BatchHealthReport:
    """批量健康报告"""
    reports: List[HealthReport]
    total_count: int
    healthy_count: int
    unhealthy_count: int
    average_score: float


class HealthChecker:
    """健康检测器"""

    # 配置
    STALE_YEARS = 2  # 超过 2 年未更新视为过时
    HIGH_ISSUE_THRESHOLD = 100  # Issue 数量超过 100 视为积压
    LOW_STARS_THRESHOLD = 10  # Star 数低于 10 视为冷门

    def __init__(self, storage: Storage):
        self.storage = storage

    async def check_project(self, project: Project) -> HealthReport:
        """检测单个项目"""
        issues = []
        recommendations = []
        details = {}

        # 1. 检查更新时间
        if project.updated_at:
            try:
                updated_date = datetime.fromisoformat(project.updated_at.replace("Z", "+00:00"))
                if isinstance(updated_date, datetime) and updated_date.tzinfo:
                    updated_date = updated_date.replace(tzinfo=None)
                age_years = (datetime.utcnow() - updated_date).days / 365
                details["age_years"] = round(age_years, 1)

                if age_years > self.STALE_YEARS:
                    issues.append(HealthIssue.STALE_REPO)
                    recommendations.append(f"项目已 {age_years:.1f} 年未更新，考虑 unstar")
            except Exception:
                pass

        # 2. 检查 README
        if not project.readme_content:
            issues.append(HealthIssue.MISSING_README)
            recommendations.append("项目缺少 README 文档")

        # 3. 检查话题标签
        if not project.topics or len(project.topics.split(",")) < 2:
            issues.append(HealthIssue.NO_TOPICS)
            recommendations.append("项目缺少话题标签，难以分类")

        # 4. 检查 Star 数（参考指标）
        if project.stargazers_count < self.LOW_STARS_THRESHOLD:
            issues.append(HealthIssue.LOW_STARS)
            details["low_stars"] = True

        # 计算健康分数
        score = 100 - (len(issues) * 20)
        if score < 0:
            score = 0

        return HealthReport(
            project_id=project.id,
            project_name=project.name,
            full_name=project.full_name,
            score=score,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    async def check_all_projects(
        self,
        limit: int = 100,
        offset: int = 0,
        min_score: Optional[float] = None,
    ) -> BatchHealthReport:
        """批量检测所有项目"""
        projects = self.storage.list_projects(limit=limit, offset=offset)

        reports = []
        for project in projects:
            report = await self.check_project(project)
            if min_score is None or report.score < min_score:
                reports.append(report)

        # 统计
        healthy = sum(1 for r in reports if r.score >= 80)
        unhealthy = sum(1 for r in reports if r.score < 50)
        avg_score = sum(r.score for r in reports) / len(reports) if reports else 0

        return BatchHealthReport(
            reports=reports,
            total_count=len(reports),
            healthy_count=healthy,
            unhealthy_count=unhealthy,
            average_score=round(avg_score, 1),
        )

    async def find_health_issues(
        self,
        issue_types: Optional[List[HealthIssue]] = None,
        min_age_years: Optional[float] = None,
    ) -> List[HealthReport]:
        """查找特定健康问题的项目"""
        projects = self.storage.list_projects(limit=1000)

        results = []
        for project in projects:
            report = await self.check_project(project)

            # 过滤条件
            if issue_types and not any(i in report.issues for i in issue_types):
                continue

            if min_age_years:
                age = report.details.get("age_years", 0)
                if age < min_age_years:
                    continue

            if report.issues:
                results.append(report)

        # 按分数排序
        results.sort(key=lambda r: r.score)
        return results

    def get_unhealthy_projects(self, threshold: float = 50) -> List[HealthReport]:
        """获取不健康项目的简单同步版本"""
        projects = self.storage.list_projects(limit=1000)

        results = []
        for project in projects:
            # 简单检查
            issues = []

            if project.updated_at:
                try:
                    updated_date = datetime.fromisoformat(project.updated_at.replace("Z", "+00:00"))
                    if isinstance(updated_date, datetime) and updated_date.tzinfo:
                        updated_date = updated_date.replace(tzinfo=None)
                    age_years = (datetime.utcnow() - updated_date).days / 365
                    if age_years > self.STALE_YEARS:
                        issues.append(HealthIssue.STALE_REPO)
                except Exception:
                    pass

            if not project.readme_content:
                issues.append(HealthIssue.MISSING_README)

            if not project.topics:
                issues.append(HealthIssue.NO_TOPICS)

            if issues:
                score = 100 - (len(issues) * 20)
                results.append(HealthReport(
                    project_id=project.id,
                    project_name=project.name,
                    full_name=project.full_name,
                    score=max(0, score),
                    issues=issues,
                    recommendations=[],
                    details={"age_years": age_years} if age_years > self.STALE_YEARS else {},
                ))

        return [r for r in results if r.score < threshold]
