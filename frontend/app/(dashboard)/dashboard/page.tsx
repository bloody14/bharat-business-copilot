"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Sparkles, Loader2, AlertCircle } from "lucide-react";
import { MetricCard } from "@/components/dashboard/metric-card";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@clerk/nextjs";

interface Movement {
  id: string;
  type: string;
  quantity_delta: string;
}

interface DashboardData {
  total_products: number;
  total_stock_quantity: string;
  low_stock_products: number;
  out_of_stock_products: number;
  recent_movements: Movement[];
}

export default function DashboardPage() {
  const { request } = useApi();
  const { orgId, isLoaded } = useAuth();
  
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    if (!orgId) {
      setIsLoading(false);
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    request("/api/v1/inventory/dashboard")
      .then((res) => {
        if (isMounted) {
          setData(res);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error(err);
          setError(err.message || "Failed to load dashboard metrics");
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [request, orgId, isLoaded]);

  if (!isLoaded || isLoading) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="size-8 animate-spin text-emerald-400" />
        </div>
      </main>
    );
  }

  if (!orgId) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 text-center">
        <div className="rounded-xl border border-white/5 bg-card p-12">
          <AlertCircle className="mx-auto size-12 text-amber-400" />
          <h2 className="mt-4 text-xl font-semibold">No Organization Active</h2>
          <p className="mt-2 text-slate-400">Please select or create an organization to view your dashboard.</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 text-center">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-12 text-red-400">
          <AlertCircle className="mx-auto size-12" />
          <h2 className="mt-4 text-xl font-semibold">Failed to load data</h2>
          <p className="mt-2">{error}</p>
        </div>
      </main>
    );
  }

  const metrics = [
    ["Total products", data?.total_products?.toString() || "0", "Catalogue size"],
    ["Stock quantity", data?.total_stock_quantity || "0", "Total items in stock"],
    ["Low stock", data?.low_stock_products?.toString() || "0", "Needs reordering"],
    ["Out of stock", data?.out_of_stock_products?.toString() || "0", "Zero inventory"],
  ];

  return <main className="mx-auto max-w-7xl p-5 lg:p-8"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-medium text-emerald-400">Overview</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Your Business Pulse</h1><p className="mt-2 text-sm text-muted-foreground">Here’s a calm start to your business day.</p></div><button className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground"><Sparkles className="size-4" />Ask Copilot</button></div><section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, detail]) => <MetricCard key={label} label={label} value={value} detail={detail} />)}</section><section className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]"><article className="rounded-xl border border-white/5 bg-card p-6"><div className="flex items-center justify-between"><div><h2 className="font-semibold">Recent Movements</h2><p className="mt-1 text-sm text-muted-foreground">Your latest inventory activity.</p></div><button className="text-sm text-emerald-400">View ledger</button></div><div className="mt-6"><div className="flex flex-col gap-3">
    {data?.recent_movements?.length ? data.recent_movements.map((m: Movement) => (
      <div key={m.id} className="flex justify-between items-center text-sm border-b border-white/5 pb-2">
        <span className="text-slate-300 capitalize">{m.type.replace('_', ' ')}</span>
        <span className={Number(m.quantity_delta) > 0 ? "text-emerald-400" : "text-amber-400"}>{Number(m.quantity_delta) > 0 ? '+' : ''}{m.quantity_delta}</span>
      </div>
    )) : (
      <div className="mt-10 grid h-40 place-items-center rounded-lg border border-dashed border-white/10 bg-white/[.02] text-center"><div><p className="font-medium text-slate-300">No activity yet</p><p className="mt-1 text-sm text-muted-foreground">Connect your business workflows in the next sprint.</p></div></div>
    )}
  </div></div></article><article className="rounded-xl border border-emerald-400/15 bg-gradient-to-br from-emerald-500/15 to-transparent p-6"><Sparkles className="size-5 text-emerald-300" /><h2 className="mt-5 text-lg font-semibold">Your AI employee is getting ready</h2><p className="mt-2 text-sm leading-6 text-slate-300">Soon you’ll be able to ask clear questions and act with confidence from one workspace.</p><button className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-emerald-300">Explore the roadmap <ArrowRight className="size-4" /></button></article></section></main>;
}
