"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, CheckCircle2, ArrowRightLeft } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { useApi } from "@/hooks/use-api";

interface TransferStockDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ProductOption { id: string; name: string; sku: string; }
interface LocationOption { id: string; name: string; location_type: string; }

export function TransferStockDialog({ open, onClose, onSuccess }: TransferStockDialogProps) {
  const { request } = useApi();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  const [form, setForm] = useState({
    product_id: "",
    location_id: "",
    destination_location_id: "",
    quantity: "",
    notes: "",
  });

  const loadOptions = useCallback(async () => {
    setDataLoading(true);
    try {
      const [prods, locs] = await Promise.all([request("/api/v1/products"), request("/api/v1/locations")]);
      setProducts(prods);
      setLocations(locs);
    } catch { setError("Failed to load products or locations"); }
    finally { setDataLoading(false); }
  }, [request]);

  useEffect(() => { if (open) loadOptions(); }, [open, loadOptions]);

  const resetForm = () => {
    setForm({ product_id: "", location_id: "", destination_location_id: "", quantity: "", notes: "" });
    setError(null);
    setSuccess(false);
  };

  const handleClose = () => { resetForm(); onClose(); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!form.product_id) { setError("Please select a product."); return; }
    if (!form.location_id) { setError("Please select the source location."); return; }
    if (!form.destination_location_id) { setError("Please select the destination location."); return; }
    if (form.location_id === form.destination_location_id) { setError("Source and destination must be different locations."); return; }
    if (!form.quantity || parseFloat(form.quantity) <= 0) { setError("Quantity must be greater than zero."); return; }

    setIsSubmitting(true);
    try {
      await request("/api/v1/inventory/transfers", {
        method: "POST",
        body: JSON.stringify({
          product_id: form.product_id,
          location_id: form.location_id,
          destination_location_id: form.destination_location_id,
          quantity: form.quantity,
          notes: form.notes || null,
        }),
      });
      setSuccess(true);
      setTimeout(() => { handleClose(); onSuccess(); }, 800);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Transfer failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-lg border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400/50 focus:outline-none focus:ring-1 focus:ring-emerald-400/30 transition";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1.5";
  const selectClass = "w-full rounded-lg border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white focus:border-emerald-400/50 focus:outline-none focus:ring-1 focus:ring-emerald-400/30 transition appearance-none";

  const hasMultipleLocations = locations.length >= 2;

  return (
    <Dialog open={open} onClose={handleClose} title="Transfer Stock" description="Move stock between locations.">
      {success ? (
        <div className="flex flex-col items-center py-6 text-emerald-400">
          <CheckCircle2 className="size-12" />
          <p className="mt-3 font-medium">Stock transferred successfully!</p>
        </div>
      ) : dataLoading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="size-6 animate-spin text-emerald-400" /></div>
      ) : !hasMultipleLocations ? (
        <div className="py-8 text-center">
          <ArrowRightLeft className="mx-auto size-10 text-slate-500" />
          <p className="mt-3 text-sm text-slate-400">You need at least two locations to transfer stock.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Product *</label>
            <select className={selectClass} value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}>
              <option value="">Select product…</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>From Location *</label>
              <select className={selectClass} value={form.location_id} onChange={(e) => setForm({ ...form, location_id: e.target.value })}>
                <option value="">Source…</option>
                {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>To Location *</label>
              <select className={selectClass} value={form.destination_location_id} onChange={(e) => setForm({ ...form, destination_location_id: e.target.value })}>
                <option value="">Destination…</option>
                {locations.filter((l) => l.id !== form.location_id).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className={labelClass}>Quantity *</label>
            <input className={inputClass} type="number" step="0.001" min="0.001" placeholder="Enter quantity" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
          </div>

          <div>
            <label className={labelClass}>Notes</label>
            <textarea className={inputClass + " resize-none"} rows={2} placeholder="Transfer reason or reference" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>

          {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={handleClose} className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-white/5">Cancel</button>
            <button type="submit" disabled={isSubmitting} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:opacity-50">
              {isSubmitting ? <><Loader2 className="size-4 animate-spin" />Transferring…</> : "Transfer Stock"}
            </button>
          </div>
        </form>
      )}
    </Dialog>
  );
}
