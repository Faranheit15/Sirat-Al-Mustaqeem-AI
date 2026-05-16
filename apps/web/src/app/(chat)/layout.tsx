import type { ReactNode } from "react";

import { ConversationSidebar } from "@/components/chat/conversation-sidebar";

export default function ChatGroupLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <ConversationSidebar className="hidden md:flex" />
      {children}
    </div>
  );
}
