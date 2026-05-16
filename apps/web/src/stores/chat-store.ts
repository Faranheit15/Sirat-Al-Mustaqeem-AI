"use client";

import { create } from "zustand";
import type { Conversation, Message, ReferenceSource } from "@sirat/shared-types";

export type ChatRole = Message["role"];

export type Citation = ReferenceSource;

export type ChatMessage = Message;

export type ConversationSummary = Conversation;

interface ChatState {
  activeConversationId: string | null;
  conversations: ConversationSummary[];
  messages: ChatMessage[];
  isStreaming: boolean;
  setActiveConversationId: (conversationId: string | null) => void;
  setConversations: (conversations: ConversationSummary[]) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  appendToLastAssistantMessage: (delta: string) => void;
  setStreaming: (isStreaming: boolean) => void;
}

function isWordLike(character: string) {
  return /[\p{L}\p{N}]/u.test(character);
}

function shouldInsertSpace(previous: string, next: string) {
  if (!previous || !next || /\s$/.test(previous) || /^\s/.test(next)) {
    return false;
  }

  const previousCharacter = previous.at(-1) ?? "";
  const nextCharacter = next.at(0) ?? "";

  if (/[,.;:!?%)]/.test(nextCharacter) || nextCharacter === "'") {
    return false;
  }

  if (/[(\[{/$-]/.test(previousCharacter)) {
    return false;
  }

  if (isWordLike(previousCharacter) && isWordLike(nextCharacter)) {
    return true;
  }

  return /[.!?:;]$/.test(previousCharacter) && isWordLike(nextCharacter);
}

function appendAssistantDelta(previous: string, delta: string) {
  return `${previous}${shouldInsertSpace(previous, delta) ? " " : ""}${delta}`;
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  conversations: [],
  messages: [],
  isStreaming: false,
  setActiveConversationId: (conversationId) => {
    set({ activeConversationId: conversationId });
  },
  setConversations: (conversations) => {
    set({ conversations });
  },
  setMessages: (messages) => {
    set({ messages });
  },
  addMessage: (message) => {
    set((state) => ({ messages: [...state.messages, message] }));
  },
  appendToLastAssistantMessage: (delta) => {
    set((state) => {
      const messages = [...state.messages];
      const last = messages.at(-1);

      if (last?.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          content: appendAssistantDelta(last.content, delta)
        };
        return { messages };
      }

      return {
        messages: [
          ...messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: delta
          }
        ]
      };
    });
  },
  setStreaming: (isStreaming) => {
    set({ isStreaming });
  }
}));
