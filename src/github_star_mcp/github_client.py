"""GitHub API 客户端"""
import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx


@dataclass
class Repository:
    """仓库信息"""
    id: int
    name: str
    full_name: str
    description: Optional[str]
    html_url: str
    clone_url: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    topics: list[str]
    created_at: str
    updated_at: str
    owner_login: str
    owner_avatar_url: str
    readme_content: Optional[str] = None


class GitHubClient:
    """GitHub API 客户端"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_user(self, username: str) -> dict:
        """获取用户信息"""
        client = await self._get_client()
        response = await client.get(f"{self.BASE_URL}/users/{username}")
        response.raise_for_status()
        return response.json()

    async def list_stars(
        self,
        username: str,
        per_page: int = 100,
    ) -> AsyncIterator[Repository]:
        """获取用户所有 stars"""
        client = await self._get_client()
        page = 1

        while True:
            response = await client.get(
                f"{self.BASE_URL}/users/{username}/starred",
                params={"per_page": per_page, "page": page, "sort": "updated"},
            )
            response.raise_for_status()
            items = response.json()

            if not items:
                break

            for item in items:
                yield Repository(
                    id=item["id"],
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description"),
                    html_url=item["html_url"],
                    clone_url=item["clone_url"],
                    language=item.get("language"),
                    stargazers_count=item.get("stargazers_count", 0),
                    forks_count=item.get("forks_count", 0),
                    topics=item.get("topics", []),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    owner_login=item["owner"]["login"],
                    owner_avatar_url=item["owner"]["avatar_url"],
                )

            if len(items) < per_page:
                break
            page += 1

    async def get_repo(self, owner: str, repo: str) -> Repository:
        """获取仓库详情"""
        client = await self._get_client()
        response = await client.get(f"{self.BASE_URL}/repos/{owner}/{repo}")
        response.raise_for_status()
        item = response.json()

        return Repository(
            id=item["id"],
            name=item["name"],
            full_name=item["full_name"],
            description=item.get("description"),
            html_url=item["html_url"],
            clone_url=item["clone_url"],
            language=item.get("language"),
            stargazers_count=item.get("stargazers_count", 0),
            forks_count=item.get("forks_count", 0),
            topics=item.get("topics", []),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
            owner_login=item["owner"]["login"],
            owner_avatar_url=item["owner"]["avatar_url"],
        )

    async def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """获取仓库 README 内容"""
        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/readme"
            )
            if response.status_code == 200:
                data = response.json()
                # 获取 README 内容
                content_response = await client.get(data["download_url"])
                if content_response.status_code == 200:
                    return content_response.text
        except httpx.HTTPStatusError:
            pass
        return None


async def get_github_client(token: str) -> GitHubClient:
    """创建 GitHub 客户端"""
    return GitHubClient(token)
