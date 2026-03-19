"""MCP 工具定义"""
import asyncio
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import Config, get_config
from .github_client import GitHubClient, get_github_client
from .storage import Storage, project_from_repository
from .vector_store import VectorStore, create_vector_store
from .gitea_client import GiteaClient, create_gitea_client
from .rag import RAG, create_rag


class MCPTools:
    """MCP 工具集"""

    def __init__(self, config: Config):
        self.config = config
        self.storage = Storage(config.db_path)
        self.vector_store = create_vector_store(config)
        self.github_client: Optional[GitHubClient] = None
        self.gitea_client: Optional[GiteaClient] = None
        self.rag: Optional[RAG] = None

    async def get_github_client(self) -> GitHubClient:
        if self.github_client is None:
            self.github_client = await get_github_client(self.config.github_token)
        return self.github_client

    async def get_gitea_client(self) -> GiteaClient:
        if self.gitea_client is None:
            self.gitea_client = await create_gitea_client(
                self.config.gitea.url,
                self.config.gitea.token,
                self.config.gitea.username,
            )
        return self.gitea_client

    def get_rag(self) -> RAG:
        if self.rag is None:
            self.rag = create_rag(self.config, self.vector_store)
        return self.rag

    async def close(self):
        """关闭所有客户端"""
        if self.github_client:
            await self.github_client.close()
        if self.gitea_client:
            await self.gitea_client.close()

    # ===== 工具实现 =====

    async def list_stars(
        self,
        limit: int = 100,
        language: Optional[str] = None,
    ) -> str:
        """获取 GitHub stars 列表"""
        client = await self.get_github_client()
        username = self.config.github_username

        repos = []
        async for repo in client.list_stars(username, per_page=limit):
            repos.append(repo)
            if language and repo.language == language:
                break

        if language:
            repos = [r for r in repos if r.language == language]

        result = f"# GitHub Stars ({len(repos)} 个项目)\n\n"
        for repo in repos:
            stars = "⭐" * min(repo.stargazers_count, 5)
            result += f"- **{repo.full_name}**\n"
            result += f"  - 描述: {repo.description or '无'}\n"
            result += f"  - 语言: {repo.language or '未知'}\n"
            result += f"  - ⭐: {repo.stargazers_count} {stars}\n"
            result += f"  - 链接: {repo.html_url}\n\n"

        return result

    async def sync_stars(self, limit: int = 100) -> str:
        """同步 stars 到本地并向量化"""
        client = await self.get_github_client()
        username = self.config.github_username

        count = 0
        async for repo in client.list_stars(username, per_page=limit):
            # 获取 README
            readme = await client.get_readme(repo.owner_login, repo.name)

            # 转换为存储模型
            project = project_from_repository(repo, readme)

            # 保存到数据库
            saved_project = self.storage.add_project(project)

            # 向量化
            vector_id = await self.vector_store.add_project(saved_project)

            # 更新同步状态
            self.storage.update_sync_status(saved_project.id, vector_id)

            count += 1

        synced_count = self.storage.count_synced_projects()
        total_count = self.storage.count_projects()

        return f"同步完成！\n\n- 本次同步: {count} 个项目\n- 已向量化: {synced_count}/{total_count} 个项目"

    async def search_projects(
        self,
        query: str,
        limit: int = 5,
    ) -> str:
        """向量语义搜索项目"""
        results = await self.vector_store.search(query, limit=limit)

        if not results:
            return f"没有找到与 '{query}' 相关的项目。"

        output = f"# 搜索结果 (查询: {query})\n\n"
        for i, result in enumerate(results, 1):
            payload = result["payload"]
            output += f"## {i}. {payload.get('name')}\n"
            output += f"- 描述: {payload.get('description') or '无'}\n"
            output += f"- 语言: {payload.get('language') or '未知'}\n"
            output += f"- 话题: {payload.get('topics') or '无'}\n"
            output += f"- 相似度: {result['score']:.4f}\n"
            output += f"- 链接: {payload.get('html_url')}\n\n"

        return output

    async def ask_about_projects(self, question: str) -> str:
        """基于 RAG 问答"""
        rag = self.get_rag()
        return await rag.ask(question)

    async def fork_to_gitea(
        self,
        full_name: str,
        use_mirror: bool = True,
    ) -> str:
        """备份项目到 Gitea"""
        # 获取项目信息
        project = self.storage.get_project_by_full_name(full_name)
        if not project:
            return f"错误: 项目 {full_name} 未同步，请先运行 sync_stars"

        if project.backed_up_at:
            return f"项目 {full_name} 已经备份过了\nGitea 链接: {project.gitea_repo_url}"

        gitea_client = await self.get_gitea_client()

        try:
            if use_mirror:
                # 使用镜像方式 (只读)
                result = await gitea_client.mirror_repo(
                    clone_url=project.clone_url,
                    name=project.name,
                    description=project.description or "",
                )
                gitea_repo_url = f"{self.config.gitea.url}/{self.config.gitea.username}/{result.get('name')}"
            else:
                # 克隆并推送
                # 创建空仓库
                result = await gitea_client.create_repo(
                    name=project.name,
                    description=project.description or "",
                )
                gitea_repo_url = result.get("clone_url", "").replace(
                    "git://", f"https://{self.config.gitea.username}:{self.config.gitea.token}@"
                )

                # 克隆并推送
                gitea_client.clone_and_push(project.clone_url, gitea_repo_url)

            # 更新备份状态
            self.storage.update_backup_status(project.id, gitea_repo_url)

            return f"备份成功！\n\n- 项目: {full_name}\n- Gitea 链接: {gitea_repo_url}"

        except Exception as e:
            return f"备份失败: {str(e)}"

    async def list_backed_up(self) -> str:
        """列出已备份项目"""
        projects = self.storage.list_backed_up_projects()

        if not projects:
            return "还没有备份任何项目。"

        result = "# 已备份项目\n\n"
        for project in projects:
            result += f"- [{project.full_name}]({project.gitea_repo_url})\n"
            result += f"  - 备份时间: {project.backed_up_at}\n\n"

        return result

    async def get_project_info(self, full_name: str) -> str:
        """获取项目详情"""
        project = self.storage.get_project_by_full_name(full_name)

        if not project:
            return f"项目 {full_name} 未找到。请先运行 sync_stars 同步数据。"

        topics = project.topics.split(",") if project.topics else []

        result = f"# {project.full_name}\n\n"
        result += f"**描述**: {project.description or '无'}\n\n"
        result += f"**语言**: {project.language or '未知'}\n\n"
        result += f"**话题**: {', '.join(topics) if topics else '无'}\n\n"
        result += f"**⭐ Stars**: {project.stargazers_count}\n\n"
        result += f"**🍴 Forks**: {project.forks_count}\n\n"
        result += f"**🔗 链接**: {project.html_url}\n\n"
        result += f"**🔒 GitHub 克隆**: {project.clone_url}\n\n"

        if project.synced_at:
            result += f"**✅ 已同步**: {project.synced_at}\n\n"
        else:
            result += "**⚠️ 未同步**\n\n"

        if project.backed_up_at:
            result += f"**✅ 已备份到 Gitea**: {project.gitea_repo_url}\n\n"
        else:
            result += "**⚠️ 未备份**\n\n"

        return result


