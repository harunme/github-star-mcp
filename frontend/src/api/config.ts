// API client for config endpoints

export interface AppConfig {
  github_token?: string;
  github_username?: string;
  gitea?: {
    url?: string;
    token?: string;
    username?: string;
  };
  llm?: {
    provider?: string;
    api_key?: string;
    model?: string;
    base_url?: string;
  };
  embedder?: {
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
  };
  text_split?: {
    chunk_size?: number;
    chunk_overlap?: number;
  };
  theme?: string;
  page_size?: number;
}

export async function getConfig(): Promise<AppConfig> {
  const response = await fetch('/api/config');
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function updateConfig(config: Partial<AppConfig>): Promise<AppConfig> {
  const response = await fetch('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function validateConfig(config: Partial<AppConfig>): Promise<{ valid: boolean; errors?: Array<{ field: string; message: string }> }> {
  const response = await fetch('/api/config/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return response.json();
}
