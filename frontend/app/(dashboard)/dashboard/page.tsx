"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Sparkles, AlertCircle, TrendingUp, PackageSearch, AlertTriangle, Download } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@clerk/nextjs";
import { formatQuantity } from "@/lib/format-indian";
import Link from "next/link";

interface Movement {
  id: string;
  type: string;
  quantity_delta: string;
  product_id: string;
  occurred_at: string;
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

  // ── Guards & Skeletons ─────────────────────────────────────────────

  if (!isLoaded || isLoading) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 animate-pulse space-y-8">
        <div className="flex justify-between">
          <div className="h-16 w-1/3 rounded-lg bg-white/5" />
          <div className="h-10 w-32 rounded-lg bg-white/5" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-32 rounded-xl bg-white/5" />)}
        </div>
        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="h-64 rounded-xl bg-white/5" />
          <div className="h-64 rounded-xl bg-white/5" />
        </div>
      </main>
    );
  }

  if (!orgId) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 text-center flex items-center justify-center min-h-[60vh]">
        <div className="rounded-xl border border-white/5 bg-card p-12 max-w-md w-full shadow-lg">
          <AlertCircle className="mx-auto size-12 text-amber-400" />
          <h2 className="mt-4 text-xl font-semibold">No Organization Active</h2>
          <p className="mt-2 text-slate-400">Please select or create an organization to view your dashboard.</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 text-center flex items-center justify-center min-h-[60vh]">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-12 text-red-400 max-w-md w-full">
          <AlertCircle className="mx-auto size-12" />
          <h2 className="mt-4 text-xl font-semibold">Failed to load data</h2>
          <p className="mt-2 text-sm opacity-90">{error}</p>
        </div>
      </main>
    );
  }

  // ── Metrics Computed ───────────────────────────────────────────────

  // Prevent overlap: Only products that are low stock AND > 0 are considered "low stock".
  // Assuming the backend returns raw counts, we subtract out_of_stock if backend included them.
  // Actually, standard logic: low_stock_products is likely count of (0 < qty <= reorder). 
  // Let's trust backend data but show clear alerts.

  const isLowStockAlert = (data?.low_stock_products ?? 0) > 0;
  const isOutOfStockAlert = (data?.out_of_stock_products ?? 0) > 0;

  return (
    <main className="mx-auto max-w-7xl p-5 lg:p-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-emerald-400">Overview</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Your Business Pulse</h1>
          <p className="mt-2 text-sm text-muted-foreground">Here’s a calm start to your business day.</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-2.5 text-sm font-medium text-emerald-400 transition hover:bg-emerald-500/20">
          <Sparkles className="size-4" />Ask Copilot
        </button>
      </div>

      {/* Alerts Section */}
      {(isOutOfStockAlert || isLowStockAlert) && (
        <section className="mt-6 flex flex-col gap-2">
          {isOutOfStockAlert && (
            <div className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <AlertTriangle className="size-4 shrink-0" />
              <p><strong>{data?.out_of_stock_products}</strong> products are completely out of stock.</p>
              <Link href="/inventory" className="ml-auto underline font-medium hover:text-red-300">View</Link>
            </div>
          )}
          {isLowStockAlert && (
            <div className="flex items-center gap-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
              <PackageSearch className="size-4 shrink-0" />
              <p><strong>{data?.low_stock_products}</strong> products are running low (below reorder level).</p>
              <Link href="/inventory" className="ml-auto underline font-medium hover:text-amber-300">View</Link>
            </div>
          )}
        </section>
      )}

      {/* Metrics Grid */}
      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Total Products", data?.total_products?.toString() || "0", "Catalogue size", "bg-blue-500/10 text-blue-400"],
          ["Total Stock", formatQuantity(data?.total_stock_quantity || "0"), "Total items across godowns", "bg-emerald-500/10 text-emerald-400"],
          ["Low Stock", data?.low_stock_products?.toString() || "0", "Needs reordering", "bg-amber-500/10 text-amber-400"],
          ["Out of Stock", data?.out_of_stock_products?.toString() || "0", "Zero inventory", "bg-red-500/10 text-red-400"],
        ].map(([label, value, detail, colorClass]) => (
          <article key={label} className="rounded-xl border border-white/5 bg-card p-5 shadow-sm transition hover:border-white/10 flex flex-col justify-between">
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <div className="mt-3">
              <p className="text-3xl font-semibold tracking-tight">{value}</p>
              <p className={`mt-2 text-xs font-medium w-fit px-2 py-0.5 rounded-full ${colorClass}`}>{detail}</p>
            </div>
          </article>
        ))}
      </section>

      {/* Main Content Grid */}
      <section className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <article className="rounded-xl border border-white/5 bg-card p-6 flex flex-col">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-lg">Recent Activity</h2>
              <p className="mt-1 text-sm text-muted-foreground">Latest stock inward, adjustments and transfers.</p>
            </div>
            <Link href="/inventory?tab=movements" className="text-sm font-medium text-emerald-400 hover:text-emerald-300 transition">View ledger</Link>
          </div>
          <div className="mt-6 flex-1">
            <div className="flex flex-col gap-0 divide-y divide-white/5">
              {data?.recent_movements?.length ? data.recent_movements.slice(0, 5).map((m: Movement) => {
                const delta = parseFloat(m.quantity_delta);
                const isPositive = delta > 0;
                const typeLabel = m.type.replace('_', ' ');
                const isReceipt = m.type === "receipt";
                
                return (
                  <div key={m.id} className="flex justify-between items-center py-3 text-sm transition hover:bg-white/[.02] px-2 rounded-lg -mx-2">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-full border ${isReceipt ? "bg-emerald-400/10 border-emerald-400/20 text-emerald-400" : isPositive ? "bg-blue-400/10 border-blue-400/20 text-blue-400" : "bg-amber-400/10 border-amber-400/20 text-amber-400"}`}>
                        {isReceipt ? <Download className="size-4" /> : isPositive ? <TrendingUp className="size-4" /> : <TrendingUp className="size-4 rotate-180" />}
                      </div>
                      <div>
                        <p className="font-medium capitalize text-slate-200">{typeLabel}</p>
                        <p className="text-xs text-slate-500">{new Date(m.occurred_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</p>
                      </div>
                    </div>
                    <span className={`font-mono font-medium ${isPositive ? "text-emerald-400" : "text-amber-400"}`}>
                      {isPositive ? '+' : ''}{formatQuantity(m.quantity_delta)}
                    </span>
                  </div>
                );
              }) : (
                <div className="grid h-40 place-items-center rounded-lg border border-dashed border-white/10 bg-white/[.02] text-center mt-2">
                  <div>
                    <p className="font-medium text-slate-300">No activity yet</p>
                    <p className="mt-1 text-sm text-muted-foreground">Start receiving stock in your inventory.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </article>

        <article className="rounded-xl border border-emerald-400/15 bg-gradient-to-br from-emerald-500/10 to-transparent p-6 relative overflow-hidden">
          <div className="absolute -right-6 -top-6 rounded-full bg-emerald-500/10 p-8 blur-2xl"></div>
          <Sparkles className="size-6 text-emerald-400" />
          <h2 className="mt-5 text-xl font-semibold text-white">Your AI employee is getting ready</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-300">
            Soon you’ll be able to ask clear questions and act with confidence from one workspace. The AI Business Copilot will analyze your inventory trends and suggest reorders automatically.
          </p>
          <div className="mt-8 pt-6 border-t border-emerald-400/10">
            <button className="inline-flex items-center gap-2 text-sm font-medium text-emerald-400 hover:text-emerald-300 transition">
              Explore the roadmap <ArrowRight className="size-4" />
            </button>
          </div>
        </article>
      </section>
    </main>
  );
}
