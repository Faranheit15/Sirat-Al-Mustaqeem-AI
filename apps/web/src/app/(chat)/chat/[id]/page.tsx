import { ChatShell } from "@/components/chat/chat-shell";

export default async function ConversationPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ChatShell conversationId={id} />;
}
