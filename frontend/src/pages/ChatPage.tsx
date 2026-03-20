import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Compass,
  Loader2,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  Settings,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { ActionButtons } from '@/components/ActionButtons';
import { usePolling } from '@/hooks/usePolling';
import { sendChat, ChatMessage } from '@/api/chat';
import { checkHealth, HealthReport } from '@/api/health';
import { fetchStatus, startVectorize, cancelVectorize } from '@/api/sync';
import { getConfig } from '@/api/config';
import type { SyncState } from '../types';

type ChatTab = 'chat' | 'discover';

export function ChatPage() {
  const [activeTab, setActiveTab] = useState<ChatTab>('chat');

  const tabs: { id: ChatTab; label: string; icon: React.ElementType }[] = [
    { id: 'chat', label: '对话', icon: MessageSquare },
    { id: 'discover', label: '发现', icon: Compass },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-semibold">GitHub Stars</h1>
        <p className="text-sm text-muted-foreground">
          语义搜索 + 健康检测
        </p>
      </div>

      {/* Tabs */}
      <div className="px-4 pt-4 border-b border-border">
        <div className="flex gap-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
                activeTab === id
                  ? 'bg-muted text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {activeTab === 'chat' ? (
          <ChatTab />
        ) : (
          <DiscoverTab />
        )}
      </div>
    </div>
  );
}

// ===== Chat Tab =====

function ChatTab() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncState, setSyncState] = useState<SyncState | null>(null);
  const [githubConfigured, setGithubConfigured] = useState<boolean | null>(null);
  const navigate = useNavigate();

  const fetchSyncState = useCallback(async () => {
    try {
      const state = await fetchStatus();
      setSyncState(state);
    } catch {
      // Ignore
    }
  }, []);

  const checkGithubConfig = useCallback(async () => {
    try {
      const cfg = await getConfig();
      setGithubConfigured(!!cfg.github_token && !!cfg.github_username);
    } catch {
      setGithubConfigured(false);
    }
  }, []);

  useEffect(() => {
    fetchSyncState();
    checkGithubConfig();
  }, [fetchSyncState, checkGithubConfig]);

  // Polling: 3s when syncing/loading_readme, 10s otherwise
  const isActive =
    syncState?.status === 'syncing' ||
    syncState?.status === 'loading_readme' ||
    syncState?.vector_status?.status === 'vectorizing';
  const pollingInterval = isActive ? 3000 : 10000;
  usePolling(fetchSyncState, pollingInterval, !!syncState);

  const handleSend = useCallback(async (message: string) => {
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChat(message);
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '发送失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleClear = useCallback(async () => {
    if (messages.length === 0) return;
    if (!confirm('确定要清除聊天历史吗？')) return;
    try {
      await fetch('/api/chat/clear', { method: 'POST' });
      setMessages([]);
    } catch {
      // Ignore errors
    }
  }, [messages.length]);

  const handleStartVectorize = async () => {
    try {
      await startVectorize();
      await fetchSyncState();
    } catch (err) {
      console.error('启动向量化失败:', err);
    }
  };

  const handleCancelVectorize = async () => {
    try {
      await cancelVectorize();
      await fetchSyncState();
    } catch (err) {
      console.error('取消向量化失败:', err);
    }
  };

  // Loading state
  if (githubConfigured === null || !syncState) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // No GitHub config → show banner
  if (!githubConfigured) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        <div className="bg-primary/10 border border-primary/20 rounded-xl p-6 text-center">
          <Sparkles className="w-8 h-8 mx-auto mb-3 text-primary" />
          <h2 className="text-lg font-semibold mb-2">欢迎使用 GitHub Stars</h2>
          <p className="text-sm text-muted-foreground mb-4">
            请先在设置中配置 GitHub Token 和用户名
          </p>
          <Button onClick={() => navigate('/settings')}>
            <Settings className="mr-2 w-4 h-4" />
            前往设置
          </Button>
        </div>
      </div>
    );
  }

  const { status, vector_status } = syncState;
  const syncedCount = syncState.synced_projects || 0;
  const readmeCount = syncState.synced_readme || 0;
  const vectorizedCount = syncState.vectorized_projects || 0;

  const isSyncing = status === 'syncing' || status === 'loading_readme';
  const isVectorizing = vector_status?.status === 'vectorizing';
  const isCompleted = status === 'completed';

  return (
    <>
      {/* SyncPanel: always visible when GitHub is configured */}
      <div className="px-4 py-3 border-b border-border bg-muted/30">
        {/* Stats row */}
        <div className="flex gap-4 text-sm mb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">已入库:</span>
            <Badge variant="secondary">{syncedCount}</Badge>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">README:</span>
            <Badge variant="secondary">{readmeCount}</Badge>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">向量化:</span>
            <Badge variant="secondary">{vectorizedCount}</Badge>
          </div>
        </div>

        {/* Progress */}
        {(isSyncing || isVectorizing) && (
          <div className="mb-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>
                {isSyncing
                  ? `README 加载中 ${syncState.readme_current || 0}/${syncState.readme_total || 0}`
                  : `向量化中 ${vector_status?.current || 0}/${vector_status?.total || 0}`}
              </span>
              <span>
                {isSyncing
                  ? syncState.readme_progress || 0
                  : vector_status?.progress || 0}
                %
              </span>
            </div>
            <Progress
              value={isSyncing ? syncState.readme_progress : vector_status?.progress || 0}
              className="h-1.5"
            />
          </div>
        )}

        {/* Ready message */}
        {isCompleted && vector_status?.status === 'completed' && (
          <p className="text-xs text-green-600 dark:text-green-400 mb-2">
            ✓ 向量库已就绪，语义搜索功能已开启
          </p>
        )}

        {/* Action Buttons */}
        <ActionButtons status={status} isLoading={isSyncing} />

        {/* Vectorize button */}
        {isCompleted && vector_status?.status === 'pending' && (
          <Button
            variant="outline"
            onClick={handleStartVectorize}
            className="w-full mt-2"
            size="sm"
          >
            <Sparkles className="mr-2 w-4 h-4" />
            开始向量化
          </Button>
        )}
        {isVectorizing && (
          <Button
            variant="outline"
            onClick={handleCancelVectorize}
            className="w-full mt-2"
            size="sm"
          >
            取消向量化
          </Button>
        )}
      </div>

      {/* Chat area */}
      <MessageList messages={messages} />
      {error && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}
      <div className="p-4 border-t border-border">
        <ChatInput onSend={handleSend} onClear={handleClear} disabled={isLoading} />
      </div>
    </>
  );
}

