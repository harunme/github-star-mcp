import { useState, useCallback } from 'react';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { sendChat, ChatMessage } from '@/api/chat';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = useCallback(async (message: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChat(message);

      // Add assistant message
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '发送失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleClear = useCallback(async () => {
    if (messages.length === 0) return;
    if (!confirm('确定要清除聊天历史吗？')) return;

    try {
      await fetch('/api/chat/clear', { method: 'POST' });
      setMessages([]);
    } catch {
      // Ignore errors
    }
  }, [messages.length]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-semibold">对话</h1>
        <p className="text-sm text-muted-foreground">
          与你的 GitHub Stars 智能助理交流
        </p>
      </div>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border">
        <ChatInput
          onSend={handleSend}
          onClear={handleClear}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}
