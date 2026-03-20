import type { SyncStatus } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ChevronRight } from 'lucide-react';

interface Props {
  status: SyncStatus;
  syncedProjects: number;
  syncedReadme: number;
  vectorizedProjects: number;
  readmeCurrent: number;
  readmeTotal: number;
}

const statusLabels: Record<SyncStatus, string> = {
  pending: '等待同步',
  syncing: '同步仓库中',
  loading_readme: '加载 README',
  completed: '同步完成',
};

const statusVariants: Record<SyncStatus, "default" | "secondary" | "outline"> = {
  pending: 'outline',
  syncing: 'secondary',
  loading_readme: 'secondary',
  completed: 'default',
};

export function SyncStatusCard({
  status,
  syncedProjects,
  syncedReadme,
  vectorizedProjects,
  readmeCurrent,
  readmeTotal,
}: Props) {
  const isLoading = status === 'syncing' || status === 'loading_readme';
  const progress = status === 'loading_readme' && readmeTotal > 0
    ? Math.round((readmeCurrent / readmeTotal) * 100)
    : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-normal text-muted-foreground">同步状态</CardTitle>
          <Badge variant={statusVariants[status]} className={isLoading ? 'animate-pulse' : ''}>
            {statusLabels[status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center gap-4 py-2">
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">{syncedProjects}</div>
            <div className="text-xs text-muted-foreground mt-1">已入库</div>
          </div>
          <ChevronRight className="text-primary/60 animate-pulse w-6 h-6" />
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">{syncedReadme}</div>
            <div className="text-xs text-muted-foreground mt-1">已同步 README</div>
          </div>
          <ChevronRight className="text-primary/60 animate-pulse w-6 h-6" />
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">{vectorizedProjects}</div>
            <div className="text-xs text-muted-foreground mt-1">已向量化</div>
          </div>
        </div>
        {status === 'loading_readme' && (
          <div className="mt-4 space-y-2">
            <Progress value={progress} max={100} />
            <p className="text-xs text-center text-muted-foreground">
              {readmeCurrent} / {readmeTotal} ({progress}%)
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
