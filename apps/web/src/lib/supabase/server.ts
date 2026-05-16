import { createServerClient } from "@supabase/ssr";
import type { CookieMethodsServer } from "@supabase/ssr";
import { cookies } from "next/headers";

import { getPublicEnv } from "@/lib/env";

export async function createClient() {
  const cookieStore = await cookies();
  const env = getPublicEnv();

  const cookieMethods: CookieMethodsServer = {
    getAll() {
      return cookieStore.getAll();
    },
    setAll(cookiesToSet) {
      try {
        cookiesToSet.forEach(({ name, value, options }) => {
          cookieStore.set({ name, value, ...options });
        });
      } catch {
        // Server Components cannot set cookies; middleware refreshes sessions.
      }
    }
  };

  // The installed @supabase/ssr type overload marks the legacy overload deprecated even
  // when getAll/setAll are provided through a typed CookieMethodsServer object.
  // eslint-disable-next-line @typescript-eslint/no-deprecated
  return createServerClient(env.supabaseUrl, env.supabaseAnonKey, {
    cookies: cookieMethods
  });
}
