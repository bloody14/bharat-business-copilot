import { Sidebar } from "@/components/dashboard/sidebar";
import { Topbar } from "@/components/dashboard/topbar";

export default function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="flex min-h-screen"><Sidebar /><div className="min-w-0 flex-1"><Topbar />{children}</div></div>;
}
