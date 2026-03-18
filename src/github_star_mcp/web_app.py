"""Web 引导页面 + MCP HTTP 代理"""
import asyncio
import contextlib
from enum import Enum
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from .config import Config
from .storage import Storage
from .tools import MCPTools, create_server


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


# 全局同步状态管理
_sync_state: dict = {
    "status": SyncStatus.PENDING,
    "progress": 0,
    "total": 0,
    "current": 0,
    "error": "",
}
_sync_task: Optional[asyncio.Task] = None


def get_templates_dir() -> Path:
    """获取模板目录"""
    return Path(__file__).parent / "templates"


def get_jinja_env() -> Environment:
    """获取 Jinja 环境"""
    templates_dir = get_templates_dir()
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def get_storage(config: Config) -> Storage:
    """获取存储实例"""
    return Storage(config.db_path)


def get_sync_state() -> dict:
    """获取同步状态"""
    return _sync_state.copy()


def set_sync_state(**kwargs) -> None:
    """设置同步状态"""
    _sync_state.update(kwargs)


def check_sync_required() -> bool:
    """检查是否需要同步"""
    return _sync_state.get("status") in (SyncStatus.PENDING, SyncStatus.FAILED)


# ===== 同步任务 =====


async def _run_sync_task(config: Config) -> None:
    """执行后台同步任务"""
    try:
        set_sync_state(
            status=SyncStatus.SYNCING,
            error="",
            current=0,
        )

        tools = MCPTools(config)
        client = await tools.get_github_client()
        username = config.github_username

        # 先统计总数
        total = 0
        async for _ in client.list_stars(username, per_page=100):
            total += 1
        set_sync_state(total=total, progress=0)

        # 重置迭代器
        count = 0
        async for repo in client.list_stars(username, per_page=100):
            # 获取 README
            readme = await client.get_readme(repo.owner_login, repo.name)

            # 转换为存储模型
            from .storage import project_from_repository
            project = project_from_repository(repo, readme)

            # 保存到数据库
            storage = get_storage(config)
            saved_project = storage.add_project(project)

            # 向量化
            vector_store = tools.vector_store
            vector_id = await vector_store.add_project(saved_project)

            # 更新同步状态
            storage.update_sync_status(saved_project.id, vector_id)

            count += 1
            set_sync_state(current=count, progress=int(count / max(total, 1) * 100))

        # 关闭客户端
        await tools.close()

        set_sync_state(
            status=SyncStatus.COMPLETED,
            progress=100,
            current=count,
            error="",
        )
    except Exception as e:
        set_sync_state(
            status=SyncStatus.FAILED,
            error=str(e),
        )


def start_sync_task(config: Config) -> bool:
    """启动同步任务（如果未在运行）"""
    global _sync_task

    if _sync_state.get("status") == SyncStatus.SYNCING:
        return False

    # 重置状态
    set_sync_state(
        status=SyncStatus.PENDING,
        progress=0,
        total=0,
        current=0,
        error="",
    )

    _sync_task = asyncio.create_task(_run_sync_task(config))
    return True


def cancel_sync_task() -> bool:
    """取消同步任务"""
    global _sync_task

    if _sync_state.get("status") != SyncStatus.SYNCING:
        return False

    if _sync_task:
        _sync_task.cancel()
        _sync_task = None

    set_sync_state(
        status=SyncStatus.PENDING,
        progress=0,
        error="已取消",
    )
    return True


def reset_sync_task() -> bool:
    """重置同步状态"""
    global _sync_task

    if _sync_task:
        _sync_task.cancel()
        _sync_task = None

    set_sync_state(
        status=SyncStatus.PENDING,
        progress=0,
        total=0,
        current=0,
        error="",
    )
    return True


# ===== 路由处理器 =====


async def index_page(request: Request) -> HTMLResponse:
    """渲染引导页面"""
    config: Config = request.app.state.config
    storage = get_storage(config)

    state = get_sync_state()
    total_projects = storage.count_projects()
    synced_projects = storage.count_synced_projects()

    env = get_jinja_env()
    template = env.get_template("index.html")

    html = template.render(
        status=state["status"],
        progress=state["progress"],
        current=state["current"],
        total=state["total"],
        error=state["error"],
        username=config.github_username,
        total_projects=total_projects,
        synced_projects=synced_projects,
        require_sync=config.server.require_sync,
    )

    return HTMLResponse(html)


