import type { VectorStatus } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
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
  isLoading?: boolean;
}

const statusLabels: Record<VectorStatus, string> = {
  pending: '等待向量化',
  vectorizing: '向量化中',
  completed: '向量化完成',
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
  isLoading,
}: Props) {
  return (
    <Card>
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[13px] text-muted-foreground tracking-wide uppercase">向量索引</span>
          <Badge variant={isRunning ? 'secondary' : status === 'completed' ? 'default' : 'outline'} className={isRunning ? 'animate-pulse' : ''}>
            {statusLabels[status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-5 space-y-5">
        {status === 'vectorizing' && (
          <div className="space-y-2">
            {total === 0 ? (
              <p className="text-sm text-muted-foreground text-center">准备中...</p>
            ) : (
              <>
                <Progress
                  value={current}
                  max={total}
                  label={`向量化进度: ${current.toLocaleString()} / ${total.toLocaleString()}`}
                />
                <p className="text-[12px] text-muted-foreground text-center tabular-nums">
                  {current.toLocaleString()} / {total.toLocaleString()} 个项目 ({Math.round(progress)}%)
                </p>
              </>
            )}
          </div>
        )}

        {status === 'completed' && (
          <p className="text-[14px] text-muted-foreground leading-relaxed">
            向量化已完成，可以使用 MCP 搜索/问答功能。
          </p>
        )}

        {status === 'pending' && !isRunning && (
          <p className="text-[14px] text-muted-foreground leading-relaxed">
            点击「开始向量化」为项目建立向量索引。
          </p>
        )}

        {error && (
          <p role="alert" className="text-[14px] text-muted-foreground leading-relaxed">
            {error}
          </p>
        )}

        <div className="flex gap-2 pt-1">
          {canStart && !isRunning && (
            <Button onClick={onStart} className="flex-1" disabled={isLoading}>
              <Zap className="mr-2 w-4 h-4" />
              {isLoading ? '启动中...' : '开始向量化'}
            </Button>
          )}
          {isRunning && (
            <Button variant="outline" onClick={onCancel} className="flex-1">
              <X className="mr-2 w-4 h-4" />
              取消向量化
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
