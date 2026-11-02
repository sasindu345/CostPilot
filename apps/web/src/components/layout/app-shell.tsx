import { AuthGate } from "@/components/layout/auth-gate";
import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { QueryProvider } from "@/components/providers/query-provider";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <QueryProvider>
      <AuthGate>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex flex-1 flex-col">
            <TopBar />
            <main className="flex-1 p-8">{children}</main>
          </div>
        </div>
      </AuthGate>
    </QueryProvider>
  );
}
