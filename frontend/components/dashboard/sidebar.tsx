import Link from "next/link";
import { BarChart3, Boxes, CircleHelp, FileText, LayoutDashboard, Megaphone, Settings, Users } from "lucide-react";

const navigation = [
  ["Overview", "/dashboard", LayoutDashboard], ["Inventory", "/inventory", Boxes], ["Billing", "/billing", FileText], ["Customers", "/customers", Users], ["Support", "/support", CircleHelp], ["Analytics", "/analytics", BarChart3], ["Marketing", "/marketing", Megaphone]
] as const;

export function Sidebar() {
  return <aside className="hidden w-64 shrink-0 flex-col border-r border-white/5 bg-[#101827] px-4 py-6 lg:flex">
    <Link href="/dashboard" className="mb-10 flex items-center gap-3 px-2"><span className="grid size-9 place-items-center rounded-xl bg-emerald-400 text-lg font-bold text-slate-950">B</span><span className="font-semibold tracking-tight">Bharat Copilot</span></Link>
    <nav className="space-y-1">{navigation.map(([label, href, Icon]) => <Link key={href} href={href} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"><Icon className="size-4" />{label}</Link>)}</nav>
    <div className="mt-auto"><Link href="/settings" className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"><Settings className="size-4" />Settings</Link><p className="mt-5 px-3 text-xs text-slate-500">Sprint 1 preview</p></div>
  </aside>;
}
