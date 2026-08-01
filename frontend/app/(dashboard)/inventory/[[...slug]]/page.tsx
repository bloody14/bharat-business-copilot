"use client";

import { useEffect, useState, useCallback } from "react";
import { PackagePlus, Search, Loader2, AlertCircle, Download, ArrowRightLeft, Wrench, MapPin, ClipboardList } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@clerk/nextjs";
import { formatRupees } from "@/lib/format-indian";

import { AddProductDialog } from "@/components/inventory/add-product-dialog";
import { ReceiveStockDialog } from "@/components/inventory/receive-stock-dialog";
import { AdjustStockDialog } from "@/components/inventory/adjust-stock-dialog";
import { TransferStockDialog } from "@/components/inventory/transfer-stock-dialog";
import { AddLocationDialog } from "@/components/inventory/add-location-dialog";

// ── Types ──────────────────────────────────────────────────────────────

interface Product {
  id: string;
  name: string;
  sku: string;
  unit: string;
  cost_price: string;
  selling_price: string;
  gst_rate: string;
  available_quantity: string;
  reorder_level: string;
  is_active: boolean;
}

interface Movement {
  id: string;
  product_id: string;
  location_id: string;
  type: string;
  quantity_delta: string;
  reference_id: string | null;
  occurred_at: string;
}

// ── Tabs ───────────────────────────────────────────────────────────────

type Tab = "products" | "movements";

// ── Main Component ─────────────────────────────────────────────────────

