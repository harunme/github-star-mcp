"""Web 引导页面 + MCP HTTP 代理"""
import asyncio
import contextlib
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

from .config import Config
from .storage import Storage
from .tools import MCPTools, create_server
from .settings import get_settings, save_settings
from .settings.schema import GiteaConfig, LLMConfig, EmbedderConfig, TextSplitConfig
from .groups import GroupService
from .agent import GitHubStarsAgent
from .health import HealthChecker


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    LOADING_README = "loading_readme"
    COMPLETED = "completed"


class VectorizeStatus(str, Enum):
    """向量化状态"""
    PENDING = "pending"
    VECTORIZING = "vectorizing"
    COMPLETED = "completed"


# 全局同步状态管理
_sync_state: dict = {
    "status": SyncStatus.PENDING,
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
    "error": None,
}
_vector_task: Optional[asyncio.Task] = None

# 全局 Agent 实例
_agent: Optional[GitHubStarsAgent] = None


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
        SyncStatus.LOADING_README,
    )


def check_vectorize_required() -> bool:
    """检查是否需要向量化"""
    return _vector_state.get("status") == VectorizeStatus.PENDING


def get_agent(config: Config) -> GitHubStarsAgent:
    """获取 Agent 实例"""
    global _agent
    if _agent is None:
        _agent = GitHubStarsAgent(config)
    return _agent


# ===== 同步任务 =====


async def _run_sync_task(config: Config) -> None:
    """执行后台同步任务（两阶段：仓库同步 + README 加载）"""
    try:
        set_sync_state(
            status=SyncStatus.SYNCING,
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
            await asyncio.sleep(0)  # 让出控制权，允许取消
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
                await asyncio.sleep(0)  # 让出控制权，允许取消
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
            synced_projects=count,
            readme_total=total,
            readme_current=total,
            readme_progress=100,
        )
    except asyncio.CancelledError:
        set_sync_state(status=SyncStatus.PENDING)
        raise
    except Exception as e:
        logger.exception("同步任务失败: %s", e)
        set_sync_state(status=SyncStatus.PENDING)


async def _run_vectorize_task(config: Config) -> None:
    """执行后台向量化任务（从 DB 读取，写入向量库）"""
    try:
        tools = MCPTools(config)
        storage = get_storage(config)

        # 用 SQLite 真实已向量化数作为起点（防止中途重启导致计数不一致）
        total_remaining = storage.count_projects() - storage.count_vectorized_projects()
        if total_remaining <= 0:
            set_vector_state(
                status=VectorizeStatus.COMPLETED,
                progress=100,
                current=storage.count_vectorized_projects(),
                total=storage.count_vectorized_projects(),
            )
            await tools.close()
            return

        set_vector_state(
            status=VectorizeStatus.VECTORIZING,
            current=0,
            total=total_remaining,
            progress=0,
        )

        count = 0
        offset = 0
        batch_size = 100
        while True:
            projects = storage.list_unvectorized_projects(limit=batch_size, offset=0)
            if not projects:
                break

            for project in projects:
                await asyncio.sleep(0)  # 让出控制权，允许取消
                try:
                    vector_id = await tools.vector_store.add_project(project)
                    storage.mark_vectorized(project.id, vector_id)
                    count += 1
                except Exception as proj_err:
                    logger.warning("项目 %s 向量化失败，跳过: %s", project.full_name, proj_err)

                # 每次更新都查真实计数，确保进度准确
                current_done = storage.count_vectorized_projects()
                set_vector_state(
                    current=count,
                    total=total_remaining,
                    progress=int(count / max(total_remaining, 1) * 100),
                )

            offset += len(projects)

        await tools.close()

        final_count = storage.count_vectorized_projects()
        set_vector_state(
            status=VectorizeStatus.COMPLETED,
            progress=100,
            current=final_count,
            total=final_count,
        )
    except asyncio.CancelledError:
        # 保留已处理的计数，重启时能从断点继续
        storage = get_storage(config)
        current_done = storage.count_vectorized_projects()
        set_vector_state(
            status=VectorizeStatus.PENDING,
            current=current_done,
        )
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception("向量化任务失败: %s", error_msg)
        # 保留已处理的计数，重启时能从断点继续
        storage = get_storage(config)
        current_done = storage.count_vectorized_projects()
        set_vector_state(
            status=VectorizeStatus.PENDING,
            error=error_msg,
            current=current_done,
        )


