import type { VectorStatus } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Zap, X } from 'lucide-react';

interface Props {
  status: VectorStatus;
  progress: number;
  current: number;
  total: number;
  error?: string;
  onStart?: () => void;
  onCancel?: () => void;
  canStart: boolean;
  isRunning: boolean;
}

const statusLabels: Record<VectorStatus, string> = {
  pending: '等待向量化',
  vectorizing: '向量化中',
  completed: '向量化完成',
};

const statusVariants: Record<VectorStatus, "default" | "secondary" | "outline"> = {
  pending: 'outline',
  vectorizing: 'secondary',
  completed: 'default',
};

export function VectorStatusCard({
  status,
  progress,
  current,
  total,
  error,
  onStart,
  onCancel,
  canStart,
  isRunning,
}: Props) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-normal text-muted-foreground">向量索引</CardTitle>
          <Badge variant={statusVariants[status]} className={isRunning ? 'animate-pulse' : ''}>
            {statusLabels[status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {(isRunning || status === 'completed') && (
          <div className="space-y-2">
            <Progress value={progress} max={100} />
            {total > 0 && (
              <p className="text-xs text-center text-muted-foreground">
                {current} / {total} 个项目 ({Math.round(progress)}%)
              </p>
            )}
          </div>
        )}

        {status === 'completed' && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-sm text-emerald-400">
            向量化已完成，可以使用 MCP 搜索/问答功能。
          </div>
        )}

        {error && (
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3 text-sm text-destructive">
            <strong>向量化失败:</strong> {error}
          </div>
        )}

        <div className="flex gap-2">
          {canStart && !isRunning && (
            <Button onClick={onStart} className="w-full">
              <Zap className="mr-2 w-4 h-4" />
              开始向量化
            </Button>
          )}
          {isRunning && (
            <Button variant="destructive" onClick={onCancel} className="w-full">
              <X className="mr-2 w-4 h-4" />
              取消向量化
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
