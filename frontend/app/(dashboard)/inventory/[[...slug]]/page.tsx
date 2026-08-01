"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PackagePlus, Search, Loader2, AlertCircle } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { useAuth } from "@clerk/nextjs";

interface Product {
  name: string;
  sku: string;
  available_quantity: string;
  reorder_level: string;
}

export default function InventoryPage() {
  const { request } = useApi();
  const { orgId, isLoaded } = useAuth();
  
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    if (!orgId) {
      setIsLoading(false);
      setProducts([]);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    request("/api/v1/products")
      .then((res) => {
        if (isMounted) {
          setProducts(res);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error(err);
          setError(err.message || "Failed to load products");
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

  const totalProducts = products.length;
  const stockQuantity = products.reduce((acc, p) => acc + parseFloat(p.available_quantity || "0"), 0);
  const lowStock = products.filter(p => parseFloat(p.available_quantity) <= parseFloat(p.reorder_level) && parseFloat(p.available_quantity) > 0).length;
  const outOfStock = products.filter(p => parseFloat(p.available_quantity) <= 0).length;

  return (
    <main className="mx-auto max-w-7xl p-5 lg:p-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-emerald-400">Inventory</p>
          <h1 className="mt-1 text-3xl font-semibold">Keep every shelf in control.</h1>
          <p className="mt-2 text-sm text-muted-foreground">Catalogue, locations and stock movements in one ledger.</p>
        </div>
        <Link href="/inventory/products/new" className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground">
          <PackagePlus className="size-4"/>Add product
        </Link>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Total products", totalProducts.toString()],
          ["Stock quantity", stockQuantity.toString()],
          ["Low stock", lowStock.toString()],
          ["Out of stock", outOfStock.toString()]
        ].map(([a, b]) => (
          <article key={a} className="rounded-xl border border-white/5 bg-card p-5">
            <p className="text-sm text-muted-foreground">{a}</p>
            <p className="mt-3 text-2xl font-semibold">{b}</p>
            <p className="mt-3 flex items-center gap-1 text-xs text-emerald-400">Live data</p>
          </article>
        ))}
      </section>

      <section className="mt-6 rounded-xl border border-white/5 bg-card">
        <div className="flex flex-col gap-4 border-b border-white/5 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold">Products</h2>
            <p className="mt-1 text-sm text-muted-foreground">Stock status across all locations.</p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-muted-foreground">
            <Search className="size-4"/>Search products
          </div>
        </div>
        <div className="overflow-x-auto">
          {products.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No products found for this organization.
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-5 py-3">Product</th>
                  <th className="px-5 py-3">SKU</th>
                  <th className="px-5 py-3">Available</th>
                  <th className="px-5 py-3">Reorder at</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const available = parseFloat(p.available_quantity);
                  const reorder = parseFloat(p.reorder_level);
                  const state = available <= 0 ? "Out of stock" : (available <= reorder ? "Low stock" : "In stock");
                  
                  return (
                    <tr key={p.sku} className="border-t border-white/5">
                      <td className="px-5 py-4 font-medium">{p.name}</td>
                      <td className="px-5 py-4 text-muted-foreground">{p.sku}</td>
                      <td className="px-5 py-4">{p.available_quantity}</td>
                      <td className="px-5 py-4">{p.reorder_level}</td>
                      <td className="px-5 py-4">
                        <span className={state === "In stock" ? "rounded-full bg-emerald-400/10 px-2.5 py-1 text-xs text-emerald-300" : "rounded-full bg-amber-400/10 px-2.5 py-1 text-xs text-amber-300"}>
                          {state}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </main>
  );
}
