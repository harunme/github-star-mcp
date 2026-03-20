import type { SyncStatus } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

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
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[13px] text-muted-foreground tracking-wide uppercase">同步状态</span>
          <Badge variant={isLoading ? 'secondary' : status === 'completed' ? 'default' : 'outline'} className={isLoading ? 'animate-pulse' : ''}>
            {statusLabels[status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between gap-4">
          <Stat value={syncedProjects} label="已入库" />
          <Divider />
          <Stat value={syncedReadme} label="已同步 README" />
          <Divider />
          <Stat value={vectorizedProjects} label="已向量化" />
        </div>
        {status === 'loading_readme' && (
          <div className="mt-6 space-y-2">
            <Progress
              value={readmeCurrent}
              max={readmeTotal}
              label={`README 加载进度: ${readmeCurrent.toLocaleString()} / ${readmeTotal.toLocaleString()}`}
            />
            <p className="text-[12px] text-muted-foreground text-center tabular-nums">
              {readmeCurrent.toLocaleString()} / {readmeTotal.toLocaleString()} ({progress}%)
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex-1 text-center">
      <div className="text-[28px] font-semibold tracking-tight text-foreground tabular-nums leading-none">
        {value.toLocaleString()}
      </div>
      <div className="text-[12px] text-muted-foreground mt-1.5 tracking-wide">{label}</div>
    </div>
  );
}

function Divider() {
  return <div className="w-px h-10 bg-border/50 shrink-0" />;
}
