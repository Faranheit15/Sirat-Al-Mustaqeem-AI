"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import type { SupabaseClient } from "@supabase/supabase-js";

import { createClient } from "@/lib/supabase/client";

const SupabaseContext = createContext<SupabaseClient | null>(null);

export function useSupabase() {
  const client = useContext(SupabaseContext);
  if (client === null) {
    throw new Error("useSupabase must be used within AppProviders.");
  }
  return client;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const supabase = useMemo(() => createClient(), []);

  return (
    <SupabaseContext.Provider value={supabase}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
        {children}
        <Toaster richColors closeButton position="top-right" />
      </ThemeProvider>
    </SupabaseContext.Provider>
  );
}
