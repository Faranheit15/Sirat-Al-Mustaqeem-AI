export type ChatRole = "system" | "user" | "assistant";

export type LLMProviderName = "groq" | "gemini" | "openrouter";

export interface User {
  id: string;
  email: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id?: string;
  user_id?: string;
  role: ChatRole;
  content: string;
  created_at?: string | null;
  citations?: ReferenceSource[];
}

export interface Conversation {
  id: string;
  user_id?: string;
  title: string;
  created_at?: string | null;
  updated_at: string;
}

export interface ChatRequest {
  conversation_id?: string | null;
  messages: Message[];
}

export interface ChatResponse {
  conversation_id: string | null;
  message: Message;
  references?: ReferenceSource[];
  provider?: LLMProviderName;
}

export interface ReferenceSource {
  title: string;
  sourceType: "quran" | "hadith" | "scholarly" | "internal";
  citation: string;
  url?: string;
}

export interface ConversationListResponse {
  conversations: Conversation[];
}

export interface ConversationMessagesResponse {
  messages: Message[];
}

export interface CreateConversationRequest {
  title: string;
}

export interface LLMRateLimitState {
  provider: LLMProviderName;
  remaining: string | null;
}

export interface LLMProviderStatus {
  provider: LLMProviderName;
  available: boolean;
  rateLimitRemaining?: string | null;
}

export interface HealthResponse {
  status: "ok";
  service: string;
}