async def api_sync_start(request: Request) -> JSONResponse:
    """开始同步"""
    config: Config = request.app.state.config

    if not start_sync_task(config):
        return JSONResponse({"error": "同步任务已在运行"}, status_code=400)

    return JSONResponse({"message": "同步已启动", "status": get_sync_state()})


async def api_sync_status(request: Request) -> JSONResponse:
    """查询同步状态"""
    config: Config = request.app.state.config
    storage = get_storage(config)

    state = get_sync_state()
    state["total_projects"] = storage.count_projects()
    state["synced_projects"] = storage.count_synced_projects()

    return JSONResponse(state)


async def api_sync_cancel(request: Request) -> JSONResponse:
    """取消同步"""
    if not cancel_sync_task():
        return JSONResponse({"error": "没有正在运行的同步任务"}, status_code=400)

    return JSONResponse({"message": "同步已取消", "status": get_sync_state()})


async def api_sync_reset(request: Request) -> JSONResponse:
    """重置同步状态"""
    config: Config = request.app.state.config

    reset_sync_task()

    # 清空数据库和向量库
    storage = get_storage(config)
    from .vector_store import COLLECTION_NAME
    from qdrant_client import QdrantClient

    # 清空 SQLite
    from .storage import Project
    with storage.get_session() as session:
        from sqlmodel import delete
        session.execute(delete(Project))
        session.commit()

    # 清空 Qdrant
    client = QdrantClient(host=config.qdrant.host, port=config.qdrant.port)
    try:
        client.delete_collection(collection_name=COLLECTION_NAME)
    except Exception:
        pass  # collection 可能不存在

    return JSONResponse({"message": "同步状态已重置", "status": get_sync_state()})


def create_web_app(config: Config, host: str = "0.0.0.0", port: int = 8080) -> Starlette:
    """创建 Web 应用"""

    # MCP Server 设置
    tools = MCPTools(config)
    server = create_server(tools)
    session_manager = StreamableHTTPSessionManager(
        app=server,
        stateless=False,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        # 初始化时检查是否已有数据
        storage = get_storage(config)
        synced = storage.count_synced_projects()
        if synced > 0:
            set_sync_state(status=SyncStatus.COMPLETED)
        yield
        # 清理
        if _sync_task:
            _sync_task.cancel()
        await tools.close()

    async def mcp_handler(request: Request):
        """MCP 端点处理器"""
        # 检查同步状态
        if config.server.require_sync and check_sync_required():
            return JSONResponse(
                {
                    "error": "Sync Required",
                    "message": "请先完成 GitHub Stars 同步",
                    "status": get_sync_state()["status"],
                },
                status_code=403,
            )

        return await session_manager.handle_request(request.scope, request.receive)

    app = Starlette(
        routes=[
            Route("/", index_page),
            Route("/mcp", mcp_handler, methods=["GET", "POST", "DELETE"]),
            Route("/api/sync/start", api_sync_start, methods=["POST"]),
            Route("/api/sync/status", api_sync_status, methods=["GET"]),
            Route("/api/sync/cancel", api_sync_cancel, methods=["POST"]),
            Route("/api/sync/reset", api_sync_reset, methods=["POST"]),
        ],
        lifespan=lifespan,
    )

    app.state.config = config
    return app


def run_web_server(
    config: Config,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """运行 Web 服务器（同步入口）"""
    host = host or config.server.host
    port = port or config.server.port

    app = create_web_app(config, host, port)
    uvicorn.run(app, host=host, port=port, loop="asyncio")


# ===== MCP HTTP Server (独立模式) =====


async def run_http_server(
    config: Config,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """HTTP 模式运行 MCP Server（无引导页面）"""
    tools = MCPTools(config)
    server = create_server(tools)
    session_manager = StreamableHTTPSessionManager(
        app=server,
        stateless=False,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    starlette_app = Starlette(
        routes=[Mount("/", app=session_manager.handle_request)],
        lifespan=lifespan,
    )

    config_uvicorn = uvicorn.Config(starlette_app, host=host, port=port)
    server_uvicorn = uvicorn.Server(config_uvicorn)
    await server_uvicorn.serve()
