import { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { ChatMessage } from '@/api/chat';

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground text-lg mb-2">你好！</p>
          <p className="text-muted-foreground text-sm">
            我是你的 GitHub Stars 智能助理，可以帮你：
          </p>
          <ul className="mt-4 text-sm text-muted-foreground space-y-1">
            <li>• 语义搜索 Stars 项目</li>
            <li>• 组织和管理项目分组</li>
            <li>• 检测不活跃的仓库</li>
            <li>• 发现 GitHub Trending</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
