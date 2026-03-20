import { useState, useEffect, useCallback } from 'react';
import { Plus, Edit2, Trash2, FolderOpen, Loader2, Star, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getGroups, createGroup, updateGroup, deleteGroup, Group, getGroupProjects, Project } from '@/api/groups';

const COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
  '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#06b6d4', '#3b82f6', '#6b7280', '#1f2937',
];

export function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '', color: COLORS[0] });
  const [saving, setSaving] = useState(false);

  const loadGroups = useCallback(async () => {
    try {
      const data = await getGroups();
      setGroups(data);
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setLoading(false);
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

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  useEffect(() => {
    if (selectedGroup) {
      loadProjects(selectedGroup);
    } else {
      setProjects([]);
    }
  }, [selectedGroup, loadProjects]);

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

  const startEdit = (group: Group) => {
    setEditingGroup(group);
    setFormData({
      name: group.name,
      description: group.description || '',
      color: group.color,
    });
    setShowCreateForm(false);
  };

  const startCreate = () => {
    setShowCreateForm(true);
    setEditingGroup(null);
    setFormData({ name: '', description: '', color: COLORS[0] });
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Groups List */}
      <div className="w-80 border-r border-border flex flex-col">
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">分组</h2>
            <Button size="sm" onClick={startCreate}>
              <Plus className="w-4 h-4 mr-1" />
              新建
            </Button>
          </div>

          {/* Create/Edit Form */}
          {(showCreateForm || editingGroup) && (
            <div className="mb-4 p-3 bg-muted rounded-lg space-y-3">
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
                    className={`w-6 h-6 rounded-full ${formData.color === color ? 'ring-2 ring-offset-2 ring-offset-muted ring-primary' : ''}`}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={editingGroup ? handleUpdate : handleCreate} disabled={saving}>
                  {saving ? '保存中...' : '保存'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setShowCreateForm(false);
                    setEditingGroup(null);
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          )}

          {/* Groups List */}
          <div className="space-y-1">
            {groups.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                还没有创建任何分组
              </p>
            ) : (
              groups.map((group) => (
                <button
                  key={group.id}
                  onClick={() => setSelectedGroup(group)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedGroup?.id === group.id
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted'
                  }`}
                >
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: group.color }}
                  />
                  <div className="flex-1 text-left truncate">{group.name}</div>
                  <Badge variant="secondary" className="text-xs">
                    {group.project_count}
                  </Badge>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="p-4 border-t border-border text-sm text-muted-foreground">
          <p>总分组: {groups.length}</p>
          <p>总项目数: {groups.reduce((acc, g) => acc + g.project_count, 0)}</p>
        </div>
      </div>

      {/* Projects */}
      <div className="flex-1 flex flex-col">
        {selectedGroup ? (
          <>
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h2 className="font-semibold flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: selectedGroup.color }}
                  />
                  {selectedGroup.name}
                </h2>
                {selectedGroup.description && (
                  <p className="text-sm text-muted-foreground">{selectedGroup.description}</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => startEdit(selectedGroup)}>
                  <Edit2 className="w-4 h-4" />
                </Button>
                <Button size="sm" variant="ghost" onClick={() => handleDelete(selectedGroup)}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {projects.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  该分组还没有项目
                </p>
              ) : (
                <div className="grid gap-3">
                  {projects.map((project) => (
                    <Card key={project.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <FolderOpen className="w-4 h-4 text-muted-foreground" />
                              <span className="font-medium">{project.full_name}</span>
                            </div>
                            {project.description && (
                              <p className="text-sm text-muted-foreground mt-1">
                                {project.description}
                              </p>
                            )}
                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                              {project.language && (
                                <span>{project.language}</span>
                              )}
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
                            className="text-muted-foreground hover:text-foreground"
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
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <FolderOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>选择一个分组查看项目</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
