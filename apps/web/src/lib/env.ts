export function getPublicEnv() {
  return {
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
    apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
  };
}
