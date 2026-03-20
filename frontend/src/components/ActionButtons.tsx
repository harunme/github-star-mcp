import { useState } from 'react';
import type { SyncStatus } from '../types';
import { Button } from '@/components/ui/button';
import { Rocket, X, RefreshCcw, Database } from 'lucide-react';
import { startSync, cancelSync, rebuildVectorize } from '@/api/sync';

interface Props {
  status: SyncStatus;
  isLoading?: boolean;
}

export function ActionButtons({ status, isLoading }: Props) {
  const [rebuilding, setRebuilding] = useState(false);

  const handleRebuildVectorize = async () => {
    try {
      setRebuilding(true);
      await rebuildVectorize();
    } catch (err) {
      console.error('重建向量库失败:', err);
    } finally {
      setRebuilding(false);
    }
  };

  if (status === 'pending') {
    return (
      <Button
        onClick={() => startSync().catch(console.error)}
        className="w-full"
        disabled={isLoading}
      >
        <Rocket className="mr-2 w-4 h-4" />
        {isLoading ? '启动中...' : '开始同步 GitHub Stars'}
      </Button>
    );
  }

  if (status === 'syncing' || status === 'loading_readme') {
    return (
      <Button variant="outline" onClick={() => cancelSync().catch(console.error)} className="w-full">
        <X className="mr-2 w-4 h-4" />
        取消同步
      </Button>
    );
  }

  if (status === 'completed') {
    return (
      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={() => startSync().catch(console.error)}
          className="flex-1"
          disabled={isLoading}
        >
          <RefreshCcw className="mr-2 w-4 h-4" />
          增量同步
        </Button>
        <Button
          variant="outline"
          onClick={handleRebuildVectorize}
          disabled={rebuilding}
        >
          <Database className="mr-2 w-4 h-4" />
          {rebuilding ? '重建中...' : '重建向量库'}
        </Button>
      </div>
    );
  }

  return null;
}
