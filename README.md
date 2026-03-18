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

1. Copy the config template:

```bash
cp config.yaml.example ~/.github-star-mcp/config.yaml
```

2. Edit `~/.github-star-mcp/config.yaml` with your settings:

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
        "ANTHROPIC_API_KEY": "your_key"
      }
    }
  }
}
```

## Dependencies

- **Qdrant** - Vector database (default localhost:6333)
- **Gitea** - Optional, for backup
- **SQLite** - Auto-created, for local storage
- **Anthropic API** - Optional, for RAG Q&A
