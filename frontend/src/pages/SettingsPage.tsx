import { useState, useEffect } from 'react';
import { Save, Loader2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { getConfig, updateConfig, AppConfig } from '@/api/config';

export function SettingsPage() {
  const [config, setConfig] = useState<AppConfig>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await getConfig();
      setConfig(data);
    } catch (err) {
      setError('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);

    try {
      await updateConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (path: string, value: unknown) => {
    const keys = path.split('.');
    setConfig((prev) => {
      const updated = { ...prev };
      let current: Record<string, unknown> = updated;

      for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        if (!current[key]) {
          current[key] = {};
        }
        current[key] = { ...(current[key] as Record<string, unknown>) };
        current = current[key] as Record<string, unknown>;
      }

      current[keys[keys.length - 1]] = value;
      return updated;
    });
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">设置</h1>
            <p className="text-sm text-muted-foreground">配置你的 GitHub Stars MCP</p>
          </div>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : saved ? (
              <Check className="w-4 h-4 mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {saved ? '已保存' : '保存'}
          </Button>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* GitHub 配置 */}
        <Card>
          <CardHeader>
            <CardTitle>GitHub</CardTitle>
            <CardDescription>GitHub 账号和访问令牌</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">用户名</label>
              <input
                type="text"
                value={config.github_username || ''}
                onChange={(e) => handleChange('github_username', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="your-github-username"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Personal Access Token</label>
              <input
                type="password"
                value={config.github_token || ''}
                onChange={(e) => handleChange('github_token', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="ghp_xxxxx"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                需要 repo 和 read:user 权限
              </p>
            </div>
          </CardContent>
        </Card>

        {/* LLM 配置 */}
        <Card>
          <CardHeader>
            <CardTitle>大语言模型 (LLM)</CardTitle>
            <CardDescription>选择和配置 AI 模型</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Provider</label>
              <select
                value={config.llm?.provider || 'anthropic'}
                onChange={(e) => handleChange('llm.provider', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="anthropic">Anthropic</option>
                <option value="openai">OpenAI</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">模型</label>
              <input
                type="text"
                value={config.llm?.model || ''}
                onChange={(e) => handleChange('llm.model', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={
                  config.llm?.provider === 'anthropic' ? 'claude-sonnet-4-20250514' :
                  config.llm?.provider === 'openai' ? 'gpt-4o' :
                  'llama3.2'
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">API Key</label>
              <input
                type="password"
                value={config.llm?.api_key || ''}
                onChange={(e) => handleChange('llm.api_key', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={config.llm?.provider === 'ollama' ? '不需要 (留空)' : 'sk-ant-...'}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Base URL</label>
              <input
                type="text"
                value={config.llm?.base_url || ''}
                onChange={(e) => handleChange('llm.base_url', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={
                  config.llm?.provider === 'ollama' ? 'http://localhost:11434' :
                  config.llm?.provider === 'openai' ? 'https://api.openai.com/v1' : ''
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Embedder 配置 */}
        <Card>
          <CardHeader>
            <CardTitle>向量嵌入 (Embedder)</CardTitle>
            <CardDescription>用于语义搜索的嵌入模型</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Provider</label>
              <select
                value={config.embedder?.provider || 'sentence-transformers'}
                onChange={(e) => handleChange('embedder.provider', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="sentence-transformers">Sentence Transformers (本地)</option>
                <option value="openai">OpenAI</option>
                <option value="cohere">Cohere</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">模型</label>
              <input
                type="text"
                value={config.embedder?.model || ''}
                onChange={(e) => handleChange('embedder.model', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={
                  config.embedder?.provider === 'openai' ? 'text-embedding-3-small' :
                  config.embedder?.provider === 'cohere' ? 'embed-english-v3.0' :
                  config.embedder?.provider === 'ollama' ? 'nomic-embed-text' :
                  'all-MiniLM-L6-v2'
                }
              />
            </div>
            {!['sentence-transformers'].includes(config.embedder?.provider || '') && (
              <div>
                <label className="block text-sm font-medium mb-1">API Key</label>
                <input
                  type="password"
                  value={config.embedder?.api_key || ''}
                  onChange={(e) => handleChange('embedder.api_key', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="sk-..."
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium mb-1">Base URL</label>
              <input
                type="text"
                value={config.embedder?.base_url || ''}
                onChange={(e) => handleChange('embedder.base_url', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={
                  config.embedder?.provider === 'ollama' ? 'http://localhost:11434' :
                  config.embedder?.provider === 'openai' ? 'https://api.openai.com/v1' : 'https://api.cohere.ai'
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* 文本分割配置 */}
        <Card>
          <CardHeader>
            <CardTitle>文本分割</CardTitle>
            <CardDescription>README 文档分块设置</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Chunk Size: {config.text_split?.chunk_size || 1024}
              </label>
              <input
                type="range"
                min="512"
                max="4096"
                step="128"
                value={config.text_split?.chunk_size || 1024}
                onChange={(e) => handleChange('text_split.chunk_size', parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>512</span>
                <span>4096</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Chunk Overlap: {config.text_split?.chunk_overlap || 128}
              </label>
              <input
                type="range"
                min="64"
                max="512"
                step="32"
                value={config.text_split?.chunk_overlap || 128}
                onChange={(e) => handleChange('text_split.chunk_overlap', parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>64</span>
                <span>512</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gitea 配置 */}
        <Card>
          <CardHeader>
            <CardTitle>Gitea 备份</CardTitle>
            <CardDescription>备份仓库到 Gitea</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Gitea URL</label>
              <input
                type="text"
                value={config.gitea?.url || 'http://localhost:3000'}
                onChange={(e) => handleChange('gitea.url', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="http://localhost:3000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">用户名</label>
              <input
                type="text"
                value={config.gitea?.username || ''}
                onChange={(e) => handleChange('gitea.username', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="your-gitea-username"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Token</label>
              <input
                type="password"
                value={config.gitea?.token || ''}
                onChange={(e) => handleChange('gitea.token', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="your-gitea-token"
              />
            </div>
          </CardContent>
        </Card>

        {/* 页面偏好 */}
        <Card>
          <CardHeader>
            <CardTitle>页面偏好</CardTitle>
            <CardDescription>界面显示设置</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">主题</label>
              <select
                value={config.theme || 'system'}
                onChange={(e) => handleChange('theme', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="system">跟随系统</option>
                <option value="light">浅色</option>
                <option value="dark">深色</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                每页数量: {config.page_size || 20}
              </label>
              <input
                type="range"
                min="10"
                max="100"
                step="10"
                value={config.page_size || 20}
                onChange={(e) => handleChange('page_size', parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>10</span>
                <span>100</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
