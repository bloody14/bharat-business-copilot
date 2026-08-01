"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Boxes, CircleHelp, FileText, LayoutDashboard, Megaphone, Settings, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard, active: true },
  { label: "Inventory", href: "/inventory", icon: Boxes, active: true },
  { label: "Billing", href: "/billing", icon: FileText, active: false },
  { label: "Customers", href: "/customers", icon: Users, active: false },
  { label: "Support", href: "/support", icon: CircleHelp, active: false },
  { label: "Analytics", href: "/analytics", icon: BarChart3, active: false },
  { label: "Marketing", href: "/marketing", icon: Megaphone, active: false }
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-white/5 bg-[#101827] px-4 py-6 lg:flex">
      <Link href="/dashboard" className="mb-10 flex items-center gap-3 px-2">
        <span className="grid size-9 place-items-center rounded-xl bg-emerald-500 text-lg font-bold text-slate-950 shadow-sm">B</span>
        <span className="font-semibold tracking-tight text-white">Bharat Copilot</span>
      </Link>
      <nav className="space-y-1">
        {navigation.map((item) => {
          const isActivePath = pathname?.startsWith(item.href);
          return (
            <Link 
              key={item.href} 
              href={item.active ? item.href : "#"} 
              className={cn(
                "group flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition",
                item.active 
                  ? isActivePath 
                    ? "bg-emerald-500/10 text-emerald-400" 
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                  : "text-slate-500 cursor-default"
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon className="size-4" />
                <span>{item.label}</span>
              </div>
              {!item.active && (
                <span className="text-[9px] uppercase tracking-wider font-semibold opacity-50 border border-slate-700 rounded px-1.5 py-0.5 group-hover:opacity-100 transition">Soon</span>
              )}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto">
        <Link href="/settings" className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/5 hover:text-white">
          <Settings className="size-4" />
          Settings
        </Link>
        <p className="mt-5 px-3 text-xs text-slate-600">Sprint 1 preview</p>
      </div>
    </aside>
  );
}
