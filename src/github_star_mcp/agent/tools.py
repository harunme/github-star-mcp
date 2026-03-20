"""Agent Tools 实现"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass

from pydantic import BaseModel

from ..config import Config
from ..storage import Storage
from ..vector_store import VectorStore
from ..groups import GroupService
from ..health import HealthChecker
from .prompts import SEARCH_PROMPT, GROUP_PROMPT, HEALTH_CHECK_PROMPT, TRENDING_PROMPT

logger = logging.getLogger(__name__)


# ===== Tool 输入/输出 Schema =====

class SearchProjectsInput(BaseModel):
    query: str
    limit: int = 5


class ListStarsInput(BaseModel):
    limit: int = 100
    language: Optional[str] = None


class AutoGroupProjectsInput(BaseModel):
    group_name: str
    criteria: Optional[str] = None


class CheckRepoHealthInput(BaseModel):
    project_id: Optional[int] = None
    full_name: Optional[str] = None


class DiscoverTrendingInput(BaseModel):
    language: Optional[str] = None
    since: str = "daily"
    limit: int = 10


class AnalyzeSyncStatusInput(BaseModel):
    pass


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    tool_name: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AgentTools:
    """Agent 工具集"""

    def __init__(
        self,
        config: Config,
        storage: Storage,
        vector_store: VectorStore,
    ):
        self.config = config
        self.storage = storage
        self.vector_store = vector_store
        self.group_service = GroupService(storage.get_session())
        self.health_checker = HealthChecker(storage)

    async def search_projects(
        self,
        query: str,
        limit: int = 5,
    ) -> ToolResult:
        """语义搜索项目"""
        try:
            results = await self.vector_store.search(query, limit=limit)

            if not results:
                return ToolResult(
                    success=True,
                    content=f"没有找到与 '{query}' 相关的项目。",
                    tool_name="search_projects",
                )

            output = f"## 搜索结果 (查询: {query})\n\n"
            for i, result in enumerate(results, 1):
                payload = result["payload"]
                score = result.get("score", 0)
                output += f"**{i}. {payload.get('name')}** ({payload.get('full_name')})\n"
                output += f"   - {payload.get('description') or '无描述'}\n"
                output += f"   - 语言: {payload.get('language') or '未知'}\n"
                output += f"   - 相似度: {score:.2%}\n"
                output += f"   - 链接: {payload.get('html_url')}\n\n"

            return ToolResult(
                success=True,
                content=output,
                tool_name="search_projects",
                metadata={"count": len(results), "query": query},
            )
        except Exception as e:
            logger.exception("搜索失败: %s", e)
            return ToolResult(
                success=False,
                content=f"搜索失败: {str(e)}",
                tool_name="search_projects",
            )

    async def list_stars(
        self,
        limit: int = 100,
        language: Optional[str] = None,
    ) -> ToolResult:
        """列出项目"""
        try:
            projects = self.storage.list_projects(limit=limit, language=language)

            if not projects:
                return ToolResult(
                    success=True,
                    content="还没有同步任何项目。请先运行同步。",
                    tool_name="list_stars",
                )

            output = f"## GitHub Stars ({len(projects)} 个项目)\n\n"
            for repo in projects[:20]:  # 最多显示 20 个
                output += f"- **{repo.full_name}**\n"
                output += f"  - {repo.description or '无描述'}\n"
                output += f"  - 语言: {repo.language or '未知'} | ⭐ {repo.stargazers_count}\n"

            if len(projects) > 20:
                output += f"\n_... 还有 {len(projects) - 20} 个项目_"

            return ToolResult(
                success=True,
                content=output,
                tool_name="list_stars",
                metadata={"count": len(projects)},
            )
        except Exception as e:
            logger.exception("列出项目失败: %s", e)
            return ToolResult(
                success=False,
                content=f"列出项目失败: {str(e)}",
                tool_name="list_stars",
            )

    async def auto_group_projects(
        self,
        group_name: str,
        criteria: Optional[str] = None,
    ) -> ToolResult:
        """自动分组项目"""
        try:
            # 获取所有项目
            projects = self.storage.list_projects(limit=1000)

            if not projects:
                return ToolResult(
                    success=True,
                    content="没有可分组的项目。",
                    tool_name="auto_group_projects",
                )

            # 按语言分组
            groups: Dict[str, List] = {}
            for p in projects:
                lang = p.language or "Unknown"
                if lang not in groups:
                    groups[lang] = []
                groups[lang].append(p)

            # 创建分组
            created_groups = []
            for lang, lang_projects in groups.items():
                group = self.group_service.get_group_by_name(lang)
                if not group:
                    group = self.group_service.create_group(
                        name=lang,
                        description=f"编程语言: {lang}",
                        is_auto=True,
                    )
                    created_groups.append(group.name)

                # 添加项目到分组
                for p in lang_projects:
                    self.group_service.add_project_to_group(
                        project_id=p.id,
                        group_id=group.id,
                        confidence=1.0,
                    )

            output = f"## 自动分组完成\n\n"
            output += f"创建了 {len(created_groups)} 个分组：\n"
            for name in created_groups:
                count = len([g for g in groups.get(name, [])])
                output += f"- **{name}**: {count} 个项目\n"

            return ToolResult(
                success=True,
                content=output,
                tool_name="auto_group_projects",
                metadata={"created_groups": len(created_groups)},
            )
        except Exception as e:
            logger.exception("自动分组失败: %s", e)
            return ToolResult(
                success=False,
                content=f"自动分组失败: {str(e)}",
                tool_name="auto_group_projects",
            )

    async def check_repo_health(
        self,
        project_id: Optional[int] = None,
        full_name: Optional[str] = None,
    ) -> ToolResult:
        """检测仓库健康状况"""
        try:
            if project_id:
                project = self.storage.get_project(project_id)
            elif full_name:
                project = self.storage.get_project_by_full_name(full_name)
            else:
                # 检测所有不健康项目
                reports = self.health_checker.get_unhealthy_projects(threshold=50)

                if not reports:
                    return ToolResult(
                        success=True,
                        content="所有项目都很健康！",
                        tool_name="check_repo_health",
                    )

                output = f"## 健康检测结果\n\n"
                output += f"发现 {len(reports)} 个可能需要关注的仓库：\n\n"

                for report in reports[:10]:
                    output += f"### {report.full_name} (健康分: {report.score}/100)\n"
                    output += f"问题：{', '.join(i.value for i in report.issues)}\n\n"

                return ToolResult(
                    success=True,
                    content=output,
                    tool_name="check_repo_health",
                    metadata={"unhealthy_count": len(reports)},
                )

            if not project:
                return ToolResult(
                    success=False,
                    content=f"项目未找到: {project_id or full_name}",
                    tool_name="check_repo_health",
                )

            report = await self.health_checker.check_project(project)

            output = f"## {project.full_name} 健康报告\n\n"
            output += f"**健康分**: {report.score}/100\n\n"
            output += f"**问题**:\n"
            if report.issues:
                for issue in report.issues:
                    output += f"- {issue.value}\n"
            else:
                output += "- 无问题\n"

            if report.recommendations:
                output += f"\n**建议**:\n"
                for rec in report.recommendations:
                    output += f"- {rec}\n"

            return ToolResult(
                success=True,
                content=output,
                tool_name="check_repo_health",
                metadata={"score": report.score, "issues": [i.value for i in report.issues]},
            )
        except Exception as e:
            logger.exception("健康检测失败: %s", e)
            return ToolResult(
                success=False,
                content=f"健康检测失败: {str(e)}",
                tool_name="check_repo_health",
            )

    async def discover_trending(
        self,
        language: Optional[str] = None,
        since: str = "daily",
        limit: int = 10,
    ) -> ToolResult:
        """发现 GitHub Trending"""
        try:
            # TODO: 实现 GitHub Trending API 调用
            # 目前返回提示
            output = f"## GitHub Trending 发现\n\n"
            output += f"语言: {language or '全部'}\n"
            output += f"时间范围: {since}\n\n"
            output += "提示: Trending 功能需要配置 GitHub API，稍后可用。\n"

            return ToolResult(
                success=True,
                content=output,
                tool_name="discover_trending",
                metadata={"language": language, "since": since},
            )
        except Exception as e:
            logger.exception("发现 Trending 失败: %s", e)
            return ToolResult(
                success=False,
                content=f"发现 Trending 失败: {str(e)}",
                tool_name="discover_trending",
            )

    async def analyze_sync_status(self) -> ToolResult:
        """分析同步状态"""
        try:
            total = self.storage.count_projects()
            synced = self.storage.count_synced_projects()
            vectorized = self.storage.count_vectorized_projects()
            readme_count = self.storage.count_readme_projects()
            groups_count = len(self.group_service.list_groups())

            output = f"## 同步状态分析\n\n"
            output += f"- 总项目数: {total}\n"
            output += f"- 已同步: {synced}\n"
            output += f"- 已获取 README: {readme_count}\n"
            output += f"- 已向量化: {vectorized}\n"
            output += f"- 分组数: {groups_count}\n\n"

            # 状态评估
            if total == 0:
                output += "**状态**: 需要同步\n"
                output += "运行 `sync_stars` 开始同步你的 GitHub Stars。"
            elif synced == total and vectorized == total:
                output += "**状态**: 全部完成\n"
                output += "你的 Stars 数据已完整同步和向量化。"
            elif synced == total and vectorized < total:
                output += "**状态**: 待向量化\n"
                output += f"还有 {total - vectorized} 个项目需要向量化。"
            else:
                output += "**状态**: 同步中\n"
                output += f"已同步 {synced}/{total} 个项目。"

            return ToolResult(
                success=True,
                content=output,
                tool_name="analyze_sync_status",
                metadata={
                    "total": total,
                    "synced": synced,
                    "vectorized": vectorized,
                },
            )
        except Exception as e:
            logger.exception("状态分析失败: %s", e)
            return ToolResult(
                success=False,
                content=f"状态分析失败: {str(e)}",
                tool_name="analyze_sync_status",
            )

    def get_tool_definitions(self) -> List[Dict]:
        """获取工具定义（用于 Agent）"""
        return [
            {
                "name": "search_projects",
                "description": "语义搜索用户 Stars 项目",
                "input_schema": SearchProjectsInput.model_json_schema(),
            },
            {
                "name": "list_stars",
                "description": "列出用户的 Stars 项目",
                "input_schema": ListStarsInput.model_json_schema(),
            },
            {
                "name": "auto_group_projects",
                "description": "使用 AI 自动分组项目",
                "input_schema": AutoGroupProjectsInput.model_json_schema(),
            },
            {
                "name": "check_repo_health",
                "description": "检测仓库健康状况",
                "input_schema": CheckRepoHealthInput.model_json_schema(),
            },
            {
                "name": "discover_trending",
                "description": "发现 GitHub Trending 项目",
                "input_schema": DiscoverTrendingInput.model_json_schema(),
            },
            {
                "name": "analyze_sync_status",
                "description": "分析同步状态",
                "input_schema": AnalyzeSyncStatusInput.model_json_schema(),
            },
        ]
