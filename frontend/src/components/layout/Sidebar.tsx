import { NavLink } from 'react-router-dom';
import { MessageSquare, Settings, FolderOpen, Github, RefreshCw } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { useEffect, useState } from 'react';

interface SidebarProps {
  children: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
  const [syncStatus, setSyncStatus] = useState<{ status: string; synced_projects: number } | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/sync/status');
      if (res.ok) {
        setSyncStatus(await res.json());
      }
    } catch {
      // Ignore errors
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  usePolling(fetchStatus, 5000, true);

  const navItems = [
    { to: '/', icon: MessageSquare, label: '对话' },
    { to: '/groups', icon: FolderOpen, label: '分组' },
    { to: '/settings', icon: Settings, label: '设置' },
  ];

  const isCompleted = syncStatus?.status === 'completed';
  const syncedCount = syncStatus?.synced_projects || 0;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Github className="w-5 h-5" />
            <span className="font-semibold">GitHub Stars</span>
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <RefreshCw className={`w-3 h-3 ${isCompleted ? 'text-green-500' : 'text-yellow-500 animate-spin'}`} />
            <span>
              {isCompleted ? '已同步' : '同步中'} {syncedCount} 个项目
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <p className="text-xs text-muted-foreground">Powered by MCP</p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 bg-background">
        {children}
      </main>
    </div>
  );
}
