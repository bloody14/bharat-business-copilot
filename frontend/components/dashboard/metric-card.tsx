import { ArrowUpRight } from "lucide-react";

export function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="rounded-xl border border-white/5 bg-card p-5 shadow-sm"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p><p className="mt-3 flex items-center gap-1 text-xs text-emerald-400"><ArrowUpRight className="size-3" />{detail}</p></article>;
}
