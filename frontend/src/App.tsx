import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { AnalyticsPanel } from "@/components/layout/AnalyticsPanel";
import { DataDrawer } from "@/components/layout/DataDrawer";
import { MapContainer } from "@/components/map/MapContainer";
import { MapControls } from "@/components/map/MapControls";
import { MapLegend } from "@/components/map/MapLegend";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 30_000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex h-screen flex-col overflow-hidden bg-slate-950 font-sans text-slate-100">
        <Header />
        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <main className="flex min-w-0 flex-1 flex-col">
            <div className="relative min-h-0 flex-1">
              <MapContainer>
                <MapControls />
                <MapLegend />
              </MapContainer>
            </div>
            <DataDrawer />
          </main>
          <AnalyticsPanel />
        </div>
      </div>
    </QueryClientProvider>
  );
}
