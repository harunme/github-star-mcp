import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Github, MessageSquare, Star, Settings } from 'lucide-react';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { sendChat, ChatMessage } from '@/api/chat';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = useCallback(async (message: string) => {
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
      // Ignore
    }
  }, [messages.length]);

  useEffect(() => {
    // Scroll to bottom when messages change
  }, [messages]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top Navigation */}
      <header className="shrink-0 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex items-center gap-6 px-4 h-14">
          <div className="flex items-center gap-2">
            <Github className="w-5 h-5" />
            <span className="font-semibold">GitHub Stars</span>
          </div>
          <nav className="flex items-center gap-1">
            <Link to="/" className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <Star className="w-4 h-4" />
              收藏
            </Link>
            <Link to="/chat" className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-primary/10 text-primary">
              <MessageSquare className="w-4 h-4" />
              对话
            </Link>
            <Link to="/settings" className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <Settings className="w-4 h-4" />
              设置
            </Link>
          </nav>
        </div>
      </header>

      {/* Chat area */}
      <MessageList messages={messages} />
      {error && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}
      <div className="p-4 border-t border-border">
        <ChatInput onSend={handleSend} onClear={handleClear} disabled={isLoading} />
      </div>
    </div>
  );
}
