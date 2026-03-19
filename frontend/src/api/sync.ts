import type { ApiResponse, InitialData, SyncState } from '../types';

const API_BASE = '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    throw new Error(errorData.error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchInitialData(): Promise<InitialData> {
  // Read from window.__INITIAL_DATA__ injected by the server
  const data = (window as unknown as { __INITIAL_DATA__?: InitialData }).__INITIAL_DATA__;
  if (data) {
    return data;
  }

  // Fallback: fetch from API
  try {
    const response = await fetch(`${API_BASE}/sync/status`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const text = await response.text();
    if (!text) {
      throw new Error('Empty response');
    }
    const state = JSON.parse(text);
    return {
      status: state.status || 'pending',
      error: state.error || '',
      readme_total: state.readme_total || 0,
      readme_current: state.readme_current || 0,
      readme_progress: state.readme_progress || 0,
      vector_status: state.vector_status?.status || 'pending',
      vector_progress: state.vector_status?.progress || 0,
      vector_current: state.vector_status?.current || 0,
      vector_total: state.vector_status?.total || 0,
      vector_error: state.vector_status?.error || '',
      username: '',
      synced_projects: state.synced_projects || 0,
      vectorized_projects: state.vectorized_projects || 0,
      require_sync: true,
    };
  } catch {
    // Return default values if API fails
    return {
      status: 'pending',
      error: '',
      readme_total: 0,
      readme_current: 0,
      readme_progress: 0,
      vector_status: 'pending',
      vector_progress: 0,
      vector_current: 0,
      vector_total: 0,
      vector_error: '',
      username: '',
      synced_projects: 0,
      vectorized_projects: 0,
      require_sync: true,
    };
  }
}

export async function fetchStatus(): Promise<SyncState> {
  return fetchJson<SyncState>(`${API_BASE}/sync/status`);
}

export async function startSync(): Promise<ApiResponse> {
  return fetchJson<ApiResponse>(`${API_BASE}/sync/start`, { method: 'POST' });
}

export async function cancelSync(): Promise<ApiResponse> {
  return fetchJson<ApiResponse>(`${API_BASE}/sync/cancel`, { method: 'POST' });
}

export async function resetSync(): Promise<ApiResponse> {
  return fetchJson<ApiResponse>(`${API_BASE}/sync/reset`, { method: 'POST' });
}

export async function startVectorize(): Promise<ApiResponse> {
  return fetchJson<ApiResponse>(`${API_BASE}/vectorize/start`, { method: 'POST' });
}

export async function cancelVectorize(): Promise<ApiResponse> {
  return fetchJson<ApiResponse>(`${API_BASE}/vectorize/cancel`, { method: 'POST' });
}
