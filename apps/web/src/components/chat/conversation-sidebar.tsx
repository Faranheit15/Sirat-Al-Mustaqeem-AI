"use client";

import { useEffect } from "react";
import Link from "next/link";
import { MessageSquarePlus, PanelLeftClose } from "lucide-react";
import { toast } from "sonner";

import { fetchConversations } from "@/lib/chat-api";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chat-store";

export function ConversationSidebar({ className }: { className?: string }) {
  const conversations = useChatStore((state) => state.conversations);
  const activeConversationId = useChatStore((state) => state.activeConversationId);
  const setConversations = useChatStore((state) => state.setConversations);
  const setMessages = useChatStore((state) => state.setMessages);
  const setActiveConversationId = useChatStore((state) => state.setActiveConversationId);

  useEffect(() => {
    void fetchConversations()
      .then(setConversations)
      .catch((error: unknown) => {
        toast.error(error instanceof Error ? error.message : "Could not load conversations.");
      });
  }, [setConversations]);

  return (
    <aside className={cn("flex h-dvh w-72 shrink-0 flex-col border-r bg-card", className)}>
      <div className="flex h-14 items-center justify-between px-3">
        <Link href="/chat" className="font-semibold">
          Sirat AI
        </Link>
        <Button variant="ghost" size="icon" className="md:hidden">
          <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">Close sidebar</span>
        </Button>
      </div>
      <div className="px-3 pb-3">
        <Button
          asChild
          className="w-full justify-start"
          variant="secondary"
          onClick={() => {
            setActiveConversationId(null);
            setMessages([]);
          }}
        >
          <Link href="/chat">
            <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
            New chat
          </Link>
        </Button>
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        <nav className="space-y-1 p-3">
          {conversations.map((conversation) => (
            <Link
              key={conversation.id}
              href={`/chat/${conversation.id}`}
              className={cn(
                "block rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent",
                activeConversationId === conversation.id && "bg-accent text-accent-foreground"
              )}
            >
              <span className="line-clamp-1">{conversation.title}</span>
              <span className="mt-1 block text-xs text-muted-foreground">
                {conversation.updated_at || "Recent"}
              </span>
            </Link>
          ))}
          {conversations.length === 0 && (
            <p className="px-3 py-4 text-sm text-muted-foreground">No saved conversations yet.</p>
          )}
        </nav>
      </ScrollArea>
    </aside>
  );
}