# ===== MCP Server =====

def create_server(tools: MCPTools) -> Server:
    """创建 MCP Server"""
    server = Server("github-star-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_stars",
                description="获取 GitHub stars 列表",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "number",
                            "description": "返回项目数量限制",
                            "default": 100,
                        },
                        "language": {
                            "type": "string",
                            "description": "过滤特定编程语言",
                        },
                    },
                },
            ),
            Tool(
                name="sync_stars",
                description="同步 stars 到本地数据库并向量化",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "number",
                            "description": "同步项目数量限制",
                            "default": 100,
                        },
                    },
                },
            ),
            Tool(
                name="search_projects",
                description="向量语义搜索项目",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询",
                        },
                        "limit": {
                            "type": "number",
                            "description": "返回结果数量",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="ask_about_projects",
                description="基于 RAG 智能问答关于你的 GitHub 项目",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "问题",
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="fork_to_gitea",
                description="备份项目到 Gitea",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "full_name": {
                            "type": "string",
                            "description": "项目完整名称 (owner/repo)",
                        },
                        "use_mirror": {
                            "type": "boolean",
                            "description": "使用镜像模式 (只读)",
                            "default": True,
                        },
                    },
                    "required": ["full_name"],
                },
            ),
            Tool(
                name="list_backed_up",
                description="列出已备份到 Gitea 的项目",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_project_info",
                description="获取项目详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "full_name": {
                            "type": "string",
                            "description": "项目完整名称 (owner/repo)",
                        },
                    },
                    "required": ["full_name"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        # 根据工具名称分发
        if name == "list_stars":
            result = await tools.list_stars(
                limit=arguments.get("limit", 100),
                language=arguments.get("language"),
            )
        elif name == "sync_stars":
            result = await tools.sync_stars(limit=arguments.get("limit", 100))
        elif name == "search_projects":
            result = await tools.search_projects(
                query=arguments["query"],
                limit=arguments.get("limit", 5),
            )
        elif name == "ask_about_projects":
            result = await tools.ask_about_projects(arguments["question"])
        elif name == "fork_to_gitea":
            result = await tools.fork_to_gitea(
                full_name=arguments["full_name"],
                use_mirror=arguments.get("use_mirror", True),
            )
        elif name == "list_backed_up":
            result = await tools.list_backed_up()
        elif name == "get_project_info":
            result = await tools.get_project_info(arguments["full_name"])
        else:
            result = f"未知工具: {name}"

        return [TextContent(type="text", text=result)]

    return server


async def run_server(config: Config):
    """运行 MCP Server (stdio 模式)"""
    tools = MCPTools(config)
    server = create_server(tools)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
