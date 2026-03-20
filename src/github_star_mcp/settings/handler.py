"""设置处理器

配置加载优先级：settings.json > 环境变量 > config.yaml > 默认值
"""
import json
import os
from pathlib import Path
from typing import Optional, Tuple

import yaml

from .schema import AppSettings, GiteaConfig, LLMConfig, EmbedderConfig, TextSplitConfig, ServerConfig, DatabaseConfig


# 全局设置路径
SETTINGS_DIR = Path("~/.github-star-mcp").expanduser()
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
CONFIG_FILE = SETTINGS_DIR / "config.yaml"


def _ensure_settings_dir() -> None:
    """确保设置目录存在"""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _load_from_yaml() -> dict:
    """从 config.yaml 加载配置"""
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_from_settings_json() -> dict:
    """从 settings.json 加载配置"""
    if not SETTINGS_FILE.exists():
        return {}

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_to_settings_json(settings: AppSettings) -> None:
    """保存配置到 settings.json"""
    _ensure_settings_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)


def _save_to_yaml(settings: AppSettings) -> None:
    """保存配置到 config.yaml（仅更新 AppSettings 管理的字段，保留其他内容）"""
    _ensure_settings_dir()

    # 读取现有 config.yaml 内容，保留未管理的字段/注释
    existing = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}

    # 只覆盖 AppSettings 管理的字段
    existing["github_token"] = settings.github_token
    existing["github_username"] = settings.github_username
    existing["anthropic_api_key"] = settings.llm.api_key
    existing["anthropic_model"] = settings.llm.model
    existing["gitea"] = settings.gitea.model_dump()
    existing["database"] = settings.database.model_dump()

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """将嵌套字典展平为点分隔键"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _unflatten_dict(d: dict, sep: str = ".") -> dict:
    """将点分隔键还原为嵌套字典"""
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def load_settings() -> AppSettings:
    """加载完整配置

    优先级: settings.json > 环境变量 > config.yaml > 默认值
    """
    # 1. 加载 config.yaml
    yaml_config = _load_from_yaml()

    # 2. 加载环境变量
    env_config = {}
    for key in ["github_token", "github_username", "anthropic_api_key", "anthropic_model"]:
        env_value = os.environ.get(f"GITHUB_STAR_{key.upper()}")
        if env_value:
            # 转换键名
            if key.startswith("anthropic_"):
                env_key = key.replace("anthropic_", "llm.")
            else:
                env_key = key.replace("_", ".")
            env_config[env_key] = env_value

    # 3. 加载 settings.json
    settings_json_config = _load_from_settings_json()

    # 4. 合并配置 (优先级从低到高)
    merged = {}
    merged.update(yaml_config)
    merged.update(env_config)
    merged.update(settings_json_config)

    # 5. 转换为 AppSettings 格式
    if merged:
        # 处理嵌套配置
        final_config = {}
        for key, value in merged.items():
            if key.startswith("gitea."):
                continue  # 特殊处理
            elif key.startswith("llm."):
                continue  # 特殊处理
            elif key.startswith("embedder."):
                continue  # 特殊处理
            elif key.startswith("text_split."):
                continue  # 特殊处理
            elif key.startswith("server."):
                continue  # 特殊处理
            elif key.startswith("database."):
                continue  # 特殊处理
            else:
                final_config[key] = value

        # 处理嵌套对象
        if "gitea" in merged:
            final_config["gitea"] = merged["gitea"]
        elif any(k.startswith("gitea.") for k in merged):
            final_config["gitea"] = _unflatten_dict({
                k.replace("gitea.", ""): v
                for k, v in merged.items()
                if k.startswith("gitea.")
            })

        if "llm" in merged:
            final_config["llm"] = merged["llm"]
        elif any(k.startswith("llm.") for k in merged):
            final_config["llm"] = _unflatten_dict({
                k.replace("llm.", ""): v
                for k, v in merged.items()
                if k.startswith("llm.")
            })

        if "embedder" in merged:
            final_config["embedder"] = merged["embedder"]
        elif any(k.startswith("embedder.") for k in merged):
            final_config["embedder"] = _unflatten_dict({
                k.replace("embedder.", ""): v
                for k, v in merged.items()
                if k.startswith("embedder.")
            })

        if "text_split" in merged:
            final_config["text_split"] = merged["text_split"]

        if "server" in merged:
            final_config["server"] = merged["server"]

        if "database" in merged:
            final_config["database"] = merged["database"]

        try:
            return AppSettings(**final_config)
        except Exception as e:
            # 如果解析失败，返回默认配置
            return AppSettings()
    else:
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """保存配置到 settings.json 和 config.yaml"""
    _save_to_settings_json(settings)
    _save_to_yaml(settings)


def get_settings_with_defaults() -> Tuple[AppSettings, dict]:
    """获取带默认值的配置和默认值差异

    返回: (当前配置, 默认配置)
    """
    current = load_settings()
    defaults = AppSettings()
    return current, defaults


def mask_sensitive_config(config: AppSettings) -> dict:
    """脱敏配置（直接返回所有值，用户可查看自己的配置）"""
    return config.model_dump()


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


def update_settings(settings: AppSettings) -> AppSettings:
    """更新并保存设置"""
    global _settings
    _settings = settings
    save_settings(settings)
    return settings
