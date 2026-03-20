// API client for health endpoints

export type HealthIssue = 'stale_repo' | 'high_issue_count' | 'missing_readme' | 'archived' | 'no_topics' | 'low_stars';

export interface HealthReport {
  project_id: number;
  project_name: string;
  full_name: string;
  score: number;
  issues: HealthIssue[];
  recommendations: string[];
  details: Record<string, unknown>;
}

export interface HealthCheckResponse {
  reports: HealthReport[];
  total: number;
}

export async function checkHealth(): Promise<HealthCheckResponse> {
  const response = await fetch('/api/health/check', { method: 'POST' });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}
