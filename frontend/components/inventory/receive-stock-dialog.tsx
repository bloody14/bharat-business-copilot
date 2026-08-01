"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2 } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { useApi } from "@/hooks/use-api";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatQuantity } from "@/lib/format-indian";

interface ReceiveStockDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ProductOption {
  id: string;
  name: string;
  sku: string;
}

interface LocationOption {
  id: string;
  name: string;
  location_type: string;
}

export function ReceiveStockDialog({ open, onClose, onSuccess }: ReceiveStockDialogProps) {
  const { request } = useApi();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [products, setProducts] = useState<ProductOption[]>([]);
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  const [form, setForm] = useState({
    product_id: "",
    location_id: "",
    quantity: "",
    notes: "",
  });

  const loadOptions = useCallback(async () => {
    setDataLoading(true);
    try {
      const [prods, locs] = await Promise.all([
        request("/api/v1/products"),
        request("/api/v1/locations"),
      ]);
      setProducts(prods);
      setLocations(locs);
    } catch {
      setError("Failed to load products or locations");
    } finally {
      setDataLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (open) loadOptions();
  }, [open, loadOptions]);

  const resetForm = () => {
    setForm({ product_id: "", location_id: "", quantity: "", notes: "" });
    setError(null);
  };

  const handleClose = () => { resetForm(); onClose(); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!form.product_id) { setError("Please select a product."); return; }
    if (!form.location_id) { setError("Please select a location."); return; }
    if (!form.quantity || parseFloat(form.quantity) <= 0) { setError("Quantity must be greater than zero."); return; }

    setIsSubmitting(true);
    try {
      await request("/api/v1/inventory/receipts", {
        method: "POST",
        body: JSON.stringify({
          product_id: form.product_id,
          location_id: form.location_id,
          quantity: form.quantity,
          notes: form.notes || null,
        }),
      });
      toast.success(`${formatQuantity(form.quantity)} units received`);
      handleClose();
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to receive stock");
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-lg border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400/50 focus:outline-none focus:ring-1 focus:ring-emerald-400/30 transition";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1.5";

  return (
    <Dialog open={open} onClose={handleClose} title="Stock Inward" description="Receive stock into a location.">
      {dataLoading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="size-6 animate-spin text-emerald-400" /></div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Product *</label>
            {products.length === 0 ? (
              <p className="text-sm text-amber-400">No products in catalogue. Add a product first.</p>
            ) : (
              <Select value={form.product_id} onValueChange={(val) => setForm({ ...form, product_id: val })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select product…" />
                </SelectTrigger>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.name} ({p.sku})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div>
            <label className={labelClass}>Location *</label>
            {locations.length === 0 ? (
              <p className="text-sm text-amber-400">No locations found. Add a location first.</p>
            ) : (
              <Select value={form.location_id} onValueChange={(val) => setForm({ ...form, location_id: val })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select location…" />
                </SelectTrigger>
                <SelectContent>
                  {locations.map((l) => (
                    <SelectItem key={l.id} value={l.id}>{l.name} ({l.location_type})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div>
            <label className={labelClass}>Quantity *</label>
            <input className={inputClass} type="number" step="0.001" min="0.001" placeholder="Enter quantity" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
          </div>

          <div>
            <label className={labelClass}>Notes / Reference</label>
            <textarea className={inputClass + " resize-none"} rows={2} placeholder="Invoice number, supplier, etc." value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>

          {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={handleClose} className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-white/5">Cancel</button>
            <button type="submit" disabled={isSubmitting || products.length === 0 || locations.length === 0} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:opacity-50">
              {isSubmitting ? <><Loader2 className="size-4 animate-spin" />Recording…</> : "Receive Stock"}
            </button>
          </div>
        </form>
      )}
    </Dialog>
  );
}
