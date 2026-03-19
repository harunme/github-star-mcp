interface Props {
  requireSync: boolean;
  syncCompleted: boolean;
}

export function MCPInfo({ requireSync, syncCompleted }: Props) {
  const isLocked = requireSync && !syncCompleted;

  return (
    <div className="mcp-info">
      <h3>MCP 端点</h3>
      <div className={`mcp-url ${isLocked ? 'mcp-locked' : ''}`}>
        {isLocked ? (
          '🔒 MCP 服务将在同步完成后可用'
        ) : (
          'MCP 端点已就绪'
        )}
      </div>
    </div>
  );
}
