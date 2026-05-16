import { cn } from "@/lib/utils";

export function StreamingIndicator({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-1 text-muted-foreground", className)} aria-label="Streaming">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:120ms]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:240ms]" />
    </div>
  );
}
