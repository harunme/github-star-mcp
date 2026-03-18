"""MCP Server 入口"""
import asyncio
import sys

import click

from .config import Config, get_config
from .tools import run_server


@click.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    help="配置文件路径",
)
@click.option(
    "--github-token",
    envvar="GITHUB_STAR_GITHUB_TOKEN",
    help="GitHub Token",
)
@click.option(
    "--github-username",
    envvar="GITHUB_STAR_GITHUB_USERNAME",
    help="GitHub 用户名",
)
@click.option(
    "--qdrant-host",
    default=None,
    help="Qdrant 主机",
)
@click.option(
    "--gitea-url",
    default=None,
    help="Gitea URL",
)
@click.option(
    "--gitea-token",
    default=None,
    help="Gitea Token",
)
@click.option(
    "--gitea-username",
    default=None,
    help="Gitea 用户名",
)
@click.option(
    "--anthropic-api-key",
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API Key (用于 RAG)",
)
def main(
    config_path: str | None,
    github_token: str | None,
    github_username: str | None,
    qdrant_host: str | None,
    gitea_url: str | None,
    gitea_token: str | None,
    gitea_username: str | None,
    anthropic_api_key: str | None,
):
    """GitHub Stars MCP Server"""
    # 加载配置
    config = Config.load(config_path)

    # 环境变量覆盖
    if github_token:
        config.github_token = github_token
    if github_username:
        config.github_username = github_username
    if qdrant_host:
        config.qdrant.host = qdrant_host
    if gitea_url:
        config.gitea.url = gitea_url
    if gitea_token:
        config.gitea.token = gitea_token
    if gitea_username:
        config.gitea.username = gitea_username
    if anthropic_api_key:
        config.anthropic_api_key = anthropic_api_key

    # 验证必要配置
    if not config.github_token:
        click.echo("错误: 需要设置 GitHub Token (--github-token 或 GITHUB_STAR_GITHUB_TOKEN)", err=True)
        sys.exit(1)

    if not config.github_username:
        click.echo("错误: 需要设置 GitHub 用户名 (--github-username 或 GITHUB_STAR_GITHUB_USERNAME)", err=True)
        sys.exit(1)

    # 运行服务器
    asyncio.run(run_server(config))


if __name__ == "__main__":
    main()
