import { Lock, CheckCircle2 } from 'lucide-react';

interface Props {
  requireSync: boolean;
  syncCompleted: boolean;
}

export function MCPInfo({ requireSync, syncCompleted }: Props) {
  const isLocked = requireSync && !syncCompleted;

  return (
    <div className="pt-4 border-t border-border">
      <div className="flex items-center gap-3 p-3 rounded-lg bg-muted">
        {isLocked ? (
          <>
            <Lock className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="text-sm text-amber-400">🔒 MCP 服务将在同步完成后可用</span>
          </>
        ) : (
          <>
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-sm text-emerald-400">✓ MCP 端点已就绪</span>
          </>
        )}
      </div>
    </div>
  );
}
