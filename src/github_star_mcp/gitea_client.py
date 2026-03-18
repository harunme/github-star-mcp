"""Gitea API 客户端"""
import tempfile
from pathlib import Path
from typing import Optional

import git
import httpx


class GiteaClient:
    """Gitea API 客户端"""

    def __init__(self, url: str, token: str, username: str):
        self.url = url.rstrip("/")
        self.token = token
        self.username = username
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"token {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_user(self) -> dict:
        """获取当前用户信息"""
        client = await self._get_client()
        response = await client.get(f"{self.url}/api/v1/user")
        response.raise_for_status()
        return response.json()

    async def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = False,
    ) -> dict:
        """创建仓库"""
        client = await self._get_client()
        response = await client.post(
            f"{self.url}/api/v1/user/repos",
            json={
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_repo(self, owner: str, repo: str) -> Optional[dict]:
        """获取仓库信息"""
        client = await self._get_client()
        try:
            response = await client.get(f"{self.url}/api/v1/repos/{owner}/{repo}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return None

    async def fork_repo(
        self,
        owner: str,
        repo: str,
    ) -> dict:
        """Fork 仓库"""
        client = await self._get_client()
        response = await client.post(
            f"{self.url}/api/v1/repos/{owner}/{repo}/fork",
            json={},
        )
        response.raise_for_status()
        return response.json()

    async def mirror_repo(
        self,
        clone_url: str,
        name: str,
        description: str = "",
    ) -> dict:
        """创建镜像仓库"""
        client = await self._get_client()
        response = await client.post(
            f"{self.url}/api/v1/repos/{self.username}",
            json={
                "name": name,
                "description": description,
                "mirror": True,
                "repo_url": clone_url,
                "service": "git",
            },
        )
        response.raise_for_status()
        return response.json()

    def clone_and_push(
        self,
        clone_url: str,
        gitea_repo_url: str,
    ) -> None:
        """克隆并推送到 Gitea"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 克隆仓库
            repo = git.Repo.clone_from(clone_url, tmpdir)

            # 添加 Gitea remote
            remote_url = gitea_repo_url.replace(
                "https://", f"https://{self.username}:{self.token}@"
            )
            repo.create_remote("gitea", remote_url)

            # Push 所有分支和标签
            repo.remotes.gitea.push(refspec="+refs/heads/*:refs/heads/*")
            try:
                repo.remotes.gitea.push(refspec="+refs/tags/*:refs/tags/*")
            except Exception:
                # 忽略标签推送失败
                pass


async def create_gitea_client(
    url: str,
    token: str,
    username: str,
) -> GiteaClient:
    """创建 Gitea 客户端"""
    return GiteaClient(url, token, username)
