import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/stores/chat-store";

function isRtlText(text: string) {
  return /[\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC]/.test(text);
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const rtl = isRtlText(message.content);

  return (
    <article
      className={cn(
        "flex animate-message-in gap-3 px-4 py-5",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar className="mt-1">
          <AvatarFallback>SA</AvatarFallback>
        </Avatar>
      )}
      <div
        className={cn(
          "max-w-[min(760px,85vw)] rounded-lg px-4 py-3 text-sm leading-7",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border bg-card text-card-foreground shadow-sm"
        )}
        dir={rtl ? "rtl" : "ltr"}
      >
        <ReactMarkdown
          rehypePlugins={[rehypeRaw]}
          components={{
            a: ({ className, ...props }) => (
              <a
                className={cn("underline underline-offset-4", className)}
                target="_blank"
                rel="noreferrer"
                {...props}
              />
            ),
            p: ({ className, ...props }) => <p className={cn("mb-3 last:mb-0", className)} {...props} />,
            ul: ({ className, ...props }) => <ul className={cn("mb-3 list-disc ps-5", className)} {...props} />,
            ol: ({ className, ...props }) => <ol className={cn("mb-3 list-decimal ps-5", className)} {...props} />
          }}
        >
          {message.content}
        </ReactMarkdown>
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 border-t pt-3 text-xs text-muted-foreground">
            {message.citations.map((citation) => (
              <a
                key={`${citation.title}-${citation.citation}`}
                className="mr-3 underline underline-offset-4"
                href={citation.url}
                target="_blank"
                rel="noreferrer"
              >
                {citation.title}: {citation.citation}
              </a>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}
