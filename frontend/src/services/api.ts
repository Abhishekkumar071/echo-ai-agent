import { ConversationSummary, Message, SessionData, TimelineEntry, SourceCitation, MemoryReference } from '../types';

const API_BASE = '/api/v1';

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('echo_session_token');
  }

  public async ensureSession(): Promise<string> {
    if (this.token) {
      return this.token;
    }
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      throw new Error(`Failed to create session: ${res.statusText}`);
    }
    const data: SessionData = await res.json();
    this.token = data.session_token;
    localStorage.setItem('echo_session_token', data.session_token);
    return this.token;
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const token = await this.ensureSession();
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  }

  public async listConversations(): Promise<ConversationSummary[]> {
    const headers = await this.getAuthHeaders();
    const res = await fetch(`${API_BASE}/conversations`, { headers });
    if (!res.ok) {
      if (res.status === 401) {
        localStorage.removeItem('echo_session_token');
        this.token = null;
        await this.ensureSession();
        return this.listConversations();
      }
      throw new Error('Failed to load conversations');
    }
    const data = await res.json();
    return data.conversations || [];
  }

  public async getConversation(id: string): Promise<{ id: string; title: string; messages: Message[] }> {
    const headers = await this.getAuthHeaders();
    const res = await fetch(`${API_BASE}/conversations/${id}`, { headers });
    if (!res.ok) {
      throw new Error('Failed to load conversation details');
    }
    const data = await res.json();
    const mappedMessages: Message[] = (data.messages || []).map((m: any) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      created_at: m.created_at,
      search_used: m.metadata?.search_used,
      memory_used: m.metadata?.memory_used,
      is_then_vs_now: m.metadata?.is_then_vs_now,
      sources: m.metadata?.sources,
      latency_ms: m.metadata?.latency_ms,
    }));
    return {
      id: data.id,
      title: data.title,
      messages: mappedMessages,
    };
  }

  public async getTimeline(fromDate?: string, toDate?: string): Promise<TimelineEntry[]> {
    const headers = await this.getAuthHeaders();
    const params = new URLSearchParams();
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    const res = await fetch(`${API_BASE}/memory/timeline?${params.toString()}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch timeline');
    const data = await res.json();
    return data.entries || [];
  }

  public async searchMemory(query: string): Promise<any[]> {
    const headers = await this.getAuthHeaders();
    const res = await fetch(`${API_BASE}/memory/search?q=${encodeURIComponent(query)}`, { headers });
    if (!res.ok) throw new Error('Failed to search memory');
    const data = await res.json();
    return data.results || [];
  }

  public async streamChat(
    message: string,
    conversationId: string | null,
    onMetadata: (data: { conversation_id: string; sources: SourceCitation[]; memory_references: MemoryReference[]; search_used: boolean; is_then_vs_now: boolean }) => void,
    onChunk: (chunk: string) => void,
    onDone: (data: { message_id: string; conversation_id: string; latency_ms: number }) => void,
    onError: (err: { code: string; message: string }) => void
  ): Promise<void> {
    const token = await this.ensureSession();
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat error: HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No readable stream available');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/^event:\s*(\w+)/m);
        const dataMatch = block.match(/^data:\s*(.+)$/m);

        if (!eventMatch || !dataMatch) continue;
        const event = eventMatch[1];
        let payload: any;
        try {
          payload = JSON.parse(dataMatch[1]);
        } catch {
          payload = dataMatch[1];
        }

        if (event === 'metadata') {
          onMetadata(payload);
        } else if (event === 'chunk') {
          onChunk(payload.text || '');
        } else if (event === 'done') {
          onDone(payload);
        } else if (event === 'error') {
          onError(payload);
        }
      }
    }
  }
}

export const api = new ApiService();
