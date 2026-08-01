import { Bell, Menu, Search } from "lucide-react";
import { UserButton, OrganizationSwitcher } from "@clerk/nextjs";

export function Topbar() {
  return <header className="flex h-20 items-center justify-between border-b border-white/5 px-5 lg:px-8"><div className="flex items-center gap-3"><button className="rounded-lg p-2 hover:bg-white/5 lg:hidden" aria-label="Open navigation"><Menu className="size-5" /></button><div className="hidden items-center gap-2 rounded-lg border border-white/5 bg-white/[.03] px-3 py-2 text-sm text-slate-500 md:flex"><Search className="size-4" />Search anything… <kbd className="ml-20 text-xs">⌘ K</kbd></div></div><div className="flex items-center gap-4"><OrganizationSwitcher hidePersonal appearance={{ elements: { organizationSwitcherTrigger: "text-slate-300 hover:text-white", organizationPreviewTextContainer: "text-slate-300" } }} /><button className="relative rounded-lg p-2 text-slate-300 hover:bg-white/5" aria-label="Notifications"><Bell className="size-5" /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-emerald-400" /></button><UserButton appearance={{ elements: { userButtonAvatarBox: "size-9" } }} /></div></header>;
}
