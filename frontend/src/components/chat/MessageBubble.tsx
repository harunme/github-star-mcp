import { User, Bot, Wrench } from 'lucide-react';
import { ChatMessage } from '@/api/chat';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : isTool
            ? 'bg-orange-500/10 text-orange-500'
            : 'bg-muted'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : isTool ? (
          <Wrench className="w-4 h-4" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      {/* Content */}
      <div
        className={`flex-1 max-w-[80%] ${
          isUser ? 'text-right' : ''
        }`}
      >
        <div
          className={`inline-block px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-md'
              : isTool
              ? 'bg-orange-500/10 text-orange-500 rounded-tl-md border border-orange-500/20'
              : 'bg-muted rounded-tl-md'
          }`}
        >
          {message.content}
        </div>

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {message.tool_calls.map((tool, i) => (
              <span
                key={i}
                className="px-2 py-0.5 text-xs bg-muted rounded-full text-muted-foreground"
              >
                {tool}
              </span>
            ))}
          </div>
        )}

        {/* Time */}
        {message.created_at && (
          <p className="mt-1 text-xs text-muted-foreground">
            {new Date(message.created_at).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
