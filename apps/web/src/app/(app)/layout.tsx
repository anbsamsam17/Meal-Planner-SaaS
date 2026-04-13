// apps/web/src/app/(app)/layout.tsx
// Layout app authentifié — navigation adaptative
// Mobile : BottomNav (4 items, 64px, fixé en bas)
// Desktop (lg+) : Sidebar (240px, fixe gauche)
// Référence : 04-components-catalog.md #17 BottomNav et #18 Sidebar
// Référence : 07-responsive-breakpoints.md
import { redirect } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import { AppBottomNav } from "@/components/navigation/app-bottom-nav";
import { AppSidebar } from "@/components/navigation/app-sidebar";

interface AppLayoutProps {
  children: React.ReactNode;
}

export default async function AppLayout({ children }: AppLayoutProps) {
  // Vérification de l'authentification côté serveur
  const supabase = createServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Rediriger vers la page de connexion si non authentifié
  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-neutral-50">
      {/* Sidebar desktop — visible à partir de lg */}
      <aside className="hidden lg:block">
        <AppSidebar />
      </aside>

      {/* Zone de contenu principal */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Contenu scrollable */}
        <main
          id="main-content"
          className="flex-1 overflow-y-auto overscroll-y-contain"
        >
          {children}
        </main>

        {/* Bottom Nav mobile — visible jusqu'à lg */}
        <nav
          className="safe-bottom border-t border-neutral-200 bg-neutral-50 shadow-2xl lg:hidden"
          aria-label="Navigation principale"
        >
          <AppBottomNav />
        </nav>
      </div>
    </div>
  );
}
