import type { SyncStatus } from '../types';
import { Button } from '@/components/ui/button';
import { Rocket, X, RefreshCcw } from 'lucide-react';

interface Props {
  status: SyncStatus;
  onStart: () => void;
  onCancel: () => void;
  onReset: () => void;
  isLoading?: boolean;
}

export function ActionButtons({ status, onStart, onCancel, onReset, isLoading }: Props) {
  if (status === 'pending') {
    return (
      <Button onClick={onStart} className="w-full" disabled={isLoading}>
        <Rocket className="mr-2 w-4 h-4" />
        {isLoading ? '启动中...' : '开始同步 GitHub Stars'}
      </Button>
    );
  }

  if (status === 'syncing' || status === 'loading_readme') {
    return (
      <Button variant="outline" onClick={onCancel} className="w-full">
        <X className="mr-2 w-4 h-4" />
        取消同步
      </Button>
    );
  }

  if (status === 'completed') {
    return (
      <Button variant="secondary" onClick={onReset} className="w-full">
        <RefreshCcw className="mr-2 w-4 h-4" />
        重新同步
      </Button>
    );
  }

  return null;
}
