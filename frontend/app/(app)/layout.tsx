import AuthGuard from "@/components/layout/AuthGuard";
import Header from "@/components/layout/Header";
import NimKeyLoader from "@/components/layout/NimKeyLoader";
import Sidebar from "@/components/layout/Sidebar";
import Toaster from "@/components/ui/Toaster";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <NimKeyLoader />
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto bg-paper">
            {children}
          </main>
        </div>
      </div>
      <Toaster />
    </AuthGuard>
  );
}
