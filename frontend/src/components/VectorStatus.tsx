import type { VectorStatus } from '../types';

interface Props {
  status: VectorStatus;
  progress: number;
  current: number;
  total: number;
  error?: string;
  onStart?: () => void;
  onCancel?: () => void;
  canStart: boolean;
  isRunning: boolean;
}

const statusLabels: Record<VectorStatus, string> = {
  pending: '等待向量化',
  vectorizing: '向量化中',
  completed: '向量化完成',
};

export function VectorStatusCard({
  status,
  progress,
  current,
  total,
  error,
  onStart,
  onCancel,
  canStart,
  isRunning,
}: Props) {
  return (
    <div className="status-card">
      <h2>
        <span className={`status-icon ${status === 'vectorizing' ? 'syncing' : status === 'completed' ? 'completed' : 'pending'}`}></span>
        <span>{statusLabels[status]}</span>
      </h2>

      <div className="progress-container">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }}></div>
        </div>
        <div className="progress-text">
          {current} / {total > 0 ? total : '?'} 个项目
        </div>
      </div>

      {status === 'completed' && (
        <div className="success-message">
          向量化已完成，可以使用 MCP 搜索/问答功能。
        </div>
      )}

      {error && (
        <div className="error-message" style={{ marginTop: '12px', padding: '10px', background: '#fee2e2', borderRadius: '6px', color: '#dc2626' }}>
          <strong>向量化失败:</strong> {error}
        </div>
      )}

      <div id="vector-action-buttons">
        {canStart && !isRunning && (
          <button className="btn btn-primary" onClick={onStart}>
            <span>⚡</span> 开始向量化
          </button>
        )}

        {isRunning && (
          <button className="btn btn-danger" onClick={onCancel}>
            <span>✕</span> 取消向量化
          </button>
        )}
      </div>
    </div>
  );
}
