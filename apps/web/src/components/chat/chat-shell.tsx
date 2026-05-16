"use client";

import { useEffect } from "react";
import { toast } from "sonner";

import { ChatInput } from "@/components/chat/chat-input";
import { MessageThread } from "@/components/chat/message-thread";
import { fetchConversationMessages } from "@/lib/chat-api";
import { useChatStore } from "@/stores/chat-store";

export function ChatShell({ conversationId = null }: { conversationId?: string | null }) {
  const setActiveConversationId = useChatStore((state) => state.setActiveConversationId);
  const setMessages = useChatStore((state) => state.setMessages);

  useEffect(() => {
    let active = true;
    setActiveConversationId(conversationId);
    if (conversationId === null) {
      setMessages([]);
      return () => {
        active = false;
      };
    }

    void fetchConversationMessages(conversationId)
      .then((messages) => {
        if (active) {
          setMessages(messages);
        }
      })
      .catch((error: unknown) => {
        toast.error(error instanceof Error ? error.message : "Could not load conversation.");
        if (active) {
          setMessages([]);
        }
      });

    return () => {
      active = false;
    };
  }, [conversationId, setActiveConversationId, setMessages]);

  return (
    <section className="flex h-dvh min-w-0 flex-1 flex-col">
      <MessageThread />
      <ChatInput />
    </section>
  );
}
