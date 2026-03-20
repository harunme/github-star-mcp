import type { ApiResponse, InitialData, SyncState } from '../types';

const API_BASE = '/api';
const FETCH_TIMEOUT = 10000; // 10s

async function fetchWithTimeout(url: string, options?: RequestInit, timeout = FETCH_TIMEOUT): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    clearTimeout(timer);
    return response;
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('请求超时，请检查网络连接');
    }
    throw err;
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetchWithTimeout(url, options);
  } catch (err) {
    if (err instanceof TypeError) {
      // Network failure (offline, CORS, etc.)
      throw new Error('网络连接失败，请检查网络');
    }
    throw err;
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    throw new Error(errorData.error || `请求失败 (${response.status})`);
  }

  return response.json();
}

export async function fetchInitialData(): Promise<InitialData> {
  try {
    const response = await fetchWithTimeout(`${API_BASE}/sync/status`);
    const state = await response.json();
    // vector_status 在 API 响应中是嵌套对象
    const vector_status = state.vector_status;
    return {
      status: state.status || 'pending',
      readme_total: state.readme_total || 0,
      readme_current: state.readme_current || 0,
      readme_progress: state.readme_progress || 0,
      vector_status: vector_status?.status || 'pending',
      vector_progress: vector_status?.progress || 0,
      vector_current: vector_status?.current || 0,
      vector_total: vector_status?.total || 0,
      vector_error: vector_status?.error,
      username: '',
      synced_projects: state.synced_projects || 0,
      synced_readme: state.synced_readme || 0,
      vectorized_projects: state.vectorized_projects || 0,
      require_sync: true,
    };
  } catch {
    // Return default values if API fails
    return {
      status: 'pending',
      readme_total: 0,
      readme_current: 0,
      readme_progress: 0,
      vector_status: 'pending',
      vector_progress: 0,
      vector_current: 0,
      vector_total: 0,
      username: '',
      synced_projects: 0,
      synced_readme: 0,
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
