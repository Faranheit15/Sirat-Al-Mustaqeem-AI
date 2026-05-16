import type { ReactNode } from "react";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b px-6 py-4">
        <p className="text-sm font-medium">Admin</p>
      </header>
      {children}
    </div>
  );
}
