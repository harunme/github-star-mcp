import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, RefreshCw, AlertTriangle, Plus, Edit2, Trash2, Star, ExternalLink, FolderOpen, Github, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { usePolling } from '@/hooks/usePolling';
import { fetchStatus, startVectorize, cancelVectorize } from '@/api/sync';
import { getConfig } from '@/api/config';
import { checkHealth, HealthReport } from '@/api/health';
import { getGroups, createGroup, updateGroup, deleteGroup, Group, getGroupProjects, Project, getAllProjects } from '@/api/groups';
import type { SyncState } from '@/types';

const COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
  '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#06b6d4', '#3b82f6', '#6b7280', '#1f2937',
];

export function GroupsPage() {
  const [syncState, setSyncState] = useState<SyncState | null>(null);
  const [githubConfigured, setGithubConfigured] = useState<boolean | null>(null);

  const [groups, setGroups] = useState<Group[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [showAllProjects, setShowAllProjects] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [totalProjects, setTotalProjects] = useState(0);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '', color: COLORS[0] });
  const [saving, setSaving] = useState(false);

  const [healthReports, setHealthReports] = useState<HealthReport[]>([]);
  const [healthLoading, setHealthLoading] = useState(false);
  const [showHealth, setShowHealth] = useState(false);

  // Sync state
  const fetchSyncState = useCallback(async () => {
    try {
      const state = await fetchStatus();
      setSyncState(state);
    } catch {
      // Ignore
    }
  }, []);

  const checkGithubConfig = useCallback(async () => {
    try {
      const cfg = await getConfig();
      setGithubConfigured(!!cfg.github_token && !!cfg.github_username);
    } catch {
      setGithubConfigured(false);
    }
  }, []);

  // Groups
  const loadGroups = useCallback(async () => {
    try {
      const data = await getGroups();
      setGroups(data);
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  const loadProjects = useCallback(async (group: Group) => {
    try {
      const data = await getGroupProjects(group.id);
      setProjects(data);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setProjects([]);
    }
  }, []);

  const loadAllProjects = useCallback(async () => {
    try {
      const data = await getAllProjects();
      setProjects(data);
      setTotalProjects(data.length);
    } catch (err) {
      console.error('Failed to load all projects:', err);
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    fetchSyncState();
    checkGithubConfig();
    loadGroups();
  }, [fetchSyncState, checkGithubConfig, loadGroups]);

  const isActive =
    syncState?.status === 'syncing' ||
    syncState?.status === 'loading_readme' ||
    syncState?.vector_status?.status === 'vectorizing';
  const pollingInterval = isActive ? 3000 : 10000;
  usePolling(fetchSyncState, pollingInterval, !!syncState);

  useEffect(() => {
    if (showAllProjects) {
      setSelectedGroup(null);
      loadAllProjects();
    } else if (selectedGroup) {
      loadProjects(selectedGroup);
    } else {
      setProjects([]);
    }
  }, [selectedGroup, showAllProjects, loadProjects, loadAllProjects]);

  const handleStartVectorize = async () => {
    try {
      await startVectorize();
      await fetchSyncState();
    } catch (err) {
      console.error('启动向量化失败:', err);
    }
  };

  const handleCancelVectorize = async () => {
    try {
      await cancelVectorize();
      await fetchSyncState();
    } catch (err) {
      console.error('取消向量化失败:', err);
    }
  };

  // Group CRUD
  const handleCreate = async () => {
    if (!formData.name.trim()) return;
    setSaving(true);
    try {
      await createGroup(formData);
      setFormData({ name: '', description: '', color: COLORS[0] });
      setShowCreateForm(false);
      loadGroups();
    } catch (err) {
      console.error('Failed to create group:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingGroup || !formData.name.trim()) return;
    setSaving(true);
    try {
      await updateGroup(editingGroup.id, formData);
      setEditingGroup(null);
      setFormData({ name: '', description: '', color: COLORS[0] });
      loadGroups();
    } catch (err) {
      console.error('Failed to update group:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (group: Group) => {
    if (!confirm(`确定要删除分组 "${group.name}" 吗？`)) return;
    try {
      await deleteGroup(group.id);
      if (selectedGroup?.id === group.id) {
        setSelectedGroup(null);
      }
      loadGroups();
    } catch (err) {
      console.error('Failed to delete group:', err);
    }
  };

  // Health check
  const handleHealthCheck = useCallback(async () => {
    setHealthLoading(true);
    try {
      const result = await checkHealth();
      setHealthReports(result.reports);
    } catch (err) {
      console.error('Health check failed:', err);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  const { status, vector_status } = syncState || {};
  const syncedCount = syncState?.synced_projects || 0;
  const readmeCount = syncState?.synced_readme || 0;
  const vectorizedCount = syncState?.vectorized_projects || 0;
  const isVectorizing = vector_status?.status === 'vectorizing';
  const isCompleted = status === 'completed';

  const isLoading_ = githubConfigured === null || groupsLoading;

  if (isLoading_) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex items-center gap-6 px-4 h-14">
          <div className="flex items-center gap-2">
            <Github className="w-5 h-5" />
            <span className="font-semibold">GitHub Stars</span>
          </div>
          <nav className="flex items-center gap-1">
            <Link
              to="/"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-primary/10 text-primary"
            >
              <Star className="w-4 h-4" />
              收藏
            </Link>
            <Link
              to="/chat"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              对话
            </Link>
            <Link
              to="/settings"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <Settings className="w-4 h-4" />
              设置
            </Link>
          </nav>
          <div className="ml-auto text-xs text-muted-foreground flex items-center gap-1.5">
            <RefreshCw className={`w-3 h-3 ${isCompleted ? 'text-green-500' : 'text-yellow-500 animate-spin'}`} />
            <span>{isCompleted ? '已同步' : '同步中'} {syncedCount} 个项目</span>
          </div>
        </div>
      </header>

      {/* Page Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-semibold">收藏</h1>
        <p className="text-sm text-muted-foreground">AI 语义搜索 · 分组管理 · 健康检测</p>
      </div>

      {/* Scrollable Content */}
      <div className="overflow-y-auto pb-8">
        <div className="p-4 space-y-6 max-w-4xl mx-auto">

          {/* AI Search */}
          {githubConfigured ? (
            <>
              {/* Sync Stats */}
              <div className="flex gap-4 text-sm text-muted-foreground mb-2">
                <span>已入库: <Badge variant="secondary">{syncedCount}</Badge></span>
                <span>README: <Badge variant="secondary">{readmeCount}</Badge></span>
                <span>向量化: <Badge variant="secondary">{vectorizedCount}</Badge></span>
                {isCompleted && vector_status?.status === 'completed' && (
                  <span className="text-green-600 dark:text-green-400">✓ 向量库已就绪</span>
                )}
              </div>
              {isCompleted && vector_status?.status === 'pending' && (
                <Button size="sm" variant="outline" onClick={handleStartVectorize} className="mb-2">
                  开始向量化
                </Button>
              )}
              {isVectorizing && (
                <Button size="sm" variant="outline" onClick={handleCancelVectorize} className="mb-2">
                  取消向量化
                </Button>
              )}
            </>
          ) : (
            <div className="bg-primary/10 border border-primary/20 rounded-xl p-4 text-center">
              <p className="text-sm text-muted-foreground mb-2">请先在设置中配置 GitHub Token 和用户名</p>
              <Button size="sm" onClick={() => window.location.href = '/settings'}>
                前往设置
              </Button>
            </div>
          )}

          {/* Groups Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">分组</h2>
              <Button size="sm" variant="ghost" onClick={() => { setShowCreateForm(true); setEditingGroup(null); setFormData({ name: '', description: '', color: COLORS[0] }); }}>
                <Plus className="w-4 h-4 mr-1" />
                新建
              </Button>
            </div>

            {/* Create/Edit Form */}
            {(showCreateForm || editingGroup) && (
              <div className="mb-3 p-3 bg-muted rounded-lg space-y-2">
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="分组名称"
                  className="w-full px-3 py-2 rounded border border-border bg-background text-sm"
                  autoFocus
                />
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="描述 (可选)"
                  className="w-full px-3 py-2 rounded border border-border bg-background text-sm"
                />
                <div className="flex flex-wrap gap-2">
                  {COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => setFormData({ ...formData, color })}
                      className={`w-6 h-6 rounded-full ${formData.color === color ? 'ring-2 ring-primary' : ''}`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={editingGroup ? handleUpdate : handleCreate} disabled={saving}>
                    {saving ? '保存中...' : '保存'}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { setShowCreateForm(false); setEditingGroup(null); }}>
                    取消
                  </Button>
                </div>
              </div>
            )}

            {/* Group Tabs */}
            <div className="flex gap-2 overflow-x-auto pb-2">
              <button
                onClick={() => setShowAllProjects(true)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors ${showAllProjects ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
              >
                <div className="w-2.5 h-2.5 rounded-full bg-gradient-to-br from-amber-400 to-orange-500" />
                全部
                <Badge variant="secondary" className="text-xs">{totalProjects}</Badge>
              </button>
              {groups.map((group) => (
                <button
                  key={group.id}
                  onClick={() => { setSelectedGroup(group); setShowAllProjects(false); }}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors ${selectedGroup?.id === group.id ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
                >
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: group.color }} />
                  {group.name}
                  <Badge variant="secondary" className="text-xs">{group.project_count}</Badge>
                </button>
              ))}
            </div>
          </div>

          {/* Projects Grid */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">
                {showAllProjects ? '全部项目' : selectedGroup ? selectedGroup.name : '项目'}
              </h2>
              {selectedGroup && (
                <div className="flex gap-1">
                  <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => {
                    setEditingGroup(selectedGroup);
                    setFormData({ name: selectedGroup.name, description: selectedGroup.description || '', color: selectedGroup.color });
                    setShowCreateForm(false);
                  }}>
                    <Edit2 className="w-3 h-3 mr-1" />
                    编辑
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive" onClick={() => handleDelete(selectedGroup)}>
                    <Trash2 className="w-3 h-3 mr-1" />
                    删除
                  </Button>
                </div>
              )}
            </div>

            {projects.length === 0 ? (
              <p className="text-center text-muted-foreground py-8 text-sm">
                {showAllProjects ? '还没有同步任何项目' : '该分组还没有项目'}
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {projects.map((project) => (
                  <Card key={project.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <FolderOpen className="w-4 h-4 text-muted-foreground shrink-0" />
                            <span className="font-medium truncate text-sm">{project.full_name}</span>
                          </div>
                          {project.description && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                              {project.description}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                            {project.language && <span>{project.language}</span>}
                            <span className="flex items-center gap-1">
                              <Star className="w-3 h-3" />
                              {project.stargazers_count}
                            </span>
                          </div>
                        </div>
                        <a
                          href={project.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted-foreground hover:text-foreground ml-2 shrink-0"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Health Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                不活跃项目检测
              </h2>
              <Button size="sm" variant="outline" onClick={() => { setShowHealth(!showHealth); if (!showHealth && healthReports.length === 0) handleHealthCheck(); }}>
                {showHealth ? '收起' : '展开'}
              </Button>
            </div>

            {showHealth && (
              <>
                <Button size="sm" variant="outline" onClick={handleHealthCheck} className="mb-3" disabled={healthLoading}>
                  <RefreshCw className={`w-4 h-4 mr-1 ${healthLoading ? 'animate-spin' : ''}`} />
                  {healthLoading ? '检测中...' : '重新检测'}
                </Button>

                {healthLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : healthReports.length === 0 ? (
                  <Card>
                    <CardContent className="py-8 text-center text-sm text-muted-foreground">
                      所有项目都很健康！
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {healthReports.map((report) => (
                      <Card key={report.project_id}>
                        <CardContent className="p-3">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-sm">{report.full_name}</span>
                                <Badge variant={report.score >= 50 ? 'secondary' : 'destructive'} className="text-xs">
                                  {report.score}分
                                </Badge>
                              </div>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {report.issues.map((issue) => (
                                  <Badge key={issue} variant="outline" className="text-xs">
                                    {issue.replace('_', ' ')}
                                  </Badge>
                                ))}
                              </div>
                              {report.recommendations.length > 0 && (
                                <ul className="mt-1 text-xs text-muted-foreground space-y-0.5">
                                  {report.recommendations.map((rec, i) => (
                                    <li key={i}>• {rec}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
