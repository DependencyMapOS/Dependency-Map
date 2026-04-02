import { AppSidebar } from "@/components/app-sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { UserNav } from "@/components/user-nav";
import { createClient } from "@/lib/supabase/server";

export default async function DashboardGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4 md:px-6">
          <span className="text-sm text-muted-foreground md:hidden">Dependency Map</span>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <UserNav email={user?.email ?? null} />
          </div>
        </header>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}
