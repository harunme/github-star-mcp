import { useEffect, useState, useCallback } from 'react';
import { SyncStatusCard } from './components/SyncStatus';
import { VectorStatusCard } from './components/VectorStatus';
import { ActionButtons } from './components/ActionButtons';
import { MCPInfo } from './components/MCPInfo';
import { usePolling } from './hooks/usePolling';
import { fetchInitialData, fetchStatus, startSync, cancelSync, resetSync, startVectorize, cancelVectorize } from './api/sync';
import type { SyncState, InitialData } from './types';

function App() {
  const [initialData, setInitialData] = useState<InitialData | null>(null);
  const [state, setState] = useState<SyncState | null>(null);

  useEffect(() => {
    fetchInitialData().then((data) => {
      setInitialData(data);
      setState({
        status: data.status,
        synced_projects: data.synced_projects,
        synced_readme: data.synced_readme,
        readme_total: data.readme_total,
        readme_current: data.readme_current,
        readme_progress: data.readme_progress,
        vectorized_projects: data.vectorized_projects,
        vector_status: {
          status: data.vector_status,
          progress: data.vector_progress,
          total: data.vector_total,
          current: data.vector_current,
          error: data.vector_error,
        },
      });
    });
  }, []);

  const shouldPoll = state?.status === 'syncing' || state?.status === 'loading_readme' || state?.vector_status.status === 'vectorizing';

  const poll = useCallback(async () => {
    if (!state) return;
    try {
      const data = await fetchStatus();
      setState(data);

      // If completed, reload the page
      if (data.status === 'completed') {
        window.location.reload();
      }
      if (data.vector_status.status === 'completed') {
        window.location.reload();
      }
    } catch (err) {
      console.error('Poll failed:', err);
    }
  }, [state]);

  usePolling(poll, 2000, shouldPoll ?? false);

  const handleStartSync = async () => {
    try {
      const result = await startSync();
      if (result.error) {
        alert(result.error);
        return;
      }
    } catch (err) {
      alert('启动同步失败，请重试');
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
    try {
      const result = await startVectorize();
      if (result.error) {
        alert(result.error);
        return;
      }
      // Don't reload - let polling update state naturally
    } catch (err) {
      alert('启动向量化失败，请重试');
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

  if (!initialData || !state) {
    return (
      <div className="container">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>加载中...</p>
        </div>
      </div>
    );
  }

  const syncCompleted = state.status === 'completed';
  const canStartVectorize = syncCompleted && state.vector_status.status === 'pending';
  const isVectorizing = state.vector_status.status === 'vectorizing';

  return (
    <div className="container">
      <div className="header">
        <h1>GitHub Stars MCP Server</h1>
        <p>用户: <span className="username">{initialData.username}</span></p>
      </div>

      <SyncStatusCard
        status={state.status}
        syncedProjects={state.synced_projects}
        syncedReadme={state.synced_readme}
        vectorizedProjects={state.vectorized_projects}
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
        isRunning={isVectorizing}
      />

      <ActionButtons
        status={state.status}
        onStart={handleStartSync}
        onCancel={handleCancelSync}
        onReset={handleResetSync}
      />

      <MCPInfo requireSync={initialData.require_sync} syncCompleted={syncCompleted} />
    </div>
  );
}

export default App;
