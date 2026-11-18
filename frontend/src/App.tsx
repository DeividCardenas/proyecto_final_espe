import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header, MobileTabBar } from "@/components/layout/Header";
import { useIsMobile } from "@/hooks/useIsMobile";
import { Sidebar } from "@/components/layout/Sidebar";
import { AnalyticsPanel } from "@/components/layout/AnalyticsPanel";
import { DataDrawer } from "@/components/layout/DataDrawer";
import { MapContainer } from "@/components/map/MapContainer";
import { MapControls } from "@/components/map/MapControls";
import { MapLegend } from "@/components/map/MapLegend";
import { GuideInvite } from "@/components/tour/GuideInvite";
import { useEffect, useState } from "react";
import { IntroScreen, introSeen } from "@/components/intro/IntroScreen";
import { useTheme } from "@/stores/useThemeStore";
import { useUiStore } from "@/stores/useUiStore";
import { applyThemeVars } from "@/theme/themes";
import { loadThemeFonts } from "@/theme/fonts";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 30_000 } },
});

function ThemeSync() {
  const theme = useTheme();
  useEffect(() => {
    void loadThemeFonts(theme.id);
    applyThemeVars(theme);
  }, [theme]);
  return null;
}

/** Escape cierra lo último que se abre encima del mapa: la tabla y luego los filtros. */
function EscapeToClose() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented) return;
      const t = e.target as HTMLElement | null;
      if (t && /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName)) return;
      const ui = useUiStore.getState();
      if (ui.drawerOpen) ui.toggleDrawer();
      else if (ui.filtersOpen) ui.toggleFilters();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return null;
}

export default function App() {
  // La portada se monta encima: el mapa y los datos cargan detrás mientras se lee
  const [intro, setIntro] = useState(() => !introSeen());
  const mobile = useIsMobile();
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeSync />
      <EscapeToClose />
      <div className="hud-app flex h-screen flex-col supports-[height:100dvh]:h-[100dvh] overflow-hidden bg-slate-950 font-sans text-slate-100">
        <Header />
        {/* Móvil: mapa arriba y el panel como hoja inferior; escritorio: tres columnas */}
        <div className="relative flex min-h-0 flex-1 flex-col md:flex-row">
          <Sidebar />
          <main className="flex min-w-0 flex-1 flex-col">
            <div className="relative min-h-0 flex-1 overflow-hidden">
              <MapContainer>
                <MapControls />
                <MapLegend />
                {!intro && <GuideInvite />}
              </MapContainer>
            </div>
            <DataDrawer />
          </main>
          <AnalyticsPanel />
        </div>
        {mobile && <MobileTabBar />}
      </div>
      {intro && <IntroScreen onClose={() => setIntro(false)} />}
    </QueryClientProvider>
  );
}
