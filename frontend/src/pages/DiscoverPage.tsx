import { useState, useEffect } from 'react';
import { Compass, TrendingUp, Search, Loader2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { checkHealth, HealthReport } from '@/api/health';

type Tab = 'trending' | 'health' | 'search';

export function DiscoverPage() {
  const [activeTab, setActiveTab] = useState<Tab>('trending');
  const [healthReports, setHealthReports] = useState<HealthReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleHealthCheck = async () => {
    setLoading(true);
    try {
      const result = await checkHealth();
      setHealthReports(result.reports);
    } catch (err) {
      console.error('Health check failed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'health' && healthReports.length === 0) {
      handleHealthCheck();
    }
  }, [activeTab]);

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'trending', label: 'Trending', icon: TrendingUp },
    { id: 'health', label: '健康检测', icon: AlertTriangle },
    { id: 'search', label: '搜索', icon: Search },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-semibold">发现</h1>
        <p className="text-sm text-muted-foreground">
          探索 Trending 项目，检测健康状况
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
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'trending' && <TrendingTab />}
        {activeTab === 'health' && (
          <HealthTab reports={healthReports} loading={loading} onRefresh={handleHealthCheck} />
        )}
        {activeTab === 'search' && (
          <SearchTab query={searchQuery} onQueryChange={setSearchQuery} />
        )}
      </div>
    </div>
  );
}

function TrendingTab() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            GitHub Trending
          </CardTitle>
          <CardDescription>当前热门的 GitHub 项目</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <Compass className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="font-medium mb-2">功能开发中</p>
            <p className="text-sm">
              GitHub Trending 集成正在开发中，<br />
             稍后将支持按语言和时间范围筛选。
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>使用提示</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>• 在聊天中输入「发现 Trending」或「推荐项目」</p>
          <p>• 可以指定编程语言，如「发现 Python Trending」</p>
          <p>• AI 助理会根据你的 Stars 推荐相似项目</p>
        </CardContent>
      </Card>
    </div>
  );
}

function HealthTab({
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">健康检测结果</h2>
        <Button size="sm" variant="outline" onClick={onRefresh}>
          重新检测
        </Button>
      </div>

      {reports.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              所有项目都很健康！🎉
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <Card key={report.project_id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{report.full_name}</span>
                      <Badge
                        variant={report.score >= 50 ? 'secondary' : 'destructive'}
                      >
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
          ))}
        </div>
      )}
    </div>
  );
}

function SearchTab({
  query,
  onQueryChange,
}: {
  query: string;
  onQueryChange: (q: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="搜索项目..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>

      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="font-medium mb-2">语义搜索</p>
          <p className="text-sm">
            在左侧对话框中使用自然语言搜索，<br />
            例如：「找一些机器学习的项目」<br />
            或「推荐前端 UI 库」
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
