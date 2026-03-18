"""配置管理模块"""
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class QdrantConfig(BaseModel):
    """Qdrant 配置"""
    host: str = "localhost"
    port: int = 6333
    vector_size: int = 384  # sentence-transformers default


class GiteaConfig(BaseModel):
    """Gitea 配置"""
    url: str = "http://localhost:3000"
    token: str = ""
    username: str = ""


class ServerConfig(BaseModel):
    """服务器配置"""
    mode: str = "guided"  # guided | mcp
    host: str = "0.0.0.0"
    port: int = 8080
    require_sync: bool = True  # 是否强制同步后解锁 MCP


class DatabaseConfig(BaseModel):
    """数据库配置"""
    path: str = "~/.github-star-mcp/data.db"


class Config(BaseSettings):
    """主配置类"""
    model_config = SettingsConfigDict(
        env_prefix="GITHUB_STAR_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # GitHub 配置
    github_token: str = ""
    github_username: str = ""

    # Qdrant 配置
    qdrant: QdrantConfig = QdrantConfig()

    # Gitea 配置
    gitea: GiteaConfig = GiteaConfig()

    # 数据库配置
    database: DatabaseConfig = DatabaseConfig()

    # 服务器配置
    server: ServerConfig = ServerConfig()

    # LLM 配置 (用于 RAG)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    @property
    def db_path(self) -> Path:
        """获取数据库完整路径"""
        return Path(self.database.path).expanduser()

    @classmethod
    def load_from_yaml(cls, path: Path) -> "Config":
        """从 YAML 文件加载配置"""
        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """加载配置

        优先级: 环境变量 > config.yaml > 默认值
        """
        if config_path is None:
            config_path = os.environ.get(
                "GITHUB_STAR_CONFIG",
                "~/.github-star-mcp/config.yaml"
            )

        config_file = Path(config_path).expanduser()
        return cls.load_from_yaml(config_file)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def set_config(config: Config) -> None:
    """设置全局配置实例"""
    global _config
    _config = config
