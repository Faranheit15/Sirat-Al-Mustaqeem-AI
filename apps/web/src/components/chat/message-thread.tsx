"use client";

import { useEffect, useRef } from "react";

import { MessageBubble } from "@/components/chat/message-bubble";
import { StreamingIndicator } from "@/components/chat/streaming-indicator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/stores/chat-store";

export function MessageThread() {
  const messages = useChatStore((state) => state.messages);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isStreaming]);

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto flex min-h-full max-w-4xl flex-col py-6">
        {messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-6 text-center text-muted-foreground">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Start a new conversation</h1>
              <p className="mt-3 max-w-lg text-sm leading-6">
                Ask a question and the assistant will answer with care, context, and room for citations.
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
        {isStreaming && <StreamingIndicator className="px-6 py-3" />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
