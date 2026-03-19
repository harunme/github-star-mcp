"""Web 引导页面 + MCP HTTP 代理"""
import asyncio
import contextlib
import json
from enum import Enum
from pathlib import Path
from typing import Optional

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

from .config import Config
from .storage import Storage
from .tools import MCPTools, create_server


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    LOADING_README = "loading_readme"
    COMPLETED = "completed"
    FAILED = "failed"


class VectorizeStatus(str, Enum):
    """向量化状态"""
    PENDING = "pending"
    VECTORIZING = "vectorizing"
    COMPLETED = "completed"
    FAILED = "failed"


# 全局同步状态管理
_sync_state: dict = {
    "status": SyncStatus.PENDING,
    "error": "",
    "synced_projects": 0,
    "readme_total": 0,
    "readme_current": 0,
    "readme_progress": 0,
}
_sync_task: Optional[asyncio.Task] = None

_vector_state: dict = {
    "status": VectorizeStatus.PENDING,
    "progress": 0,
    "total": 0,
    "current": 0,
    "error": "",
}
_vector_task: Optional[asyncio.Task] = None


def get_storage(config: Config) -> Storage:
    """获取存储实例"""
    return Storage(config.db_path)


def get_sync_state() -> dict:
    """获取同步状态"""
    return _sync_state.copy()


def set_sync_state(**kwargs) -> None:
    """设置同步状态"""
    _sync_state.update(kwargs)


def get_vector_state() -> dict:
    """获取向量化状态"""
    return _vector_state.copy()


def set_vector_state(**kwargs) -> None:
    """设置向量化状态"""
    _vector_state.update(kwargs)


def check_sync_required() -> bool:
    """检查是否需要同步"""
    return _sync_state.get("status") in (
        SyncStatus.PENDING,
        SyncStatus.FAILED,
        SyncStatus.LOADING_README,
    )


def check_vectorize_required() -> bool:
    """检查是否需要向量化"""
    return _vector_state.get("status") in (VectorizeStatus.PENDING, VectorizeStatus.FAILED)


# ===== 同步任务 =====


async def _run_sync_task(config: Config) -> None:
    """执行后台同步任务（两阶段：仓库同步 + README 加载）"""
    try:
        set_sync_state(
            status=SyncStatus.SYNCING,
            error="",
            synced_projects=0,
            readme_total=0,
            readme_current=0,
            readme_progress=0,
        )

        tools = MCPTools(config)
        client = await tools.get_github_client()
        username = config.github_username
        storage = get_storage(config)

        # Phase 1: 同步仓库元数据（无进度，GitHub starred API 无 total）
        count = 0
        async for repo in client.list_stars(username, per_page=100):
            from .storage import project_from_repository
            project = project_from_repository(repo, readme_content=None)
            saved = storage.add_project(project)
            storage.mark_data_synced(saved.id)
            count += 1
            set_sync_state(synced_projects=count)

        # Phase 2: 加载 README（有进度，因为从 DB 可知总数）
        total = storage.count_projects()
        set_sync_state(
            status=SyncStatus.LOADING_README,
            readme_total=total,
            readme_current=0,
            readme_progress=0,
        )

        current = 0
        offset = 0
        while True:
            projects = storage.list_projects(limit=100, offset=offset)
            if not projects:
                break

            for project in projects:
                readme = await client.get_readme(project.owner_login, project.name)
                storage.update_readme(project.id, readme)
                current += 1
                set_sync_state(
                    readme_current=current,
                    readme_progress=int(current / max(total, 1) * 100),
                )

            offset += len(projects)

        await tools.close()

        set_sync_state(
            status=SyncStatus.COMPLETED,
            error="",
            readme_total=total,
            readme_current=total,
            readme_progress=100,
        )
    except Exception as e:
        set_sync_state(
            status=SyncStatus.FAILED,
            error=str(e),
        )


