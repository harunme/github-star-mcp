# GitHub Stars MCP Server

A Model Context Protocol (MCP) server for managing GitHub stars with vector storage, RAG-based Q&A, and Gitea backup.

## Features

- **list_stars** - List GitHub starred repositories
- **sync_stars** - Sync and vectorize stars
- **search_projects** - Semantic vector search
- **ask_about_projects** - RAG-based Q&A
- **fork_to_gitea** - Backup projects to Gitea
- **list_backed_up** - List backed up projects
- **get_project_info** - Get project details

## Installation

```bash
cd github-star-mcp
pip install -e .
```

## Configuration

1. Create the config directory and copy the config template:

```bash
mkdir -p ~/.github-star-mcp
cp config.yaml.example ~/.github-star-mcp/config.yaml
```

2. Edit `~/.github-star-mcp/config.yaml` with your settings:

```yaml
github_token: your_github_token
github_username: your_username

gitea:
  url: http://localhost:3000
  token: your_gitea_token
  username: your_username

llm:
  provider: anthropic  # anthropic | openai | ollama
  api_key: your_api_key
  model: claude-sonnet-4-20250514
  base_url: ""  # Custom base URL for OpenAI compatible APIs

database:
  path: ~/.github-star-mcp/data.db
```

## Usage

### Command Line

```bash
github-star-mcp --github-token your_token --github-username your_user
```

### Claude Desktop

Add the following to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github-star-mcp": {
      "command": "github-star-mcp",
      "env": {
        "GITHUB_STAR_GITHUB_TOKEN": "your_token",
        "GITHUB_STAR_GITHUB_USERNAME": "your_user",
        "LLM_API_KEY": "your_key"
      }
    }
  }
}
```

## Dependencies

- **LanceDB** - Embedded vector database (auto-created at `~/.github-star-mcp/vectors/`)
- **Gitea** - Optional, for backup
- **SQLite** - Auto-created, for local storage
- **Anthropic API** - Optional, for RAG Q&A
