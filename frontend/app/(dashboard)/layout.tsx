import { auth } from "@clerk/nextjs/server";
import { Sidebar } from "@/components/dashboard/sidebar";
import { Topbar } from "@/components/dashboard/topbar";

export default async function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await auth.protect();
  return <div className="flex min-h-screen"><Sidebar /><div className="min-w-0 flex-1"><Topbar />{children}</div></div>;
}
