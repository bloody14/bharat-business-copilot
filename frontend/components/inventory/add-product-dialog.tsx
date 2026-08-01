"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { useApi } from "@/hooks/use-api";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const UNITS = ["piece", "packet", "box", "kg", "gram", "litre", "ml"] as const;
const GST_RATES = ["0", "5", "12", "18", "28"] as const;

interface AddProductDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function AddProductDialog({ open, onClose, onSuccess }: AddProductDialogProps) {
  const { request } = useApi();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    sku: "",
    unit: "piece" as string,
    hsn_sac: "",
    cost_price: "",
    selling_price: "",
    gst_rate: "5" as string,
    reorder_level: "0",
  });

  const resetForm = () => {
    setForm({ name: "", sku: "", unit: "piece", hsn_sac: "", cost_price: "", selling_price: "", gst_rate: "5", reorder_level: "0" });
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (form.name.trim().length < 2) { setError("Product name must be at least 2 characters."); return; }
    if (form.sku.trim().length < 2) { setError("SKU must be at least 2 characters."); return; }
    if (!form.cost_price || parseFloat(form.cost_price) < 0) { setError("Cost price must be 0 or more."); return; }
    if (!form.selling_price || parseFloat(form.selling_price) < 0) { setError("Selling price must be 0 or more."); return; }
    if (form.hsn_sac && !/^\d{4,8}$/.test(form.hsn_sac)) { setError("HSN/SAC code must be 4-8 digits."); return; }

    setIsSubmitting(true);
    try {
      await request("/api/v1/products", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          sku: form.sku.trim(),
          unit: form.unit,
          hsn_sac: form.hsn_sac || null,
          cost_price: form.cost_price,
          selling_price: form.selling_price,
          gst_rate: form.gst_rate,
          reorder_level: form.reorder_level || "0",
        }),
      });
      toast.success("Product added successfully");
      handleClose();
      onSuccess();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create product";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-lg border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400/50 focus:outline-none focus:ring-1 focus:ring-emerald-400/30 transition";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1.5";
  const sectionTitleClass = "text-xs font-semibold uppercase tracking-wider text-emerald-400/80 mb-3";

  return (
    <Dialog open={open} onClose={handleClose} title="Add New Product" description="Add a product to your catalogue.">
      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Basic Information */}
        <fieldset>
          <legend className={sectionTitleClass}>Basic Information</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={labelClass}>Product Name *</label>
              <input className={inputClass} placeholder="e.g. Tata Salt 1 kg" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div>
              <label className={labelClass}>SKU *</label>
              <input className={inputClass} placeholder="e.g. TATA-SALT-1KG" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} required />
            </div>
            <div>
              <label className={labelClass}>Unit *</label>
              <Select value={form.unit} onValueChange={(val) => setForm({ ...form, unit: val })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select unit" />
                </SelectTrigger>
                <SelectContent>
                  {UNITS.map((u) => (
                    <SelectItem key={u} value={u}>{u.charAt(0).toUpperCase() + u.slice(1)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </fieldset>

        {/* Tax & Pricing */}
        <fieldset>
          <legend className={sectionTitleClass}>Tax & Pricing</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>HSN/SAC Code</label>
              <input className={inputClass} placeholder="4-8 digit code" value={form.hsn_sac} onChange={(e) => setForm({ ...form, hsn_sac: e.target.value })} />
            </div>
            <div>
              <label className={labelClass}>GST Rate *</label>
              <Select value={form.gst_rate} onValueChange={(val) => setForm({ ...form, gst_rate: val })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select GST" />
                </SelectTrigger>
                <SelectContent>
                  {GST_RATES.map((r) => (
                    <SelectItem key={r} value={r}>{r}%</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className={labelClass}>Cost Price (₹) *</label>
              <input className={inputClass} type="number" step="0.01" min="0" placeholder="0.00" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} required />
            </div>
            <div>
              <label className={labelClass}>MRP / Selling Price (₹) *</label>
              <input className={inputClass} type="number" step="0.01" min="0" placeholder="0.00" value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} required />
            </div>
          </div>
        </fieldset>

        {/* Inventory */}
        <fieldset>
          <legend className={sectionTitleClass}>Inventory</legend>
          <div>
            <label className={labelClass}>Reorder Level</label>
            <input className={inputClass} type="number" step="1" min="0" placeholder="Minimum stock before alert" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: e.target.value })} />
          </div>
        </fieldset>

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={handleClose} className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-white/5">
            Cancel
          </button>
          <button type="submit" disabled={isSubmitting} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:opacity-50">
            {isSubmitting ? <><Loader2 className="size-4 animate-spin" />Creating…</> : "Add Product"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
