import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="relative isolate flex min-h-screen items-center overflow-hidden px-6">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_75%_25%,rgba(16,185,129,.2),transparent_28rem)]" />
      <section className="mx-auto max-w-3xl text-center">
        <div className="mx-auto mb-6 flex w-fit items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-300"><Sparkles className="size-4" /> Bharat Business Copilot</div>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">Your business, <span className="text-emerald-400">in control.</span></h1>
        <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-muted-foreground">A single, intelligent workspace for the daily rhythm of Indian businesses.</p>
        <Link className="mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 font-medium text-primary-foreground transition hover:bg-emerald-500" href="/dashboard">Open dashboard <ArrowRight className="size-4" /></Link>
      </section>
    </main>
  );
}
