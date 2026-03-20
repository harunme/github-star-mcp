import { Lock, CheckCircle2 } from 'lucide-react';

interface Props {
  requireSync: boolean;
  syncCompleted: boolean;
}

export function MCPInfo({ requireSync, syncCompleted }: Props) {
  const isLocked = requireSync && !syncCompleted;

  return (
    <div className="pt-2">
      <div className="flex items-center gap-3 px-5 py-4 rounded-2xl border bg-secondary/30">
        {isLocked ? (
          <>
            <Lock className="w-4 h-4 text-muted-foreground shrink-0" aria-hidden="true" />
            <span className="text-[14px] text-muted-foreground leading-relaxed">同步完成后即可使用 MCP 服务</span>
          </>
        ) : (
          <>
            <CheckCircle2 className="w-4 h-4 text-primary shrink-0" aria-hidden="true" />
            <span className="text-[14px] text-foreground leading-relaxed">MCP 端点已就绪</span>
          </>
        )}
      </div>
    </div>
  );
}
