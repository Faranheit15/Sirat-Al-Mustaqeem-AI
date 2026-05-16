"use client";

import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { toast } from "sonner";

import { streamChatCompletion } from "@/lib/chat-api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChatStore, type ChatMessage } from "@/stores/chat-store";

export function ChatInput() {
  const [content, setContent] = useState("");
  const activeConversationId = useChatStore((state) => state.activeConversationId);
  const messages = useChatStore((state) => state.messages);
  const addMessage = useChatStore((state) => state.addMessage);
  const appendToLastAssistantMessage = useChatStore((state) => state.appendToLastAssistantMessage);
  const setStreaming = useChatStore((state) => state.setStreaming);
  const setActiveConversationId = useChatStore((state) => state.setActiveConversationId);
  const isStreaming = useChatStore((state) => state.isStreaming);

  async function sendMessage() {
    const trimmed = content.trim();
    if (!trimmed || isStreaming) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed
    };
    const nextMessages = [...messages, userMessage];
    addMessage(userMessage);
    setContent("");
    setStreaming(true);

    try {
      await streamChatCompletion({
        conversationId: activeConversationId,
        messages: nextMessages,
        onDelta: appendToLastAssistantMessage,
        onDone: setActiveConversationId
      });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Chat request failed.");
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="border-t bg-background/95 px-4 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-end gap-3">
        <Textarea
          value={content}
          onChange={(event) => {
            setContent(event.target.value);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void sendMessage();
            }
          }}
          placeholder="Ask with adab. Shift+Enter adds a new line."
          className="max-h-48 min-h-12 flex-1"
        />
        <Button
          size="icon"
          onClick={() => {
            void sendMessage();
          }}
          disabled={!content.trim() || isStreaming}
        >
          <SendHorizontal className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">Send</span>
        </Button>
      </div>
    </div>
  );
}
