"""设置处理器"""
import os
from pathlib import Path

import yaml

CONFIG_FILE = Path("~/.github-star-mcp/config.yaml").expanduser()


def _load_yaml() -> dict:
    """从 config.yaml 加载配置"""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(data: dict) -> None:
    """保存配置到 config.yaml"""
    # 确保目录存在
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_settings() -> dict:
    """从 config.yaml 加载配置（兼容 dict 格式）"""
    data = _load_yaml()

    # 环境变量覆盖
    if token := os.environ.get("GITHUB_STAR_GITHUB_TOKEN"):
        data["github_token"] = token
    if username := os.environ.get("GITHUB_STAR_GITHUB_USERNAME"):
        data["github_username"] = username
    if api_key := os.environ.get("GITHUB_STAR_ANTHROPIC_API_KEY"):
        data.setdefault("llm", {})["api_key"] = api_key
    if model := os.environ.get("GITHUB_STAR_ANTHROPIC_MODEL"):
        data.setdefault("llm", {})["model"] = model

    return data


def save_settings(settings: dict) -> None:
    """保存配置到 config.yaml"""
    _save_yaml(settings)


def get_settings() -> dict:
    """获取配置（从 config.yaml）"""
    return load_settings()


def reload_settings() -> dict:
    """重新加载配置"""
    return load_settings()
