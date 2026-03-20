"""设置处理器"""
import os
from pathlib import Path
from typing import Optional

import yaml

from .schema import AppSettings, GiteaConfig, LLMConfig, EmbedderConfig, TextSplitConfig, ServerConfig, DatabaseConfig


CONFIG_FILE = Path("~/.github-star-mcp/config.yaml").expanduser()


def load_settings() -> AppSettings:
    """从 config.yaml 加载配置，支持环境变量覆盖"""
    if not CONFIG_FILE.exists():
        return AppSettings()

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # 环境变量覆盖
    if token := os.environ.get("GITHUB_STAR_GITHUB_TOKEN"):
        data["github_token"] = token
    if username := os.environ.get("GITHUB_STAR_GITHUB_USERNAME"):
        data["github_username"] = username
    if api_key := os.environ.get("GITHUB_STAR_ANTHROPIC_API_KEY"):
        data.setdefault("llm", {})["api_key"] = api_key
    if model := os.environ.get("GITHUB_STAR_ANTHROPIC_MODEL"):
        data.setdefault("llm", {})["model"] = model

    try:
        return AppSettings(**data)
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """保存配置到 config.yaml"""
    data = settings.model_dump()

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# 全局设置实例
_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """获取全局设置实例"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reload_settings() -> AppSettings:
    """重新加载设置"""
    global _settings
    _settings = load_settings()
    return _settings