async def _run_vectorize_task(config: Config) -> None:
    """执行后台向量化任务（从 DB 读取，写入向量库）"""
    try:
        set_vector_state(
            status=VectorizeStatus.VECTORIZING,
            error="",
            current=0,
        )

        tools = MCPTools(config)
        storage = get_storage(config)

        # 统计待向量化总数（用于百分比进度）
        total = 0
        offset = 0
        batch = storage.list_unvectorized_projects(limit=500, offset=offset)
        while batch:
            total += len(batch)
            offset += len(batch)
            batch = storage.list_unvectorized_projects(limit=500, offset=offset)

        set_vector_state(total=total, progress=0)

        count = 0
        offset = 0
        while True:
            projects = storage.list_unvectorized_projects(limit=100, offset=offset)
            if not projects:
                break

            for project in projects:
                vector_id = await tools.vector_store.add_project(project)
                storage.mark_vectorized(project.id, vector_id)
                count += 1
                set_vector_state(
                    current=count,
                    progress=int(count / max(total, 1) * 100),
                )

            offset += len(projects)

        await tools.close()

        set_vector_state(
            status=VectorizeStatus.COMPLETED,
            progress=100,
            current=count,
            total=total,
            error="",
        )
    except Exception as e:
        set_vector_state(
            status=VectorizeStatus.FAILED,
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
        error="",
        synced_projects=0,
        readme_total=0,
        readme_current=0,
        readme_progress=0,
    )

    _sync_task = asyncio.create_task(_run_sync_task(config))
    return True


def start_vectorize_task(config: Config) -> bool:
    """启动向量化任务（如果未在运行）"""
    global _vector_task

    if _vector_state.get("status") == VectorizeStatus.VECTORIZING:
        return False

    set_vector_state(
        status=VectorizeStatus.PENDING,
        progress=0,
        total=0,
        current=0,
        error="",
    )

    _vector_task = asyncio.create_task(_run_vectorize_task(config))
    return True


def cancel_sync_task() -> bool:
    """取消同步任务"""
    global _sync_task

    if _sync_state.get("status") not in (SyncStatus.SYNCING, SyncStatus.LOADING_README):
        return False

    if _sync_task:
        _sync_task.cancel()
        _sync_task = None

    set_sync_state(
        status=SyncStatus.PENDING,
        error="已取消",
    )
    return True


def cancel_vectorize_task() -> bool:
    """取消向量化任务"""
    global _vector_task

    if _vector_state.get("status") != VectorizeStatus.VECTORIZING:
        return False

    if _vector_task:
        _vector_task.cancel()
        _vector_task = None

    set_vector_state(
        status=VectorizeStatus.PENDING,
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
        error="",
        synced_projects=0,
        readme_total=0,
        readme_current=0,
        readme_progress=0,
    )
    return True


def reset_vectorize_task() -> bool:
    """重置向量化状态"""
    global _vector_task

    if _vector_task:
        _vector_task.cancel()
        _vector_task = None

    set_vector_state(
        status=VectorizeStatus.PENDING,
        progress=0,
        total=0,
        current=0,
        error="",
    )
    return True

# ===== 路由处理器 =====


def get_static_dir() -> Path:
    """获取静态文件目录"""
    return Path(__file__).parent / "static"


