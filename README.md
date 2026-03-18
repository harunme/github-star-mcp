# GitHub Stars MCP Server

获取 GitHub stars 列表、向量化存储、RAG 问答、备份到 Gitea 的 MCP 服务。

## 功能

- 📥 **list_stars** - 获取 GitHub stars 列表
- 🔄 **sync_stars** - 同步 stars 到本地并向量化
- 🔍 **search_projects** - 向量语义搜索项目
- 💬 **ask_about_projects** - 基于 RAG 智能问答
- 📦 **fork_to_gitea** - 备份项目到 Gitea
- 📋 **list_backed_up** - 列出已备份项目
- ℹ️ **get_project_info** - 获取项目详情

## 安装

```bash
cd github-star-mcp
pip install -e .
```

## 配置

创建 `~/.github-star-mcp/config.yaml`:

```yaml
github_token: your_github_token
github_username: your_username

qdrant:
  host: localhost
  port: 6333

gitea:
  url: http://localhost:3000
  token: your_gitea_token
  username: your_username

anthropic_api_key: your_anthropic_api_key

database:
  path: ~/.github-star-mcp/data.db
```

## 使用

### 命令行运行

```bash
github-star-mcp --github-token your_token --github-username your_user
```

### Claude Desktop 配置

在 `~/Library/Application Support/Claude/claude_desktop_config.json` 中添加:

```json
{
  "mcpServers": {
    "github-star-mcp": {
      "command": "github-star-mcp",
      "env": {
        "GITHUB_STAR_GITHUB_TOKEN": "your_token",
        "GITHUB_STAR_GITHUB_USERNAME": "your_username",
        "ANTHROPIC_API_KEY": "your_key"
      }
    }
  }
}
```

## 依赖服务

- **Qdrant**: 向量数据库 (默认 localhost:6333)
- **Gitea**: 可选，用于备份
- **SQLite**: 自动创建，用于本地存储
- **Anthropic API**: 可选，用于 RAG 问答
