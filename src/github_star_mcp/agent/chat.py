"""Agent 聊天逻辑"""
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..config import Config
from ..storage import Storage
from ..vector_store import VectorStore
from .intent_parser import IntentParser, FallbackIntentParser
from .tools import AgentTools, ToolResult
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ChatMessage:
    """聊天消息"""
    def __init__(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
    ):
        self.role = role  # "user" | "assistant" | "system" | "tool"
        self.content = content
        self.tool_calls = tool_calls or []
        self.tool_results = tool_results or []
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class ChatHistory:
    """聊天历史（持久化到 SQLite）"""
    def __init__(self, storage: Optional[Storage] = None, max_messages: int = 50):
        self.storage = storage
        self.messages: List[ChatMessage] = []
        self.max_messages = max_messages
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.storage:
            db_msgs = self.storage.get_chat_messages(self.max_messages)
            import json
            for m in db_msgs:
                self.messages.append(ChatMessage(
                    role=m.role,
                    content=m.content,
                    tool_calls=json.loads(m.tool_calls or "[]"),
                    tool_results=json.loads(m.tool_results or "[]"),
                    metadata=json.loads(m.metadata or "{}"),
                    created_at=m.created_at,
                ))

    def add(self, message: ChatMessage) -> None:
        self._ensure_loaded()
        self.messages.append(message)
        # 限制历史长度
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        # 持久化
        if self.storage:
            self.storage.save_chat_message(
                role=message.role,
                content=message.content,
                tool_calls=message.tool_calls,
                tool_results=message.tool_results,
                metadata=message.metadata,
            )

    def get_context(self) -> str:
        """获取上下文字符串"""
        self._ensure_loaded()
        context_parts = []
        for msg in self.messages[-10:]:  # 最近 10 条
            role = {"user": "用户", "assistant": "助手", "system": "系统"}.get(msg.role, msg.role)
            context_parts.append(f"{role}: {msg.content}")
        return "\n".join(context_parts)

    def to_list(self) -> List[dict]:
        self._ensure_loaded()
        return [m.to_dict() for m in self.messages]


