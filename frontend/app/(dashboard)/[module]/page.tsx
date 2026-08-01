import { Construction } from "lucide-react";

const titles: Record<string, string> = { inventory: "Inventory", billing: "Billing", customers: "Customers", support: "Support", analytics: "Analytics", marketing: "Marketing", settings: "Settings" };

export default async function PlaceholderPage({ params }: { params: Promise<{ module: string }> }) {
  const { module } = await params;
  const title = titles[module] ?? "Workspace";
  return <main className="grid min-h-[calc(100vh-5rem)] place-items-center p-5"><section className="max-w-md text-center"><div className="mx-auto grid size-12 place-items-center rounded-xl bg-emerald-400/10 text-emerald-300"><Construction className="size-6" /></div><h1 className="mt-5 text-2xl font-semibold">{title}</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">This workspace is reserved for a later approved sprint. The platform foundation is ready.</p></section></main>;
}