async def index_page(request: Request) -> Response:
    """渲染 React 引导页面"""
    config: Config = request.app.state.config
    storage = get_storage(config)

    state = get_sync_state()
    vector_state = get_vector_state()
    synced_projects = storage.count_synced_projects()
    vectorized_projects = storage.count_vectorized_projects()

    initial_data = {
        "status": state["status"],
        "error": state["error"],
        "readme_total": state.get("readme_total", 0),
        "readme_current": state.get("readme_current", 0),
        "readme_progress": state.get("readme_progress", 0),
        "vector_status": vector_state["status"],
        "vector_progress": vector_state["progress"],
        "vector_current": vector_state["current"],
        "vector_total": vector_state["total"],
        "vector_error": vector_state["error"],
        "username": config.github_username,
        "synced_projects": synced_projects,
        "vectorized_projects": vectorized_projects,
        "require_sync": config.server.require_sync,
    }

    # Read the React index.html
    static_dir = get_static_dir()
    index_path = static_dir / "index.html"

    if index_path.exists():
        # Read the HTML and inject initial data
        html = index_path.read_text(encoding="utf-8")
        # Inject initial data as a script tag
        script = f'<script>window.__INITIAL_DATA__ = {json.dumps(initial_data)};</script>'
        # Insert before the closing </head> or </body>
        html = html.replace("</head>", f"{script}</head>")
        return Response(content=html, media_type="text/html")
    else:
        # Fallback: Return a simple HTML page if React hasn't been built
        fallback_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Stars MCP Server</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
        .container {{ background: #21262d; padding: 40px; border-radius: 16px; text-align: center; max-width: 500px; }}
        h1 {{ color: #f0f6fc; }}
        p {{ color: #8b949e; margin: 20px 0; }}
        .cmd {{ background: #161b22; padding: 16px; border-radius: 8px; font-family: monospace; text-align: left; margin: 20px 0; }}
        code {{ color: #58a6ff; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>GitHub Stars MCP Server</h1>
        <p>用户: {config.github_username}</p>
        <div class="cmd">
            <code>cd frontend && npm install && npm run build</code>
        </div>
        <p>请先构建 React 前端后再访问此页面</p>
    </div>
    <script>window.__INITIAL_DATA__ = {json.dumps(initial_data)};</script>
</body>
</html>
"""
        return Response(content=fallback_html, media_type="text/html")


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
    state["synced_projects"] = storage.count_synced_projects()
    state["vectorized_projects"] = storage.count_vectorized_projects()
    state["vector_status"] = get_vector_state()
    # 返回 readme 加载进度字段
    for key in ("readme_total", "readme_current", "readme_progress"):
        if key not in state:
            state[key] = 0

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
    reset_vectorize_task()

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


async def api_vectorize_start(request: Request) -> JSONResponse:
    """开始向量化"""
    config: Config = request.app.state.config

    if not start_vectorize_task(config):
        return JSONResponse({"error": "向量化任务已在运行"}, status_code=400)

    return JSONResponse({"message": "向量化已启动", "status": get_vector_state()})


async def api_vectorize_status(request: Request) -> JSONResponse:
    """查询向量化状态"""
    config: Config = request.app.state.config
    storage = get_storage(config)

    state = get_vector_state()
    state["total_projects"] = storage.count_projects()
    state["synced_projects"] = storage.count_synced_projects()
    state["vectorized_projects"] = storage.count_vectorized_projects()
    return JSONResponse(state)


async def api_vectorize_cancel(request: Request) -> JSONResponse:
    """取消向量化"""
    if not cancel_vectorize_task():
        return JSONResponse({"error": "没有正在运行的向量化任务"}, status_code=400)

    return JSONResponse({"message": "向量化已取消", "status": get_vector_state()})


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
        vectorized = storage.count_vectorized_projects()
        if vectorized > 0:
            set_vector_state(status=VectorizeStatus.COMPLETED)
        yield
        # 清理
        if _sync_task:
            _sync_task.cancel()
        if _vector_task:
            _vector_task.cancel()
        await tools.close()

    async def mcp_handler(request: Request):
        """MCP 端点处理器"""
        # 检查同步状态
        if config.server.require_sync and (check_sync_required() or check_vectorize_required()):
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
            Route("/api/vectorize/start", api_vectorize_start, methods=["POST"]),
            Route("/api/vectorize/status", api_vectorize_status, methods=["GET"]),
            Route("/api/vectorize/cancel", api_vectorize_cancel, methods=["POST"]),
        ] + ([Mount("/assets", app=StaticFiles(directory=str(get_static_dir() / "assets")), packages=None)] if (get_static_dir() / "assets").exists() else []),
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
