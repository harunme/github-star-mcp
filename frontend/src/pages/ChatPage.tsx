import { useState, useCallback, useEffect } from 'react';
import {
  MessageSquare,
  Compass,
  Loader2,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { sendChat, ChatMessage } from '@/api/chat';
import { checkHealth, HealthReport } from '@/api/health';

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

  return (
    <>
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
