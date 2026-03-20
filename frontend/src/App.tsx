import { useEffect, useState, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SyncStatusCard } from './components/SyncStatus';
import { VectorStatusCard } from './components/VectorStatus';
import { ActionButtons } from './components/ActionButtons';
import { MCPInfo } from './components/MCPInfo';
import { usePolling } from './hooks/usePolling';
import { useTheme } from './hooks/useTheme';
import { fetchStatus, startSync, cancelSync, resetSync, startVectorize, cancelVectorize } from '@/api/sync';
import type { SyncState, InitialData } from './types';
import { Github, Sun, Moon } from 'lucide-react';

function App() {
  const { theme, toggle } = useTheme();
  const [initialData, setInitialData] = useState<InitialData | null>(null);
  const [state, setState] = useState<SyncState | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isVectorizing, setIsVectorizing] = useState(false);
  const stateRef = useRef<SyncState | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/sync/status', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((state) => {
        const newState: SyncState = {
          status: state.status || 'pending',
          synced_projects: state.synced_projects || 0,
          synced_readme: state.synced_readme || 0,
          readme_total: state.readme_total || 0,
          readme_current: state.readme_current || 0,
          readme_progress: state.readme_progress || 0,
          vectorized_projects: state.vectorized_projects || 0,
          vector_status: {
            status: state.vector_status?.status || 'pending',
            progress: state.vector_status?.progress || 0,
            total: state.vector_status?.total || 0,
            current: state.vector_status?.current || 0,
            error: state.vector_status?.error,
          },
        };
        setInitialData({
          status: newState.status,
          readme_total: newState.readme_total,
          readme_current: newState.readme_current,
          readme_progress: newState.readme_progress,
          vector_status: newState.vector_status.status,
          vector_progress: newState.vector_status.progress,
          vector_current: newState.vector_status.current,
          vector_total: newState.vector_status.total,
          vector_error: newState.vector_status.error,
          username: '',
          synced_projects: newState.synced_projects,
          synced_readme: newState.synced_readme,
          vectorized_projects: newState.vectorized_projects,
          require_sync: true,
        });
        stateRef.current = newState;
        setState(newState);
      })
      .catch((err) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setInitError(err instanceof Error ? err.message : '获取数据失败，请刷新重试');
        console.error('获取初始数据失败:', err);
      });
    return () => controller.abort();
  }, []);

  const shouldPoll = state?.status === 'syncing' || state?.status === 'loading_readme' || state?.vector_status.status === 'vectorizing';

  const poll = useCallback(async () => {
    try {
      const data = await fetchStatus();
      stateRef.current = data;
      setState(data);
    } catch (err) {
      console.error('Poll failed:', err);
    }
  }, []);

  usePolling(poll, 2000, shouldPoll ?? false);

  const handleStartSync = async () => {
    setIsSyncing(true);
    try {
      const result = await startSync();
      if (result.error) {
        alert(result.error);
      }
    } catch (err) {
      alert('启动同步失败，请重试');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCancelSync = async () => {
    try {
      await cancelSync();
      window.location.reload();
    } catch (err) {
      console.error('取消同步失败:', err);
    }
  };

  const handleResetSync = async () => {
    if (!confirm('确定要清空所有同步数据并重新开始吗？')) {
      return;
    }
    try {
      await resetSync();
      window.location.reload();
    } catch (err) {
      console.error('重置失败:', err);
    }
  };

  const handleStartVectorize = async () => {
    setIsVectorizing(true);
    try {
      const result = await startVectorize();
      if (result.error) {
        alert(result.error);
      }
    } catch (err) {
      alert('启动向量化失败，请重试');
    } finally {
      setIsVectorizing(false);
    }
  };

  const handleCancelVectorize = async () => {
    try {
      await cancelVectorize();
      window.location.reload();
    } catch (err) {
      console.error('取消向量化失败:', err);
    }
  };

  if (initError) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <Card className="w-full max-w-sm">
          <CardContent className="p-8">
            <div role="alert" className="text-center space-y-4">
              <p className="text-[15px] text-foreground">加载失败</p>
              <p className="text-[13px] text-muted-foreground leading-relaxed">{initError}</p>
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
              >
                重新加载
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!initialData || !state) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardContent className="p-8">
            <p className="text-center text-muted-foreground text-[15px] animate-pulse">加载中...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const syncCompleted = state.status === 'completed';
  const canStartVectorize = syncCompleted && state.vector_status.status === 'pending';
  const serverVectorizing = state.vector_status.status === 'vectorizing';

  return (
    <div className="min-h-screen py-20 px-6 bg-background">
      <div className="max-w-2xl mx-auto">
        <Card className="w-full">
          <CardHeader className="text-center pb-0">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Github className="w-5 h-5 text-muted-foreground" />
                <h1 className="text-[15px] font-semibold tracking-tight">GitHub Stars MCP</h1>
              </div>
              <Button variant="ghost" size="icon" onClick={toggle} aria-label={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}>
                {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </Button>
            </div>
            {initialData.username && (
              <p className="text-[14px] text-muted-foreground tracking-wide">
                {initialData.username}
              </p>
            )}
          </CardHeader>

          <CardContent className="space-y-3" aria-live="polite">
            <SyncStatusCard
              status={state.status}
              syncedProjects={state.synced_projects}
              syncedReadme={state.synced_readme}
              vectorizedProjects={state.vectorized_projects}
              readmeCurrent={state.readme_current}
              readmeTotal={state.readme_total}
            />

            <VectorStatusCard
              status={state.vector_status.status}
              progress={state.vector_status.progress}
              current={state.vector_status.current}
              total={state.vector_status.total}
              error={state.vector_status.error}
              onStart={handleStartVectorize}
              onCancel={handleCancelVectorize}
              canStart={canStartVectorize}
              isRunning={serverVectorizing || isVectorizing}
              isLoading={isVectorizing}
            />

            <ActionButtons
              status={state.status}
              onStart={handleStartSync}
              onCancel={handleCancelSync}
              onReset={handleResetSync}
              isLoading={isSyncing}
            />

            <MCPInfo requireSync={initialData.require_sync} syncCompleted={syncCompleted} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default App;