// ===== Discover Tab =====

function DiscoverTab() {
  const [activeSection, setActiveSection] = useState<'health' | 'trending'>('health');
  const [healthReports, setHealthReports] = useState<HealthReport[]>([]);
  const [loading, setLoading] = useState(false);

  const handleHealthCheck = useCallback(async () => {
    setLoading(true);
    try {
      const result = await checkHealth();
      setHealthReports(result.reports);
    } catch (err) {
      console.error('Health check failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeSection === 'health' && healthReports.length === 0) {
      handleHealthCheck();
    }
  }, [activeSection]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Section selector */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant={activeSection === 'health' ? 'primary' : 'outline'}
          onClick={() => setActiveSection('health')}
        >
          <AlertTriangle className="w-4 h-4 mr-1" />
          健康检测
        </Button>
        <Button
          size="sm"
          variant={activeSection === 'trending' ? 'primary' : 'outline'}
          onClick={() => setActiveSection('trending')}
        >
          <TrendingUp className="w-4 h-4 mr-1" />
          Trending
        </Button>
      </div>

      {activeSection === 'health' && (
        <HealthSection reports={healthReports} loading={loading} onRefresh={handleHealthCheck} />
      )}

      {activeSection === 'trending' && <TrendingSection />}
    </div>
  );
}

function HealthSection({
  reports,
  loading,
  onRefresh,
}: {
  reports: HealthReport[];
  loading: boolean;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">不活跃项目检测</h2>
        <Button size="sm" variant="outline" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4 mr-1" />
          重新检测
        </Button>
      </div>

      {reports.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">所有项目都很健康！</p>
          </CardContent>
        </Card>
      ) : (
        reports.map((report) => (
          <Card key={report.project_id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{report.full_name}</span>
                    <Badge variant={report.score >= 50 ? 'secondary' : 'destructive'}>
                      {report.score}分
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {report.issues.map((issue) => (
                      <Badge key={issue} variant="outline" className="text-xs">
                        {issue.replace('_', ' ')}
                      </Badge>
                    ))}
                  </div>
                  {report.recommendations.length > 0 && (
                    <ul className="mt-2 text-xs text-muted-foreground space-y-1">
                      {report.recommendations.map((rec, i) => (
                        <li key={i}>• {rec}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

function TrendingSection() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          GitHub Trending
        </CardTitle>
        <CardDescription>当前热门的 GitHub 项目</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-center py-8 text-muted-foreground">
          <Compass className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="font-medium mb-2">功能开发中</p>
          <p className="text-sm">
            GitHub Trending 集成正在开发中，<br />
            稍后将支持按语言和时间范围筛选。
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
