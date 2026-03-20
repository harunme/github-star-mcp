// API client for groups endpoints

export interface Group {
  id: number;
  name: string;
  description?: string;
  color: string;
  icon?: string;
  is_auto: boolean;
  project_count: number;
  created_at?: string;
}

export interface Project {
  id: number;
  name: string;
  full_name: string;
  description?: string;
  language?: string;
  stargazers_count: number;
  html_url: string;
}

export async function getGroups(): Promise<Group[]> {
  const response = await fetch('/api/groups');
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  return data.groups || [];
}

export async function createGroup(group: Partial<Group>): Promise<Group> {
  const response = await fetch('/api/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(group),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function updateGroup(id: number, group: Partial<Group>): Promise<Group> {
  const response = await fetch(`/api/groups/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(group),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function deleteGroup(id: number): Promise<void> {
  const response = await fetch(`/api/groups/${id}`, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

export async function getGroupProjects(groupId: number, limit = 100, offset = 0): Promise<Project[]> {
  const response = await fetch(`/api/groups/${groupId}/projects?limit=${limit}&offset=${offset}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  return data.projects || [];
}

export async function addProjectsToGroup(groupId: number, projectIds: number[]): Promise<void> {
  const response = await fetch(`/api/groups/${groupId}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_ids: projectIds }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

export async function removeProjectFromGroup(groupId: number, projectId: number): Promise<void> {
  const response = await fetch(`/api/groups/${groupId}/projects/${projectId}`, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}
