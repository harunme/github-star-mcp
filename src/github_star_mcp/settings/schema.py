"""设置配置 Schema"""
from typing import ClassVar, Literal

from pydantic import BaseModel, Field


class GiteaConfig(BaseModel):
    """Gitea 配置"""
    url: str = "http://localhost:3000"
    token: str = ""
    username: str = ""


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    base_url: str = ""

    # 模型列表 (ClassVar)
    anthropic_models: ClassVar[list[str]] = [
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-haiku-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    openai_models: ClassVar[list[str]] = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]

    ollama_models: ClassVar[list[str]] = [
        "llama3.2",
        "llama3.1",
        "qwen2.5",
        "deepseek-v2",
    ]


class EmbedderConfig(BaseModel):
    """Embedder 配置"""
    provider: Literal["openai", "cohere", "sentence-transformers", "ollama"] = "sentence-transformers"
    model: str = "all-MiniLM-L6-v2"
    api_key: str = ""
    base_url: str = ""

    # sentence-transformers 模型
    sentence_transformers_models: ClassVar[list[str]] = [
        "all-MiniLM-L6-v2",  # 384 维
        "all-mpnet-base-v2",  # 768 维
        "paraphrase-multilingual-MiniLM-L12-v2",  # 384 维, 多语言
    ]

    openai_models: ClassVar[list[str]] = [
        "text-embedding-3-small",  # 1536 维
        "text-embedding-3-large",  # 3072 维
        "text-embedding-ada-002",  # 1536 维
    ]

    cohere_models: ClassVar[list[str]] = [
        "embed-english-v3.0",  # 1024 维
        "embed-english-light-v3.0",
        "embed-multilingual-v3.0",
    ]

    ollama_models: ClassVar[list[str]] = [
        "nomic-embed-text",  # 768 维
        "mxbai-embed-large",
    ]


class TextSplitConfig(BaseModel):
    """文本分割配置"""
    chunk_size: int = Field(default=1024, ge=512, le=4096)
    chunk_overlap: int = Field(default=128, ge=64, le=512)


class ServerConfig(BaseModel):
    """服务器配置"""
    mode: Literal["guided", "mcp"] = "guided"
    host: str = "0.0.0.0"
    port: int = 8080
    require_sync: bool = True


class DatabaseConfig(BaseModel):
    """数据库配置"""
    path: str = "~/.github-star-mcp/data.db"


class ConfigSchema:
    """配置 Schema 定义（用于前端表单生成）"""

    llm_providers = (
        LLMConfig().anthropic_models +
        LLMConfig().openai_models +
        LLMConfig().ollama_models
    )
    embedder_providers = (
        EmbedderConfig().sentence_transformers_models +
        EmbedderConfig().openai_models +
        EmbedderConfig().cohere_models +
        EmbedderConfig().ollama_models
    )

    fields = {
        "github_token": {
            "type": "password",
            "label": "GitHub Token",
            "description": "GitHub Personal Access Token",
            "required": True,
        },
        "github_username": {
            "type": "text",
            "label": "GitHub Username",
            "description": "你的 GitHub 用户名",
            "required": True,
        },
        "gitea_url": {
            "type": "text",
            "label": "Gitea URL",
            "description": "Gitea 服务器地址",
            "default": "http://localhost:3000",
        },
        "gitea_token": {
            "type": "password",
            "label": "Gitea Token",
            "description": "Gitea API Token",
        },
        "gitea_username": {
            "type": "text",
            "label": "Gitea Username",
            "description": "Gitea 用户名",
        },
        "llm_provider": {
            "type": "select",
            "label": "LLM Provider",
            "options": ["anthropic", "openai", "ollama"],
            "default": "anthropic",
        },
        "llm_api_key": {
            "type": "password",
            "label": "LLM API Key",
            "description": "API Key (Anthropic/OpenAI)",
        },
        "llm_model": {
            "type": "select",
            "label": "LLM Model",
            "options": {
                "anthropic": LLMConfig().anthropic_models,
                "openai": LLMConfig().openai_models,
                "ollama": LLMConfig().ollama_models,
            },
            "default": "claude-sonnet-4-20250514",
        },
        "llm_base_url": {
            "type": "text",
            "label": "LLM Base URL",
            "description": "自定义 API 地址 (Ollama)",
            "default": "",
        },
        "embedder_provider": {
            "type": "select",
            "label": "Embedder Provider",
            "options": ["sentence-transformers", "openai", "cohere", "ollama"],
            "default": "sentence-transformers",
        },
        "embedder_model": {
            "type": "select",
            "label": "Embedder Model",
            "options": {
                "sentence-transformers": EmbedderConfig().sentence_transformers_models,
                "openai": EmbedderConfig().openai_models,
                "cohere": EmbedderConfig().cohere_models,
                "ollama": EmbedderConfig().ollama_models,
            },
            "default": "all-MiniLM-L6-v2",
        },
        "embedder_api_key": {
            "type": "password",
            "label": "Embedder API Key",
            "description": "OpenAI/Cohere API Key",
        },
        "embedder_base_url": {
            "type": "text",
            "label": "Embedder Base URL",
            "description": "自定义 Embedder 地址 (Ollama)",
            "default": "http://localhost:11434",
        },
        "chunk_size": {
            "type": "slider",
            "label": "Chunk Size",
            "min": 512,
            "max": 4096,
            "step": 128,
            "default": 1024,
        },
        "chunk_overlap": {
            "type": "slider",
            "label": "Chunk Overlap",
            "min": 64,
            "max": 512,
            "step": 32,
            "default": 128,
        },
        "theme": {
            "type": "select",
            "label": "Theme",
            "options": ["system", "light", "dark"],
            "default": "system",
        },
        "page_size": {
            "type": "slider",
            "label": "Page Size",
            "min": 10,
            "max": 100,
            "step": 10,
            "default": 20,
        },
    }
