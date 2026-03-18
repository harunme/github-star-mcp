"""RAG 问答模块"""
from typing import Optional

import anthropic

from .config import Config
from .vector_store import VectorStore


class RAG:
    """RAG 问答"""

    def __init__(self, config: Config, vector_store: VectorStore):
        self.config = config
        self.vector_store = vector_store
        self._client: Optional[anthropic.AsyncAnthropic] = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            if not self.config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required for RAG")
            self._client = anthropic.AsyncAnthropic(
                api_key=self.config.anthropic_api_key,
            )
        return self._client

    async def ask(
        self,
        question: str,
        max_projects: int = 5,
    ) -> str:
        """基于 RAG 问答"""
        # 1. 向量搜索相关项目
        search_results = await self.vector_store.search(
            query=question,
            limit=max_projects,
        )

        if not search_results:
            return "没有找到相关的项目。"

        # 2. 构建上下文
        context_parts = []
        for i, result in enumerate(search_results, 1):
            payload = result["payload"]
            context_parts.append(
                f"项目 {i}: {payload.get('name')}\n"
                f"描述: {payload.get('description') or '无'}\n"
                f"语言: {payload.get('language') or '未知'}\n"
                f"话题: {payload.get('topics') or '无'}\n"
                f"链接: {payload.get('html_url')}\n"
            )

        context = "\n\n".join(context_parts)

        # 3. 调用 LLM 生成答案
        client = self._get_client()

        system_prompt = """你是一个 GitHub 项目助手。用户向你询问关于他们收藏的 GitHub 项目的问题。

根据以下相关的 GitHub 项目信息，回答用户的问题。
如果无法从提供的信息中找到答案，请如实说明。

相关项目信息：
"""
        user_prompt = f"""用户问题: {question}

相关项目信息:
{context}

请根据以上信息回答用户的问题。"""

        response = await client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        # 提取文本内容
        answer = ""
        for block in response.content:
            if hasattr(block, "text"):
                answer += block.text

        # 添加相关项目引用
        references = "\n\n参考项目:\n"
        for result in search_results:
            payload = result["payload"]
            references += f"- [{payload.get('name')}]({payload.get('html_url')}) (相似度: {result['score']:.2f})\n"

        return answer + references


def create_rag(config: Config, vector_store: VectorStore) -> RAG:
    """创建 RAG 实例"""
    return RAG(config, vector_store)
