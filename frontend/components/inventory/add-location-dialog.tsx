"use client";

import { useState } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { useApi } from "@/hooks/use-api";

const LOCATION_TYPES = ["store", "warehouse", "godown", "shelf", "other"] as const;

interface AddLocationDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function AddLocationDialog({ open, onClose, onSuccess }: AddLocationDialogProps) {
  const { request } = useApi();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    name: "",
    location_type: "store" as string,
  });

  const resetForm = () => { setForm({ name: "", location_type: "store" }); setError(null); setSuccess(false); };
  const handleClose = () => { resetForm(); onClose(); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (form.name.trim().length < 2) { setError("Location name must be at least 2 characters."); return; }

    setIsSubmitting(true);
    try {
      await request("/api/v1/locations", {
        method: "POST",
        body: JSON.stringify({ name: form.name.trim(), location_type: form.location_type }),
      });
      setSuccess(true);
      setTimeout(() => { handleClose(); onSuccess(); }, 800);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create location");
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-lg border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400/50 focus:outline-none focus:ring-1 focus:ring-emerald-400/30 transition";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1.5";
  const selectClass = "w-full rounded-lg border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white focus:border-emerald-400/50 focus:outline-none focus:ring-1 focus:ring-emerald-400/30 transition appearance-none";

  return (
    <Dialog open={open} onClose={handleClose} title="Add Location" description="Create a new inventory location (store, godown, etc.)">
      {success ? (
        <div className="flex flex-col items-center py-6 text-emerald-400">
          <CheckCircle2 className="size-12" />
          <p className="mt-3 font-medium">Location created!</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Location Name *</label>
            <input className={inputClass} placeholder="e.g. Main Store, Back Godown" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label className={labelClass}>Location Type *</label>
            <select className={selectClass} value={form.location_type} onChange={(e) => setForm({ ...form, location_type: e.target.value })}>
              {LOCATION_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>

          {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={handleClose} className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-white/5">Cancel</button>
            <button type="submit" disabled={isSubmitting} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:opacity-50">
              {isSubmitting ? <><Loader2 className="size-4 animate-spin" />Creating…</> : "Add Location"}
            </button>
          </div>
        </form>
      )}
    </Dialog>
  );
}
