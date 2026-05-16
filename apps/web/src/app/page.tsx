import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center bg-background px-6 text-foreground">
      <section className="mx-auto w-full max-w-4xl py-16">
        <p className="font-mono text-sm uppercase tracking-[0.2em] text-muted-foreground">Sirat Al Mustaqeem AI</p>
        <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-tight md:text-6xl">
          Islamic AI guidance with sources, humility, and clear boundaries.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
          Ask careful questions, review citations, and keep conversations organized as the assistant grows.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button asChild>
            <Link href="/chat">Start chatting</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/login">Log in</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
