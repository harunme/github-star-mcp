export type SyncStatus = 'pending' | 'syncing' | 'loading_readme' | 'completed';
export type VectorStatus = 'pending' | 'vectorizing' | 'completed';

export interface VectorState {
  status: VectorStatus;
  progress: number;
  total: number;
  current: number;
  error?: string;
}

export interface SyncState {
  status: SyncStatus;
  synced_projects: number;
  synced_readme: number;
  readme_total: number;
  readme_current: number;
  readme_progress: number;
  vectorized_projects: number;
  vector_status: VectorState;
}

export interface InitialData {
  status: SyncStatus;
  readme_total: number;
  readme_current: number;
  readme_progress: number;
  vector_status: VectorStatus;
  vector_progress: number;
  vector_current: number;
  vector_total: number;
  vector_error?: string;
  username: string;
  synced_projects: number;
  synced_readme: number;
  vectorized_projects: number;
  require_sync: boolean;
}

export interface ApiResponse<T = unknown> {
  error?: string;
  message?: string;
  status?: SyncState | VectorState;
  data?: T;
  [key: string]: T | undefined | string | SyncState | VectorState;
}
