"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useSupabase } from "@/components/providers/app-providers";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = useSupabase();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const next = searchParams.get("next") ?? "/chat";

  async function handleEmailLogin(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}${next}`
      }
    });
    setLoading(false);

    if (error) {
      toast.error(error.message);
      return;
    }

    toast.success("Check your email for the login link.");
  }

  async function handleGoogleLogin() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}${next}`
      }
    });

    if (error) {
      toast.error(error.message);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Log in</CardTitle>
        <CardDescription>Continue your conversations with Sirat Al Mustaqeem AI.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={handleEmailLogin}>
          <Input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
            required
          />
          <Button className="w-full" type="submit" disabled={loading}>
            {loading ? "Sending link..." : "Email magic link"}
          </Button>
        </form>
        <div className="flex items-center gap-3">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">or</span>
          <Separator className="flex-1" />
        </div>
        <Button className="w-full" variant="outline" onClick={handleGoogleLogin}>
          Continue with Google
        </Button>
        <Button
          className="w-full"
          variant="ghost"
          onClick={() => {
            router.push("/signup");
          }}
        >
          Create an account
        </Button>
      </CardContent>
    </Card>
  );
}
