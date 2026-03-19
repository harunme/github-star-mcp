import type { SyncStatus } from '../types';

interface Props {
  status: SyncStatus;
  syncedProjects: number;
  syncedReadme: number;
  vectorizedProjects: number;
}

const statusLabels: Record<SyncStatus, string> = {
  pending: '等待同步',
  syncing: '同步仓库中',
  loading_readme: '加载 README',
  completed: '同步完成',
};

const statusIcons: Record<SyncStatus, string> = {
  pending: 'pending',
  syncing: 'syncing',
  loading_readme: 'loading_readme',
  completed: 'completed',
};

export function SyncStatusCard({
  status,
  syncedProjects,
  syncedReadme,
  vectorizedProjects,
}: Props) {
  return (
    <div className="status-card">
      <h2>
        <span className={`status-icon ${statusIcons[status]}`}></span>
        <span>{statusLabels[status]}</span>
      </h2>

      <div className="stats-flow">
        <div className="stat-item">
          <div className="stat-label">已入库</div>
          <div className="stat-value">{syncedProjects}</div>
        </div>

        <div className="flow-arrow">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M13 5l7 7-7 7" />
          </svg>
        </div>

        <div className="stat-item">
          <div className="stat-label">已同步 README</div>
          <div className="stat-value">{syncedReadme}</div>
        </div>

        <div className="flow-arrow">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M13 5l7 7-7 7" />
          </svg>
        </div>

        <div className="stat-item">
          <div className="stat-label">已向量化</div>
          <div className="stat-value">{vectorizedProjects}</div>
        </div>
      </div>
    </div>
  );
}
