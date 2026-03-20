// API client for chat endpoints

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: string[];
  tool_results?: Array<{ tool: string; result: string }>;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface ChatResponse {
  message: string;
  history: ChatMessage[];
}

export interface ChatStreamChunk {
  type: 'content' | 'tool_call' | 'done' | 'error';
  data: unknown;
}

export async function sendChat(message: string): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function sendChatStream(
  message: string,
  onChunk: (chunk: ChatStreamChunk) => void,
  onDone: () => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim()) {
          try {
            const chunk = JSON.parse(line) as ChatStreamChunk;
            onChunk(chunk);
            if (chunk.type === 'done' || chunk.type === 'error') {
              onDone();
              return;
            }
          } catch {
            // Ignore parse errors
          }
        }
      }
    }

    onDone();
  } catch (error) {
    onError(error instanceof Error ? error : new Error(String(error)));
  }
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  const response = await fetch('/api/chat/history');
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  return data.history || [];
}

export async function clearChatHistory(): Promise<void> {
  const response = await fetch('/api/chat/clear', { method: 'POST' });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}
