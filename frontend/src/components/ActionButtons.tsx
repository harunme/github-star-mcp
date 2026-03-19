import type { SyncStatus } from '../types';

interface Props {
  status: SyncStatus;
  onStart: () => void;
  onCancel: () => void;
  onReset: () => void;
}

export function ActionButtons({ status, onStart, onCancel, onReset }: Props) {
  if (status === 'pending') {
    return (
      <button className="btn btn-primary" onClick={onStart}>
        <span>🚀</span> 开始同步 GitHub Stars
      </button>
    );
  }

  if (status === 'syncing' || status === 'loading_readme') {
    return (
      <button className="btn btn-danger" onClick={onCancel}>
        <span>✕</span> 取消同步
      </button>
    );
  }

  if (status === 'completed') {
    return (
      <button className="btn btn-secondary" onClick={onReset}>
        <span>↻</span> 重新同步
      </button>
    );
  }

  if (status === 'failed') {
    return (
      <>
        <button className="btn btn-primary" onClick={onStart}>
          <span>↻</span> 重试同步
        </button>
        <button className="btn btn-secondary" onClick={onReset} style={{ marginTop: '8px' }}>
          <span>🗑</span> 清空数据并重新开始
        </button>
      </>
    );
  }

  return null;
}