class GitHubStarsAgent:
    """GitHub Stars Agent"""

    def __init__(
        self,
        config: Config,
        storage: Optional[Storage] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self.config = config
        self.storage = storage if storage is not None else Storage(config.db_path)
        self.vector_store = vector_store if vector_store is not None else VectorStore(config.vector_db_path)
        self.tools = AgentTools(config, self.storage, self.vector_store)
        self.chat_history = ChatHistory(self.storage)
        self._llm = None
        self._intent_parser = None

    def _create_llm(self):
        """创建 LLM 实例"""
        llm_config = getattr(self.config, "llm", None)
        provider = llm_config.provider if llm_config else "anthropic"

        if provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    api_key=llm_config.api_key or "",
                    model=llm_config.model or "gpt-4o",
                    base_url=llm_config.base_url or None,
                    streaming=True,
                )
            except ImportError:
                logger.warning("OpenAI LLM not available, falling back to Anthropic")
                provider = "anthropic"

        if provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    api_key=llm_config.api_key or "",
                    model=llm_config.model or "claude-sonnet-4-20250514",
                    base_url=llm_config.base_url or None,
                    streaming=True,
                )
            except ImportError:
                logger.warning("Anthropic LLM not available")
                return None

        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    base_url=llm_config.base_url if llm_config else "http://localhost:11434",
                    model=llm_config.model if llm_config else "llama3.2",
                    streaming=True,
                )
            except ImportError:
                logger.warning("Ollama LLM not available")
                return None

        return None

    def _get_intent_parser(self):
        """获取意图解析器（懒加载）"""
        if self._intent_parser is None:
            llm = self._create_llm()
            if llm is not None:
                self._intent_parser = IntentParser(llm)
            else:
                # LLM 不可用时使用备用解析器
                self._intent_parser = FallbackIntentParser()
        return self._intent_parser

    def _route_intent(self, message: str) -> tuple[str, dict]:
        """路由意图识别

        返回: (intent_name, intent_params)
        """
        message_lower = message.lower()

        # 搜索意图
        search_keywords = ["搜索", "找", "查找", "推荐", "有什么", "show me"]
        if any(kw in message_lower for kw in search_keywords):
            return "search", {"query": message}

        # 分组意图
        group_keywords = ["分组", "归类", "分类", "整理"]
        if any(kw in message_lower for kw in group_keywords):
            if "自动" in message or "ai" in message_lower:
                return "auto_group", {"criteria": message}
            return "list_groups", {}

        # 健康检测意图
        health_keywords = ["健康", "检测", "检查", "不活跃", "归档", "过时"]
        if any(kw in message_lower for kw in health_keywords):
            return "check_health", {}

        # 发现意图
        discover_keywords = ["发现", "热门", "trending", "趋势"]
        if any(kw in message_lower for kw in discover_keywords):
            return "discover", {"query": message}

        # 同步意图
        sync_keywords = ["同步", "sync", "更新"]
        if any(kw in message_lower for kw in sync_keywords):
            return "sync", {}

        # 状态意图
        status_keywords = ["状态", "统计", "状态", "how many"]
        if any(kw in message_lower for kw in status_keywords):
            return "status", {}

        # 列出意图
        list_keywords = ["列表", "列出", "list", "看看"]
        if any(kw in message_lower for kw in list_keywords):
            return "list", {}

        # 默认：搜索
        return "search", {"query": message}

    async def _execute_tool(self, tool_name: str, params: dict) -> ToolResult:
        """执行工具"""
        try:
            if tool_name == "search_projects":
                return await self.tools.search_projects(
                    query=params.get("query", ""),
                    limit=params.get("limit", 5),
                )
            elif tool_name == "list_stars":
                return await self.tools.list_stars(
                    limit=params.get("limit", 100),
                    language=params.get("language"),
                )
            elif tool_name == "auto_group_projects":
                return await self.tools.auto_group_projects(
                    group_name=params.get("group_name", "默认分组"),
                    criteria=params.get("criteria"),
                )
            elif tool_name == "check_repo_health":
                return await self.tools.check_repo_health(
                    project_id=params.get("project_id"),
                    full_name=params.get("full_name"),
                )
            elif tool_name == "discover_trending":
                return await self.tools.discover_trending(
                    language=params.get("language"),
                    since=params.get("since", "daily"),
                    limit=params.get("limit", 10),
                )
            elif tool_name == "analyze_sync_status":
                return await self.tools.analyze_sync_status()
            else:
                return ToolResult(
                    success=False,
                    content=f"未知工具: {tool_name}",
                    tool_name=tool_name,
                )
        except Exception as e:
            logger.exception("工具执行失败: %s", e)
            return ToolResult(
                success=False,
                content=f"工具执行失败: {str(e)}",
                tool_name=tool_name,
            )

    async def chat(self, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """处理聊天消息"""
        # 添加用户消息到历史
        self.chat_history.add(ChatMessage(role="user", content=message))

        # 意图识别（LLM 驱动）
        parser = self._get_intent_parser()
        if isinstance(parser, IntentParser):
            intent, params = await parser.parse(message)
        else:
            intent, params = parser.parse(message)

        # 记录工具调用
        tool_calls = []

        try:
            # 根据意图执行工具
            if intent == "search":
                result = await self._execute_tool("search_projects", {
                    "query": params["query"],
                    "limit": 5,
                })
                tool_calls.append({"tool": "search_projects", "params": params})

            elif intent == "auto_group":
                result = await self._execute_tool("auto_group_projects", {
                    "group_name": params.get("group_name", "默认分组"),
                    "criteria": params.get("criteria"),
                })
                tool_calls.append({"tool": "auto_group_projects", "params": params})

            elif intent == "check_health":
                result = await self._execute_tool("check_repo_health", {})
                tool_calls.append({"tool": "check_repo_health", "params": {}})

            elif intent == "discover":
                result = await self._execute_tool("discover_trending", {
                    "query": params.get("query", ""),
                })
                tool_calls.append({"tool": "discover_trending", "params": params})

            elif intent == "sync":
                # 暂时不支持直接同步，返回提示
                result = ToolResult(
                    success=True,
                    content="同步功能正在开发中。请使用 Web 界面中的同步按钮。",
                    tool_name="sync_stars",
                )

            elif intent == "status":
                result = await self._execute_tool("analyze_sync_status", {})
                tool_calls.append({"tool": "analyze_sync_status", "params": {}})

            elif intent == "list":
                result = await self._execute_tool("list_stars", {"limit": 20})
                tool_calls.append({"tool": "list_stars", "params": {"limit": 20}})

            elif intent == "list_groups":
                groups = self.tools.group_service.list_groups()
                result = ToolResult(
                    success=True,
                    content=f"## 分组列表\n\n" + "\n".join([f"- {g.name}: {self.tools.group_service.count_projects_in_group(g.id)} 个项目" for g in groups]) if groups else "还没有创建任何分组。",
                    tool_name="list_groups",
                )

            else:
                # 默认使用搜索
                result = await self._execute_tool("search_projects", {
                    "query": message,
                    "limit": 5,
                })
                tool_calls.append({"tool": "search_projects", "params": {"query": message}})

            # 流式返回结果
            content = result.content

            # 发送工具调用信息
            if tool_calls:
                yield {
                    "type": "tool_call",
                    "data": tool_calls,
                }

            # 发送内容（分段）
            for i in range(0, len(content), 100):
                chunk = content[i:i + 100]
                yield {
                    "type": "content",
                    "data": chunk,
                }

            # 添加助手消息到历史
            self.chat_history.add(ChatMessage(
                role="assistant",
                content=content,
                tool_calls=[tc["tool"] for tc in tool_calls],
            ))

            # 发送完成信号
            yield {
                "type": "done",
                "data": None,
            }

        except Exception as e:
            logger.exception("聊天处理失败: %s", e)
            error_content = f"处理失败: {str(e)}"
            yield {
                "type": "error",
                "data": error_content,
            }
            self.chat_history.add(ChatMessage(
                role="assistant",
                content=error_content,
            ))

    async def chat_simple(self, message: str) -> str:
        """简单聊天（返回完整响应）"""
        result_parts = []
        async for chunk in self.chat(message):
            if chunk["type"] == "content":
                result_parts.append(chunk["data"])
            elif chunk["type"] == "done":
                break
            elif chunk["type"] == "error":
                return f"错误: {chunk['data']}"

        return "".join(result_parts)

    def get_history(self) -> List[dict]:
        """获取聊天历史"""
        return self.chat_history.to_list()

    def clear_history(self) -> None:
        """清除聊天历史（内存 + DB）"""
        self.chat_history.messages = []
        self.chat_history._loaded = True
        if self.storage:
            self.storage.clear_chat_messages()
