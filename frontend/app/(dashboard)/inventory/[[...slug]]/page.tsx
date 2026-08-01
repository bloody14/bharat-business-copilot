"use client";

import { useEffect, useState, useCallback } from "react";
import { PackagePlus, Search, AlertCircle, Download, ArrowRightLeft, Wrench, MapPin, ClipboardList, LayoutGrid, List } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@clerk/nextjs";
import { formatRupees, formatQuantity } from "@/lib/format-indian";

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

type Tab = "products" | "movements";
type ViewMode = "table" | "grid";

export default function InventoryPage() {
  const { request } = useApi();
  const { orgId, isLoaded } = useAuth();

  const [products, setProducts] = useState<Product[]>([]);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("products");
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [searchQuery, setSearchQuery] = useState("");

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

  // ── Guards & Skeletons ─────────────────────────────────────────────

  if (!isLoaded || isLoading) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 animate-pulse space-y-8">
        <div className="h-16 w-1/3 rounded-lg bg-white/5" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 rounded-xl bg-white/5" />)}
        </div>
        <div className="h-12 w-2/3 rounded-lg bg-white/5" />
        <div className="h-64 rounded-xl bg-white/5" />
      </main>
    );
  }

  if (!orgId) {
    return (
      <main className="mx-auto max-w-7xl p-5 lg:p-8 text-center flex h-full items-center justify-center min-h-[60vh]">
        <div className="rounded-xl border border-white/5 bg-card p-12 max-w-md w-full shadow-lg">
          <AlertCircle className="mx-auto size-12 text-amber-400" />
          <h2 className="mt-4 text-xl font-semibold">No Organization Active</h2>
          <p className="mt-2 text-slate-400">Please select or create an organization using the account menu to view your inventory.</p>
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
          <button onClick={fetchData} className="mt-6 rounded-lg bg-white/10 px-4 py-2 text-sm hover:bg-white/20 transition">Retry</button>
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

  const productMap = new Map(products.map(p => [p.id, p.name]));

  // ── Render Helpers ──────────────────────────────────────────────────

  const getProductState = (p: Product) => {
    const available = parseFloat(p.available_quantity);
    const reorder = parseFloat(p.reorder_level);
    const state = available <= 0 ? "Out of stock" : available <= reorder ? "Low stock" : "In stock";
    const statusClass = state === "In stock"
      ? "bg-emerald-400/10 text-emerald-300 border-emerald-400/20"
      : state === "Low stock"
        ? "bg-amber-400/10 text-amber-300 border-amber-400/20"
        : "bg-red-400/10 text-red-300 border-red-400/20";
    return { state, statusClass };
  };

  return (
    <>
      <AddProductDialog open={showAddProduct} onClose={() => setShowAddProduct(false)} onSuccess={onMutationSuccess} />
      <ReceiveStockDialog open={showReceiveStock} onClose={() => setShowReceiveStock(false)} onSuccess={onMutationSuccess} />
      <AdjustStockDialog open={showAdjustStock} onClose={() => setShowAdjustStock(false)} onSuccess={onMutationSuccess} />
      <TransferStockDialog open={showTransferStock} onClose={() => setShowTransferStock(false)} onSuccess={onMutationSuccess} />
      <AddLocationDialog open={showAddLocation} onClose={() => setShowAddLocation(false)} onSuccess={onMutationSuccess} />

      <main className="mx-auto max-w-7xl p-5 lg:p-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-medium text-emerald-400">Inventory Management</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">Keep every shelf in control.</h1>
            <p className="mt-2 text-sm text-muted-foreground">Catalogue, locations and stock movements in one ledger.</p>
          </div>
          <div className="flex flex-wrap gap-2 w-full md:w-auto">
            <button onClick={() => setShowAddLocation(true)} className="flex-1 md:flex-none inline-flex justify-center items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/5 hover:text-white shadow-sm">
              <MapPin className="size-4" />Location
            </button>
            <button onClick={() => setShowAddProduct(true)} className="flex-1 md:flex-none inline-flex justify-center items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600 shadow-sm shadow-emerald-500/20">
              <PackagePlus className="size-4" />Add Product
            </button>
          </div>
        </div>

        <section className="mt-8 grid gap-4 grid-cols-2 lg:grid-cols-4">
          {[
            ["Total Products", totalProducts.toString(), "In catalogue", "bg-blue-500/10 text-blue-400"],
            ["Stock Quantity", formatQuantity(stockQuantity), "Total items", "bg-emerald-500/10 text-emerald-400"],
            ["Low Stock", lowStock.toString(), "Needs reordering", "bg-amber-500/10 text-amber-400"],
            ["Out of Stock", outOfStock.toString(), "Zero inventory", "bg-red-500/10 text-red-400"],
          ].map(([a, b, c, colorClass]) => (
            <article key={a} className="rounded-xl border border-white/5 bg-card p-5 shadow-sm transition hover:border-white/10 flex flex-col justify-between">
              <p className="text-sm font-medium text-muted-foreground">{a}</p>
              <div className="mt-3">
                <p className="text-3xl font-semibold tracking-tight">{b}</p>
                <p className={`mt-2 text-xs font-medium w-fit px-2 py-0.5 rounded-full ${colorClass}`}>{c}</p>
              </div>
            </article>
          ))}
        </section>

        <section className="mt-6 flex flex-wrap gap-2">
          <button onClick={() => setShowReceiveStock(true)} className="inline-flex items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/5 px-4 py-2.5 text-sm font-medium text-emerald-300 transition hover:bg-emerald-400/10 hover:border-emerald-400/30">
            <Download className="size-4" />Stock Inward
          </button>
          <button onClick={() => setShowAdjustStock(true)} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/5 hover:text-white">
            <Wrench className="size-4" />Adjust Stock
          </button>
          <button onClick={() => setShowTransferStock(true)} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/5 hover:text-white">
            <ArrowRightLeft className="size-4" />Transfer
          </button>
        </section>

        <div className="mt-8 flex gap-1 rounded-lg border border-white/5 bg-white/[.02] p-1 w-fit">
          <button onClick={() => setTab("products")} className={`rounded-md px-4 py-2 text-sm font-medium transition ${tab === "products" ? "bg-white/10 text-white shadow-sm" : "text-slate-400 hover:text-white"}`}>
            <PackagePlus className="mr-2 inline size-4" />Products
          </button>
          <button onClick={() => setTab("movements")} className={`rounded-md px-4 py-2 text-sm font-medium transition ${tab === "movements" ? "bg-white/10 text-white shadow-sm" : "text-slate-400 hover:text-white"}`}>
            <ClipboardList className="mr-2 inline size-4" />Movement Ledger
          </button>
        </div>

        {tab === "products" ? (
          <section className="mt-4 rounded-xl border border-white/5 bg-card shadow-sm overflow-hidden">
            <div className="flex flex-col gap-4 border-b border-white/5 p-5 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="font-semibold text-lg">Product Catalogue</h2>
                <p className="mt-1 text-sm text-muted-foreground">Manage your items and track current stock.</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[.02] px-3 py-2 text-sm text-muted-foreground focus-within:border-emerald-400/50 focus-within:ring-1 focus-within:ring-emerald-400/30 transition flex-1 md:w-64">
                  <Search className="size-4 shrink-0" />
                  <input className="w-full bg-transparent outline-none placeholder:text-slate-500 text-white" placeholder="Search product or SKU…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
                </div>
                <div className="hidden md:flex rounded-lg border border-white/10 bg-white/[.02] p-1">
                  <button onClick={() => setViewMode("table")} className={`p-1.5 rounded-md transition ${viewMode === "table" ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"}`} title="Table View"><List className="size-4" /></button>
                  <button onClick={() => setViewMode("grid")} className={`p-1.5 rounded-md transition ${viewMode === "grid" ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"}`} title="Grid View"><LayoutGrid className="size-4" /></button>
                </div>
              </div>
            </div>
            
            {filteredProducts.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-center">
                <div className="rounded-full bg-white/5 p-4 mb-4">
                  <PackagePlus className="size-8 text-slate-400" />
                </div>
                {products.length === 0 ? (
                  <>
                    <h3 className="text-lg font-medium text-white mb-1">No products yet</h3>
                    <p className="text-slate-400 mb-6 max-w-sm">Add your first product to start tracking your inventory and managing stock.</p>
                    <button onClick={() => setShowAddProduct(true)} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600">
                      Add Product
                    </button>
                  </>
                ) : (
                  <>
                    <h3 className="text-lg font-medium text-white mb-1">No results found</h3>
                    <p className="text-slate-400">No products match the search &quot;{searchQuery}&quot;.</p>
                  </>
                )}
              </div>
            ) : viewMode === "grid" ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-5">
                {filteredProducts.map(p => {
                  const { state, statusClass } = getProductState(p);
                  return (
                    <div key={p.id} className="rounded-lg border border-white/5 bg-white/[.02] p-4 flex flex-col transition hover:border-white/10">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="font-semibold text-white line-clamp-1">{p.name}</h3>
                          <p className="text-xs font-mono text-slate-400 mt-0.5">{p.sku}</p>
                        </div>
                        <span className={`px-2 py-1 text-[10px] uppercase font-bold tracking-wider rounded border ${statusClass}`}>{state}</span>
                      </div>
                      <div className="mt-auto grid grid-cols-2 gap-y-3 pt-3 border-t border-white/5 text-sm">
                        <div><p className="text-xs text-slate-500">MRP</p><p className="font-medium">{formatRupees(p.selling_price)}</p></div>
                        <div><p className="text-xs text-slate-500">Stock</p><p className="font-medium text-white">{formatQuantity(p.available_quantity)} {p.unit}</p></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="text-xs uppercase tracking-wide text-muted-foreground bg-white/[.01]">
                    <tr>
                      <th className="px-5 py-4 font-medium">Product</th>
                      <th className="px-5 py-4 font-medium">SKU</th>
                      <th className="px-5 py-4 font-medium">Cost</th>
                      <th className="px-5 py-4 font-medium">MRP</th>
                      <th className="px-5 py-4 font-medium">GST</th>
                      <th className="px-5 py-4 font-medium text-right">Available</th>
                      <th className="px-5 py-4 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredProducts.map((p) => {
                      const { state, statusClass } = getProductState(p);
                      return (
                        <tr key={p.sku} className="transition hover:bg-white/[.02]">
                          <td className="px-5 py-4">
                            <p className="font-medium text-white">{p.name}</p>
                            <p className="text-xs text-slate-500 md:hidden mt-1">{p.sku}</p>
                          </td>
                          <td className="px-5 py-4 text-muted-foreground font-mono text-xs">{p.sku}</td>
                          <td className="px-5 py-4 text-slate-300">{formatRupees(p.cost_price)}</td>
                          <td className="px-5 py-4 font-medium text-slate-200">{formatRupees(p.selling_price)}</td>
                          <td className="px-5 py-4 text-slate-400">{p.gst_rate}%</td>
                          <td className="px-5 py-4 font-medium text-right text-white">
                            {formatQuantity(p.available_quantity)}
                            <span className="text-xs text-slate-500 ml-1.5 font-normal">{p.unit}</span>
                          </td>
                          <td className="px-5 py-4">
                            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusClass}`}>{state}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ) : (
          <section className="mt-4 rounded-xl border border-white/5 bg-card shadow-sm overflow-hidden">
            <div className="border-b border-white/5 p-5">
              <h2 className="font-semibold text-lg">Movement Ledger</h2>
              <p className="mt-1 text-sm text-muted-foreground">Complete stock movement history — receipts, adjustments, and transfers.</p>
            </div>
            <div className="overflow-x-auto">
              {movements.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 text-center">
                  <div className="rounded-full bg-white/5 p-4 mb-4">
                    <ClipboardList className="size-8 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-medium text-white mb-1">No movements yet</h3>
                  <p className="text-slate-400 mb-6 max-w-sm">Use &quot;Stock Inward&quot; to receive items from suppliers and build your ledger.</p>
                  <button onClick={() => setShowReceiveStock(true)} className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/20">
                    <Download className="size-4" />Stock Inward
                  </button>
                </div>
              ) : (
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="text-xs uppercase tracking-wide text-muted-foreground bg-white/[.01]">
                    <tr>
                      <th className="px-5 py-4 font-medium">Date</th>
                      <th className="px-5 py-4 font-medium">Type</th>
                      <th className="px-5 py-4 font-medium">Product</th>
                      <th className="px-5 py-4 font-medium text-right">Qty Change</th>
                      <th className="px-5 py-4 font-medium">Reference</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {movements.map((m) => {
                      const delta = parseFloat(m.quantity_delta);
                      const isPositive = delta > 0;
                      const typeLabel = m.type.replace(/_/g, " ");

                      const typeColor =
                        m.type === "receipt" ? "bg-emerald-400/10 text-emerald-300 border-emerald-400/20" :
                        m.type === "adjustment" ? "bg-amber-400/10 text-amber-300 border-amber-400/20" :
                        m.type.startsWith("transfer") ? "bg-blue-400/10 text-blue-300 border-blue-400/20" :
                        "bg-slate-400/10 text-slate-300 border-slate-400/20";

                      return (
                        <tr key={m.id} className="transition hover:bg-white/[.02]">
                          <td className="px-5 py-4 text-slate-400">{new Date(m.occurred_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                          <td className="px-5 py-4">
                            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${typeColor}`}>{typeLabel}</span>
                          </td>
                          <td className="px-5 py-4 font-medium text-slate-200">{productMap.get(m.product_id) || m.product_id.slice(0, 8)}</td>
                          <td className="px-5 py-4 text-right">
                            <span className={`font-mono font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                              {isPositive ? "+" : ""}{formatQuantity(m.quantity_delta)}
                            </span>
                          </td>
                          <td className="px-5 py-4 text-muted-foreground font-mono text-xs">{m.reference_id ? m.reference_id.slice(0, 8) + "…" : "—"}</td>
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