export default function InventoryPage() {
  const { request } = useApi();
  const { orgId, isLoaded } = useAuth();

  const [products, setProducts] = useState<Product[]>([]);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("products");
  const [searchQuery, setSearchQuery] = useState("");

  // Dialog states
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [showReceiveStock, setShowReceiveStock] = useState(false);
  const [showAdjustStock, setShowAdjustStock] = useState(false);
  const [showTransferStock, setShowTransferStock] = useState(false);
  const [showAddLocation, setShowAddLocation] = useState(false);

  const fetchData = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [prods, movs] = await Promise.all([
        request("/api/v1/products"),
        request("/api/v1/inventory/movements"),
      ]);
      setProducts(prods);
      setMovements(movs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load inventory data");
    } finally {
      setIsLoading(false);
    }
  }, [request, orgId]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!orgId) {
      setIsLoading(false);
      setProducts([]);
      setMovements([]);
      setError(null);
      return;
    }
    fetchData();
  }, [isLoaded, orgId, fetchData]);

  const onMutationSuccess = () => fetchData();

  // ── Guards ─────────────────────────────────────────────────────────

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
          <p className="mt-2 text-slate-400">Please select or create an organization to view your inventory.</p>
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

  // ── Computed stats ─────────────────────────────────────────────────

  const totalProducts = products.length;
  const stockQuantity = products.reduce((acc, p) => acc + parseFloat(p.available_quantity || "0"), 0);
  const lowStock = products.filter(p => {
    const avail = parseFloat(p.available_quantity);
    const reorder = parseFloat(p.reorder_level);
    return avail > 0 && avail <= reorder;
  }).length;
  const outOfStock = products.filter(p => parseFloat(p.available_quantity) <= 0).length;

  const filteredProducts = searchQuery
    ? products.filter(p =>
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.sku.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : products;

  // ── Product name lookup for movements ──────────────────────────────
  const productMap = new Map(products.map(p => [p.id, p.name]));

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <>
      {/* Dialogs */}
      <AddProductDialog open={showAddProduct} onClose={() => setShowAddProduct(false)} onSuccess={onMutationSuccess} />
      <ReceiveStockDialog open={showReceiveStock} onClose={() => setShowReceiveStock(false)} onSuccess={onMutationSuccess} />
      <AdjustStockDialog open={showAdjustStock} onClose={() => setShowAdjustStock(false)} onSuccess={onMutationSuccess} />
      <TransferStockDialog open={showTransferStock} onClose={() => setShowTransferStock(false)} onSuccess={onMutationSuccess} />
      <AddLocationDialog open={showAddLocation} onClose={() => setShowAddLocation(false)} onSuccess={onMutationSuccess} />

      <main className="mx-auto max-w-7xl p-5 lg:p-8">
        {/* Header */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-sm font-medium text-emerald-400">Inventory</p>
            <h1 className="mt-1 text-3xl font-semibold">Keep every shelf in control.</h1>
            <p className="mt-2 text-sm text-muted-foreground">Catalogue, locations and stock movements in one ledger.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setShowAddLocation(true)} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:bg-white/5">
              <MapPin className="size-4" />Location
            </button>
            <button onClick={() => setShowAddProduct(true)} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600">
              <PackagePlus className="size-4" />Add Product
            </button>
          </div>
        </div>

        {/* Stats */}
        <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Total Products", totalProducts.toString(), "In catalogue"],
            ["Stock Quantity", stockQuantity.toString(), "Total items"],
            ["Low Stock", lowStock.toString(), "Needs reordering"],
            ["Out of Stock", outOfStock.toString(), "Zero inventory"],
          ].map(([a, b, c]) => (
            <article key={a} className="rounded-xl border border-white/5 bg-card p-5">
              <p className="text-sm text-muted-foreground">{a}</p>
              <p className="mt-3 text-2xl font-semibold">{b}</p>
              <p className="mt-3 text-xs text-emerald-400">{c}</p>
            </article>
          ))}
        </section>

        {/* Action Bar */}
        <section className="mt-6 flex flex-wrap gap-2">
          <button onClick={() => setShowReceiveStock(true)} className="inline-flex items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/5 px-4 py-2.5 text-sm font-medium text-emerald-300 transition hover:bg-emerald-400/10">
            <Download className="size-4" />Stock Inward
          </button>
          <button onClick={() => setShowAdjustStock(true)} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-white/5">
            <Wrench className="size-4" />Adjust Stock
          </button>
          <button onClick={() => setShowTransferStock(true)} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-white/5">
            <ArrowRightLeft className="size-4" />Transfer
          </button>
        </section>

        {/* Tab Selector */}
        <div className="mt-6 flex gap-1 rounded-lg border border-white/5 bg-white/[.02] p-1 w-fit">
          <button onClick={() => setTab("products")} className={`rounded-md px-4 py-2 text-sm font-medium transition ${tab === "products" ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"}`}>
            <PackagePlus className="mr-1.5 inline size-4" />Products
          </button>
          <button onClick={() => setTab("movements")} className={`rounded-md px-4 py-2 text-sm font-medium transition ${tab === "movements" ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"}`}>
            <ClipboardList className="mr-1.5 inline size-4" />Movement Ledger
          </button>
        </div>

        {/* Tab Content */}
        {tab === "products" ? (
          <section className="mt-4 rounded-xl border border-white/5 bg-card">
            <div className="flex flex-col gap-4 border-b border-white/5 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-semibold">Products</h2>
                <p className="mt-1 text-sm text-muted-foreground">Stock status across all locations.</p>
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-muted-foreground">
                <Search className="size-4" />
                <input className="w-40 bg-transparent outline-none placeholder:text-slate-500" placeholder="Search products…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
              </div>
            </div>
            <div className="overflow-x-auto">
              {filteredProducts.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  {products.length === 0
                    ? "No products in catalogue. Click \"Add Product\" to get started."
                    : "No products match your search."}
                </div>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-5 py-3">Product</th>
                      <th className="px-5 py-3">SKU</th>
                      <th className="px-5 py-3">Cost (₹)</th>
                      <th className="px-5 py-3">MRP (₹)</th>
                      <th className="px-5 py-3">GST</th>
                      <th className="px-5 py-3">Available</th>
                      <th className="px-5 py-3">Reorder</th>
                      <th className="px-5 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProducts.map((p) => {
                      const available = parseFloat(p.available_quantity);
                      const reorder = parseFloat(p.reorder_level);
                      const state = available <= 0 ? "Out of stock" : available <= reorder ? "Low stock" : "In stock";
                      const statusClass = state === "In stock"
                        ? "rounded-full bg-emerald-400/10 px-2.5 py-1 text-xs text-emerald-300"
                        : state === "Low stock"
                          ? "rounded-full bg-amber-400/10 px-2.5 py-1 text-xs text-amber-300"
                          : "rounded-full bg-red-400/10 px-2.5 py-1 text-xs text-red-300";

                      return (
                        <tr key={p.sku} className="border-t border-white/5 transition hover:bg-white/[.02]">
                          <td className="px-5 py-4 font-medium">{p.name}</td>
                          <td className="px-5 py-4 text-muted-foreground font-mono text-xs">{p.sku}</td>
                          <td className="px-5 py-4">{formatRupees(p.cost_price)}</td>
                          <td className="px-5 py-4">{formatRupees(p.selling_price)}</td>
                          <td className="px-5 py-4">{p.gst_rate}%</td>
                          <td className="px-5 py-4 font-medium">{p.available_quantity}</td>
                          <td className="px-5 py-4 text-muted-foreground">{p.reorder_level}</td>
                          <td className="px-5 py-4"><span className={statusClass}>{state}</span></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        ) : (
          /* Movement Ledger Tab */
          <section className="mt-4 rounded-xl border border-white/5 bg-card">
            <div className="border-b border-white/5 p-5">
              <h2 className="font-semibold">Movement Ledger</h2>
              <p className="mt-1 text-sm text-muted-foreground">Complete stock movement history — receipts, adjustments, and transfers.</p>
            </div>
            <div className="overflow-x-auto">
              {movements.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No movements recorded yet. Use Stock Inward to receive your first items.
                </div>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-5 py-3">Type</th>
                      <th className="px-5 py-3">Product</th>
                      <th className="px-5 py-3">Qty Change</th>
                      <th className="px-5 py-3">Reference</th>
                      <th className="px-5 py-3">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {movements.map((m) => {
                      const delta = parseFloat(m.quantity_delta);
                      const isPositive = delta > 0;
                      const typeLabel = m.type.replace(/_/g, " ");

                      const typeColor =
                        m.type === "receipt" ? "bg-emerald-400/10 text-emerald-300" :
                        m.type === "adjustment" ? "bg-amber-400/10 text-amber-300" :
                        m.type.startsWith("transfer") ? "bg-blue-400/10 text-blue-300" :
                        "bg-slate-400/10 text-slate-300";

                      return (
                        <tr key={m.id} className="border-t border-white/5 transition hover:bg-white/[.02]">
                          <td className="px-5 py-4">
                            <span className={`rounded-full px-2.5 py-1 text-xs capitalize ${typeColor}`}>{typeLabel}</span>
                          </td>
                          <td className="px-5 py-4 font-medium">{productMap.get(m.product_id) || m.product_id.slice(0, 8)}</td>
                          <td className="px-5 py-4">
                            <span className={`font-mono font-medium ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                              {isPositive ? "+" : ""}{m.quantity_delta}
                            </span>
                          </td>
                          <td className="px-5 py-4 text-muted-foreground font-mono text-xs">{m.reference_id ? m.reference_id.slice(0, 8) + "…" : "—"}</td>
                          <td className="px-5 py-4 text-muted-foreground">{new Date(m.occurred_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