def start_sync_task(config: Config) -> bool:
    """启动同步任务（如果未在运行）"""
    global _sync_task

    if _sync_state.get("status") == SyncStatus.SYNCING:
        return False

    # 重置状态
    set_sync_state(
        status=SyncStatus.PENDING,
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
    )
    return True


def rebuild_vectorize_task(config: Config) -> bool:
    """重建向量库：清空 LanceDB + 重置 SQLite vector_id，然后启动向量化"""
    global _vector_task

    if _vector_task:
        _vector_task.cancel()
        _vector_task = None

    # 重置向量状态
    set_vector_state(
        status=VectorizeStatus.PENDING,
        progress=0,
        total=0,
        current=0,
        error=None,
    )

    # 清空 LanceDB
    from .vector_store import create_vector_store
    vs = create_vector_store(config)
    vs.clear()

    # 重置 SQLite 中已向量化的标记
    storage = get_storage(config)
    storage.reset_vectorized_marks()

    # 启动向量化任务
    _vector_task = asyncio.create_task(_run_vectorize_task(config))
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
    synced_readme = storage.count_readme_projects()
    vectorized_projects = storage.count_vectorized_projects()

    initial_data = {
        "status": state["status"],
        "readme_total": state.get("readme_total", 0),
        "readme_current": state.get("readme_current", 0),
        "readme_progress": state.get("readme_progress", 0),
        "vector_status": vector_state["status"],
        "vector_progress": vector_state["progress"],
        "vector_current": vector_state["current"],
        "vector_total": vector_state["total"],
        "username": config.github_username,
        "synced_projects": synced_projects,
        "synced_readme": synced_readme,
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


async def spa_fallback(request: Request) -> Response:
    """SPA fallback: 未匹配的路径返回 index.html 由 React Router 处理"""
    return await index_page(request)


# ===== 同步 API =====


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
    state["synced_readme"] = storage.count_readme_projects()
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

    # 清空 SQLite
    from .storage import Project
    with storage.get_session() as session:
        from sqlmodel import delete
        session.execute(delete(Project))
        session.commit()

    # 清空 LanceDB
    from .vector_store import create_vector_store
    vs = create_vector_store(config)
    vs.clear()

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


async def api_sync_rebuild(request: Request) -> JSONResponse:
    """重建向量库"""
    config: Config = request.app.state.config

    if not rebuild_vectorize_task(config):
        return JSONResponse({"error": "向量库重建任务启动失败"}, status_code=400)

    return JSONResponse({"message": "向量库重建已启动", "status": get_vector_state()})


# ===== 配置 API =====


async def api_config_get(request: Request) -> JSONResponse:
    """获取配置（脱敏）"""
    try:
        settings = get_settings()
        # 脱敏处理：隐藏敏感字段
        if "github_token" in settings and settings["github_token"]:
            settings["github_token"] = "***"
        if "llm" in settings and settings["llm"].get("api_key"):
            settings["llm"]["api_key"] = "***"
        if "gitea" in settings and settings["gitea"].get("token"):
            settings["gitea"]["token"] = "***"
        if "embedder" in settings and settings["embedder"].get("api_key"):
            settings["embedder"]["api_key"] = "***"
        return JSONResponse(settings)
    except Exception as e:
        logger.exception("获取配置失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_config_put(request: Request) -> JSONResponse:
    """更新配置"""
    try:
        body = await request.json()
        cfg = request.app.state.config

        # 检测 LLM/Embedder 配置是否变更
        llm_changed = False
        embedder_changed = False

        if "github_token" in body:
            cfg.github_token = body["github_token"]
        if "github_username" in body:
            cfg.github_username = body["github_username"]
        if "llm" in body:
            llm_body = body["llm"]
            old_llm = cfg.llm
            cfg.llm = LLMConfig(**{k: v for k, v in llm_body.items() if v})
            llm_changed = (
                old_llm.provider != cfg.llm.provider or
                old_llm.model != cfg.llm.model or
                old_llm.base_url != cfg.llm.base_url
            )
        if "embedder" in body:
            embedder_body = body["embedder"]
            old_emb = cfg.embedder
            cfg.embedder = EmbedderConfig(**{k: v for k, v in embedder_body.items() if v})
            embedder_changed = (
                old_emb.provider != cfg.embedder.provider or
                old_emb.model != cfg.embedder.model or
                old_emb.base_url != cfg.embedder.base_url
            )
        if "gitea" in body:
            cfg.gitea = GiteaConfig(**{k: v for k, v in body["gitea"].items() if v})
        if "text_split" in body:
            cfg.text_split = TextSplitConfig(**{k: v for k, v in body["text_split"].items() if v is not None})
        if "theme" in body:
            cfg.theme = body["theme"]
        if "page_size" in body:
            cfg.page_size = body["page_size"]

        # 同步到 config.yaml
        save_settings(cfg.model_dump())

        # LLM/Embedder 变更时重建 Agent
        if llm_changed or embedder_changed:
            from .vector_store import VectorStore
            storage = get_storage(cfg)
            vector_store = VectorStore(cfg.vector_db_path)
            # 重建 _agent（全局）
            global _agent
            _agent = GitHubStarsAgent(config=cfg, storage=storage, vector_store=vector_store)
            # 同步到 request.app.state（供当前请求链使用）
            request.app.state.agent = _agent

        return JSONResponse({"message": "配置已保存"})
    except Exception as e:
        logger.exception("更新配置失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_config_validate(request: Request) -> JSONResponse:
    """验证配置"""
    try:
        body = await request.json()
        errors = []

        # 基本验证
        if "github_username" in body and not body["github_username"]:
            errors.append({"field": "github_username", "message": "GitHub 用户名不能为空"})

        if "llm" in body:
            llm = body["llm"]
            if llm.get("provider") == "anthropic" and not llm.get("api_key"):
                errors.append({"field": "llm.api_key", "message": "Anthropic API Key 不能为空"})

        if errors:
            return JSONResponse({"valid": False, "errors": errors}, status_code=400)

        return JSONResponse({"valid": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== 分组 API =====


async def api_groups_list(request: Request) -> JSONResponse:
    """列出分组"""
    try:
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())
        groups = service.list_groups()

        result = []
        for g in groups:
            result.append({
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "color": g.color,
                "icon": g.icon,
                "is_auto": g.is_auto,
                "project_count": service.count_projects_in_group(g.id),
                "created_at": g.created_at.isoformat() if g.created_at else None,
            })

        return JSONResponse({"groups": result})
    except Exception as e:
        logger.exception("列出分组失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_groups_create(request: Request) -> JSONResponse:
    """创建分组"""
    try:
        body = await request.json()
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())

        group = service.create_group(
            name=body.get("name"),
            description=body.get("description"),
            color=body.get("color", "#6366f1"),
            icon=body.get("icon"),
        )

        return JSONResponse({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "icon": group.icon,
            "created_at": group.created_at.isoformat() if group.created_at else None,
        })
    except Exception as e:
        logger.exception("创建分组失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_groups_update(request: Request) -> JSONResponse:
    """更新分组"""
    try:
        group_id = int(request.path_params.get("id", 0))
        body = await request.json()
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())

        group = service.update_group(
            group_id=group_id,
            name=body.get("name"),
            description=body.get("description"),
            color=body.get("color"),
            icon=body.get("icon"),
        )

        if not group:
            return JSONResponse({"error": "分组不存在"}, status_code=404)

        return JSONResponse({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "icon": group.icon,
        })
    except Exception as e:
        logger.exception("更新分组失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_groups_delete(request: Request) -> JSONResponse:
    """删除分组"""
    try:
        group_id = int(request.path_params.get("id", 0))
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())

        if not service.delete_group(group_id):
            return JSONResponse({"error": "分组不存在"}, status_code=404)

        return JSONResponse({"message": "分组已删除"})
    except Exception as e:
        logger.exception("删除分组失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_groups_add_projects(request: Request) -> JSONResponse:
    """添加项目到分组"""
    try:
        group_id = int(request.path_params.get("id", 0))
        body = await request.json()
        project_ids = body.get("project_ids", [])
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())

        count = service.batch_add_projects_to_group(project_ids, group_id)

        return JSONResponse({"message": f"已添加 {count} 个项目到分组"})
    except Exception as e:
        logger.exception("添加项目到分组失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_groups_remove_project(request: Request) -> JSONResponse:
    """从分组移除项目"""
    try:
        group_id = int(request.path_params.get("id", 0))
        project_id = int(request.path_params.get("project_id", 0))
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())

        if not service.remove_project_from_group(project_id, group_id):
            return JSONResponse({"error": "项目不在该分组中"}, status_code=404)

        return JSONResponse({"message": "已从分组移除"})
    except Exception as e:
        logger.exception("从分组移除项目失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_groups_get_projects(request: Request) -> JSONResponse:
    """获取分组中的项目"""
    try:
        group_id = int(request.path_params.get("id", 0))
        limit = int(request.query_params.get("limit", 100))
        offset = int(request.query_params.get("offset", 0))
        config: Config = request.app.state.config
        storage = get_storage(config)
        service = GroupService(storage.get_session())

        project_groups = service.get_group_projects(group_id, limit, offset)
        projects = []
        for pg in project_groups:
            p = storage.get_project(pg.project_id)
            if p:
                projects.append({
                    "id": p.id,
                    "name": p.name,
                    "full_name": p.full_name,
                    "description": p.description,
                    "language": p.language,
                    "stargazers_count": p.stargazers_count,
                    "html_url": p.html_url,
                })

        return JSONResponse({"projects": projects})
    except Exception as e:
        logger.exception("获取分组项目失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== 聊天 API =====


async def api_chat(request: Request) -> JSONResponse:
    """发送聊天消息"""
    try:
        body = await request.json()
        message = body.get("message", "")

        if not message:
            return JSONResponse({"error": "消息不能为空"}, status_code=400)

        agent: GitHubStarsAgent = getattr(request.app.state, "agent", None) or get_agent(request.app.state.config)

        # 处理聊天
        response = await agent.chat_simple(message)

        return JSONResponse({
            "message": response,
            "history": agent.get_history(),
        })
    except Exception as e:
        logger.exception("聊天处理失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_chat_stream(request: Request) -> StreamingResponse:
    """流式聊天响应"""
    try:
        body = await request.json()
        message = body.get("message", "")

        if not message:
            return StreamingResponse(
                iter([json.dumps({"error": "消息不能为空"})]),
                media_type="application/json",
                status_code=400,
            )

        agent: GitHubStarsAgent = getattr(request.app.state, "agent", None) or get_agent(request.app.state.config)

        async def generate():
            async for chunk in agent.chat(message):
                yield f"{json.dumps(chunk, ensure_ascii=False)}\n"

        return StreamingResponse(generate(), media_type="application/x-ndjson")
    except Exception as e:
        logger.exception("流式聊天失败: %s", e)
        return StreamingResponse(
            iter([json.dumps({"error": str(e)})]),
            media_type="application/json",
            status_code=500,
        )


async def api_chat_history(request: Request) -> JSONResponse:
    """获取聊天历史"""
    try:
        agent: GitHubStarsAgent = getattr(request.app.state, "agent", None) or get_agent(request.app.state.config)

        return JSONResponse({"history": agent.get_history()})
    except Exception as e:
        logger.exception("获取聊天历史失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_chat_clear(request: Request) -> JSONResponse:
    """清除聊天历史"""
    try:
        agent: GitHubStarsAgent = getattr(request.app.state, "agent", None) or get_agent(request.app.state.config)
        agent.clear_history()

        return JSONResponse({"message": "聊天历史已清除"})
    except Exception as e:
        logger.exception("清除聊天历史失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== 健康检测 API =====


async def api_health_check(request: Request) -> JSONResponse:
    """健康检测"""
    try:
        config: Config = request.app.state.config
        storage = get_storage(config)
        checker = HealthChecker(storage)

        reports = checker.get_unhealthy_projects(threshold=50)

        return JSONResponse({
            "reports": [r.to_dict() for r in reports],
            "total": len(reports),
        })
    except Exception as e:
        logger.exception("健康检测失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== 发现 API =====


async def api_discover_trending(request: Request) -> JSONResponse:
    """发现 Trending 项目"""
    try:
        # TODO: 实现真正的 GitHub Trending API
        return JSONResponse({
            "trending": [],
            "message": "Trending 功能开发中",
        })
    except Exception as e:
        logger.exception("发现 Trending 失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


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
        # 初始化 Agent 到 app.state
        app.state.agent = get_agent(config)
        # 启动 MCP session manager
        async with session_manager.run():
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

        return await session_manager.handle_request(request.scope, request.receive, request._send)

    app = Starlette(
        routes=[
            Route("/", index_page),
            Route("/mcp", mcp_handler, methods=["GET", "POST", "DELETE"]),
            # 同步 API
            Route("/api/sync/start", api_sync_start, methods=["POST"]),
            Route("/api/sync/status", api_sync_status, methods=["GET"]),
            Route("/api/sync/cancel", api_sync_cancel, methods=["POST"]),
            Route("/api/sync/reset", api_sync_reset, methods=["POST"]),
            Route("/api/sync/rebuild", api_sync_rebuild, methods=["POST"]),
            # 向量化 API
            Route("/api/vectorize/start", api_vectorize_start, methods=["POST"]),
            Route("/api/vectorize/status", api_vectorize_status, methods=["GET"]),
            Route("/api/vectorize/cancel", api_vectorize_cancel, methods=["POST"]),
            # 配置 API
            Route("/api/config", api_config_get, methods=["GET"]),
            Route("/api/config", api_config_put, methods=["PUT"]),
            Route("/api/config/validate", api_config_validate, methods=["POST"]),
            # 分组 API
            Route("/api/groups", api_groups_list, methods=["GET"]),
            Route("/api/groups", api_groups_create, methods=["POST"]),
            Route("/api/groups/{id}", api_groups_update, methods=["PUT"]),
            Route("/api/groups/{id}", api_groups_delete, methods=["DELETE"]),
            Route("/api/groups/{id}/projects", api_groups_get_projects, methods=["GET"]),
            Route("/api/groups/{id}/projects", api_groups_add_projects, methods=["POST"]),
            Route("/api/groups/{id}/projects/{project_id}", api_groups_remove_project, methods=["DELETE"]),
            # 聊天 API
            Route("/api/chat", api_chat, methods=["POST"]),
            Route("/api/chat/stream", api_chat_stream, methods=["POST"]),
            Route("/api/chat/history", api_chat_history, methods=["GET"]),
            Route("/api/chat/clear", api_chat_clear, methods=["POST"]),
            # 健康检测 API
            Route("/api/health/check", api_health_check, methods=["POST"]),
            # 发现 API
            Route("/api/discover/trending", api_discover_trending, methods=["GET"]),
            # SPA fallback: 所有未匹配的路径都返回 index.html 由 React Router 处理
            Route("/{path:path}", spa_fallback),
        ] + ([Mount("/assets", app=StaticFiles(directory=str(get_static_dir() / "assets")))] if (get_static_dir() / "assets").exists() else []),
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
