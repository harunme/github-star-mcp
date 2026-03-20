"""LLM 意图解析器"""
import json
import logging
from typing import Tuple, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """你是一个 GitHub Stars 助手，负责解析用户查询。

用户会用中文或英文提问，你需要：
1. 识别用户意图 (intent)
2. 提取相关参数 (params)

支持的意图类型：
- search: 搜索项目 (需要 query)
- list: 列出项目 (需要 limit, language 可选)
- auto_group: 自动分组项目
- check_health: 健康检测
- status: 状态查询
- discover: 发现趋势/热门项目
- list_groups: 列出分组
- sync: 同步 stars

参数提取要求：
- language: 编程语言（如 Python, JavaScript, Go 等）
- limit: 返回数量（默认 5）
- query: 搜索关键词
- group_name: 分组名称
- criteria: 分组标准

请以 JSON 格式返回：
{
  "intent": "search",
  "params": {
    "query": "Python web framework",
    "language": "Python",
    "limit": 5
  },
  "reasoning": "用户想找 Python 的 web 框架"
}
"""


class IntentParser:
    """LLM 意图解析器"""

    def __init__(self, llm):
        self.llm = llm

    async def parse(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """解析用户消息，返回 (intent, params)"""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=INTENT_SYSTEM_PROMPT),
                HumanMessage(content=message)
            ])

            # 解析 JSON 响应
            result = json.loads(response.content)
            intent = result.get("intent", "search")
            params = result.get("params", {})

            logger.debug(f"Intent parsed: {intent}, params: {params}")
            return intent, params

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}, falling back to search")
            return "search", {"query": message}
        except Exception as e:
            logger.exception(f"Intent parsing failed: {e}")
            return "search", {"query": message}


class FallbackIntentParser:
    """关键字匹配的备用解析器"""

    def parse(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """基于关键字的意图识别"""
        message_lower = message.lower()

        # 搜索意图
        search_keywords = ["搜索", "找", "查找", "推荐", "有什么", "show me", "find", "search"]
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
        status_keywords = ["状态", "统计", "how many"]
        if any(kw in message_lower for kw in status_keywords):
            return "status", {}

        # 列出意图
        list_keywords = ["列表", "列出", "list", "看看"]
        if any(kw in message_lower for kw in list_keywords):
            return "list", {}

        # 默认：搜索
        return "search", {"query": message}
