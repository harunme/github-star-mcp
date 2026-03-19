import type { SyncStatus } from '../types';

interface Props {
  status: SyncStatus;
  syncedProjects: number;
  vectorizedProjects: number;
  readmeProgress: number;
  readmeCurrent: number;
  readmeTotal: number;
  error?: string;
}

const statusLabels: Record<SyncStatus, string> = {
  pending: '等待同步',
  syncing: '同步仓库中',
  loading_readme: '加载 README',
  completed: '同步完成',
  failed: '同步失败',
};

const statusIcons: Record<SyncStatus, string> = {
  pending: 'pending',
  syncing: 'syncing',
  loading_readme: 'loading_readme',
  completed: 'completed',
  failed: 'failed',
};

export function SyncStatusCard({
  status,
  syncedProjects,
  vectorizedProjects,
  readmeProgress,
  readmeCurrent,
  readmeTotal,
  error,
}: Props) {
  const showReadmeProgress = status === 'syncing' || status === 'loading_readme';

  return (
    <div className="status-card">
      <h2>
        <span className={`status-icon ${statusIcons[status]}`}></span>
        <span>{statusLabels[status]}</span>
      </h2>

      <div className="stats">
        <div className="stat-item">
          <div className="stat-value">{syncedProjects}</div>
          <div className="stat-label">已入库</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{vectorizedProjects}</div>
          <div className="stat-label">已向量化</div>
        </div>
      </div>

      {showReadmeProgress && (
        <div className="progress-container">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${readmeProgress}%` }}></div>
          </div>
          <div className="progress-text">
            {readmeCurrent} / {readmeTotal > 0 ? readmeTotal : '?'} 个项目
          </div>
        </div>
      )}

      {error && status === 'failed' && (
        <div className="error-message">
          <strong>同步失败:</strong> {error}
        </div>
      )}

      {status === 'completed' && (
        <div className="success-message">所有 GitHub Stars 已同步完成！</div>
      )}
    </div>
  );
}
