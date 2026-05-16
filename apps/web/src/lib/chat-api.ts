"use client";

import {
  chatStream,
  createApiClient,
  createConversation,
  deleteConversation,
  getConversationMessages,
  getConversations,
  setApiClientAccessTokenProvider
} from "@sirat/api-client";
import type { Message } from "@sirat/shared-types";

import { createClient } from "@/lib/supabase/client";

async function getAccessToken() {
  const supabase = createClient();
  const {
    data: { session }
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

setApiClientAccessTokenProvider(getAccessToken);

export const apiClient = createApiClient({ getAccessToken });

export async function fetchConversations() {
  return getConversations();
}

export async function fetchConversationMessages(id: string) {
  return getConversationMessages(id);
}

export async function createNewConversation(title: string) {
  return createConversation(title);
}

export async function removeConversation(id: string) {
  return deleteConversation(id);
}

export async function streamChatCompletion({
  conversationId,
  messages,
  onDelta,
  onDone
}: {
  conversationId: string | null;
  messages: Message[];
  onDelta: (delta: string) => void;
  onDone: (conversationId: string | null) => void;
}) {
  for await (const chunk of chatStream(messages, conversationId)) {
    if (chunk.startsWith("[DONE:") && chunk.endsWith("]")) {
      const resolvedConversationId = chunk.slice("[DONE:".length, -1);
      onDone(resolvedConversationId || null);
      continue;
    }

    onDelta(chunk);
  }
}
