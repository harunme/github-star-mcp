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
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="传输模式: stdio 或 http",
)
@click.option(
    "--mode",
    type=click.Choice(["guided", "mcp"]),
    default=None,
    help="服务器模式: guided (引导页面) 或 mcp (纯 MCP)",
)
@click.option(
    "--host",
    default=None,
    help="HTTP 模式监听地址",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="HTTP 模式监听端口",
)
def main(
    config_path: str | None,
    github_token: str | None,
    github_username: str | None,
    gitea_url: str | None,
    gitea_token: str | None,
    gitea_username: str | None,
    anthropic_api_key: str | None,
    transport: str = "stdio",
    mode: str | None = None,
    host: str | None = None,
    port: int | None = None,
):
    """GitHub Stars MCP Server"""
    # 加载配置
    config = Config.load(config_path)

    # 环境变量覆盖
    if github_token:
        config.github_token = github_token
    if github_username:
        config.github_username = github_username
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
    if mode == "guided":
        # 引导模式
        from .web_app import run_web_server
        run_web_server(config, host=host, port=port)
    elif transport == "http":
        from .web_app import run_http_server
        actual_host = host or config.server.host
        actual_port = port or config.server.port
        asyncio.run(run_http_server(config, host=actual_host, port=actual_port))
    else:
        from .tools import run_server
        asyncio.run(run_server(config))


if __name__ == "__main__":
    main()
