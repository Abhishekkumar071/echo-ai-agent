export interface SourceCitation {
  index: number;
  title: string;
  url: string;
  snippet: string;
  score?: number;
  metadata?: {
    domain?: string;
    published_date?: string;
  };
}

export interface MemoryReference {
  id: string;
  content: string;
  original_query?: string;
  created_at: string;
  memory_type: string;
  similarity_score?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  search_used?: boolean;
  memory_used?: boolean;
  is_then_vs_now?: boolean;
  sources?: SourceCitation[];
  memory_references?: MemoryReference[];
  latency_ms?: number;
  isStreaming?: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionData {
  session_token: string;
  user_id: string;
  expires_at: string;
}

export interface TimelineEntry {
  id: string;
  original_query: string | null;
  content: string;
  summary: string | null;
  created_at: string;
  topic_tags?: string[];
  conversation_id?: string;
}
