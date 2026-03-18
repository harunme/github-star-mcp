"""测试模块"""
import pytest
from unittest.mock import Mock, AsyncMock, patch


def test_config_load():
    """测试配置加载"""
    from github_star_mcp.config import Config

    config = Config(
        github_token="test_token",
        github_username="test_user",
    )

    assert config.github_token == "test_token"
    assert config.github_username == "test_user"


def test_project_model():
    """测试项目模型"""
    from github_star_mcp.storage import Project

    project = Project(
        id=1,
        name="test-repo",
        full_name="testuser/test-repo",
        description="A test repo",
        html_url="https://github.com/testuser/test-repo",
        clone_url="https://github.com/testuser/test-repo.git",
        owner_login="testuser",
    )

    assert project.id == 1
    assert project.name == "test-repo"
    assert project.full_name == "testuser/test-repo"


@pytest.mark.asyncio
async def test_github_client_list_stars():
    """测试 GitHub 客户端获取 stars"""
    from github_star_mcp.github_client import GitHubClient

    with patch("httpx.AsyncClient") as mock_client:
        # Mock 响应
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "description": "A test repo",
                "html_url": "https://github.com/testuser/test-repo",
                "clone_url": "https://github.com/testuser/test-repo.git",
                "language": "Python",
                "stargazers_count": 100,
                "forks_count": 10,
                "topics": ["test"],
                "created_at": "2023-01-01",
                "updated_at": "2023-12-01",
                "owner": {
                    "login": "testuser",
                    "avatar_url": "https://github.com/testuser.png",
                },
            }
        ]
        mock_response.raise_for_status = Mock()

        mock_client.return_value.get = AsyncMock(return_value=mock_response)

        client = GitHubClient("test_token")
        repos = [repo async for repo in client.list_stars("testuser")]

        assert len(repos) == 1
        assert repos[0].name == "test-repo"
        assert repos[0].language == "Python"
