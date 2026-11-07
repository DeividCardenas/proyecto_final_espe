import { useCallback, useEffect, useRef, type ReactNode } from "react";
import { Popup, type GeoJSONSource, type MapGeoJSONFeature, type MapLayerMouseEvent, type Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useQuery } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";
import { MapProvider } from "@/context/MapContext";
import { BASEMAP_STYLE, useMapLibre } from "@/hooks/useMapLibre";
import { useSpatialFilters } from "@/hooks/useSpatialFilters";
import { useTopSegments } from "@/hooks/useTopSegments";
import { useQueryFilters, useViewportCrashes } from "@/hooks/useViewportCrashes";
import { crashService } from "@/services/crashService";
import { useFilterStore } from "@/stores/useFilterStore";
import { CHICAGO_CENTER, CHICAGO_MAX_BOUNDS, useMapStore, type LayerId } from "@/stores/useMapStore";
import { useUiStore } from "@/stores/useUiStore";
import { addCrashTileLayers, HEATMAP_LAYER, POINTS_LAYER, setCrashTileUrl } from "./layers/CrashHeatmapLayer";
import {
  addClusterLayers, CLUSTER_COUNT_LAYER, CLUSTER_LAYER, CLUSTER_SOURCE, setClusterData, setHighlight,
} from "./layers/CrashClusterLayer";
import { addRiskLayer, RISK_LAYER, RISK_OUTLINE_LAYER, setRiskData } from "./layers/RiskChoroplethLayer";
import { addRoadClosureLayers, PERMIT_FILL_LAYER, PERMIT_LINE_LAYER, setPermitData } from "./layers/RoadClosureLayer";
import {
  AADT_LAYER, addTrafficLayers, HOTSPOT_LAYER, setAadtData, setHotspotData,
} from "./layers/TrafficAADTLayer";
import { addSegmentLayer, SEGMENT_LAYER, setSegmentData } from "./layers/SegmentRiskLayer";
import { MapPopup } from "./MapPopup";
import { useTheme } from "@/stores/useThemeStore";
import { applyMapTheme } from "@/theme/mapTheme";
import type { SegmentProps } from "@/types/api";

const LAYER_GROUPS: Record<LayerId, string[]> = {
  heatmap: [HEATMAP_LAYER],
  points: [POINTS_LAYER],
  clusters: [CLUSTER_LAYER, CLUSTER_COUNT_LAYER],
  risk: [RISK_LAYER, RISK_OUTLINE_LAYER],
  segments: [SEGMENT_LAYER],
  permits: [PERMIT_FILL_LAYER, PERMIT_LINE_LAYER],
  hotspots: [HOTSPOT_LAYER],
  aadt: [AADT_LAYER],
};
const FILTERABLE_LAYERS = [HEATMAP_LAYER, POINTS_LAYER];

const LAYER_NAMES: Partial<Record<LayerId, string>> = {
  segments: "riesgo por cuadra", risk: "riesgo por zona", permits: "obras en la vía",
  hotspots: "puntos calientes", aadt: "volumen de tráfico", clusters: "agrupaciones",
};

function initLayers(map: MLMap, tileUrl: string) {
  // Orden de apilado: rejilla de riesgo < obras < aforos < densidad < puntos < clusters
  const firstSymbol = map.getStyle().layers?.find((l) => l.type === "symbol")?.id;
  addRiskLayer(map, firstSymbol);
  addRoadClosureLayers(map);
  addTrafficLayers(map);
  addCrashTileLayers(map, tileUrl);
  addSegmentLayer(map);
  addClusterLayers(map);
}

const tileUrlOf = (s: { startDate: string | null; endDate: string | null; workzoneOnly: boolean }) =>
  crashService.tileUrl(s.startDate, s.endDate, s.workzoneOnly);

const pct = (v: number) => `${(v * 100).toLocaleString("es", { maximumFractionDigits: 0 })}%`;

export function MapContainer({ children }: { children?: ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { map, loaded, webGlSupported, contextLost, basemapFallback } = useMapLibre(containerRef, {
    style: BASEMAP_STYLE,
    center: CHICAGO_CENTER,
    zoom: 10.5,
    minZoom: 9,
    maxZoom: 18,
    maxBounds: CHICAGO_MAX_BOUNDS,
    attributionControl: { compact: true },
  });

  const layers = useMapStore((s) => s.layers);
  const setViewport = useMapStore((s) => s.setViewport);
  const { startDate, endDate, workzoneOnly } = useFilterStore(
    useShallow((s) => ({ startDate: s.startDate, endDate: s.endDate, workzoneOnly: s.workzoneOnly })),
  );
  // Selectores explícitos: el mapa no se vuelve a pintar por cambios de UI que no le afectan
  const {
    drawerOpen, selectedCrashId, selectedCoords, flyOnSelect, selectCrash, pickingPoint, setSimulatorPoint,
    simulatorPoint, selectSegment, selectedSegment, focusPoint,
  } = useUiStore(useShallow((s) => ({
    drawerOpen: s.drawerOpen, selectedCrashId: s.selectedCrashId, selectedCoords: s.selectedCoords,
    flyOnSelect: s.flyOnSelect, selectCrash: s.selectCrash, pickingPoint: s.pickingPoint,
    setSimulatorPoint: s.setSimulatorPoint, simulatorPoint: s.simulatorPoint, selectSegment: s.selectSegment,
    selectedSegment: s.selectedSegment, focusPoint: s.focusPoint,
  })));

  // --- Inicialización de capas y sincronización del viewport ---
  useEffect(() => {
    if (!map || !loaded) return;
    initLayers(map, tileUrlOf(useFilterStore.getState()));
    const sync = () => {
      const b = map.getBounds();
      const c = map.getCenter();
      setViewport([c.lng, c.lat], map.getZoom(), [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);
    };
    sync();
    map.on("moveend", sync);
    return () => {
      map.off("moveend", sync);
    };
  }, [map, loaded, setViewport]);

  // --- Piel visual: recolorea mapa base y capas de datos ---
  const theme = useTheme();
  useEffect(() => {
    if (map && loaded) applyMapTheme(map, theme);
  }, [map, loaded, theme]);

  // --- Fechas y «sólo zona de obra»: filtro en servidor sobre las teselas MVT ---
  useEffect(() => {
    if (map && loaded) setCrashTileUrl(map, tileUrlOf({ startDate, endDate, workzoneOnly }));
  }, [map, loaded, startDate, endDate, workzoneOnly]);

  // --- Hora y severidad: filtro en GPU (map.setFilter) ---
  useSpatialFilters(map, loaded, FILTERABLE_LAYERS);

  // --- Visibilidad de capas ---
  useEffect(() => {
    if (!map || !loaded) return;
    for (const [group, ids] of Object.entries(LAYER_GROUPS) as [LayerId, string[]][]) {
      for (const id of ids) {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", layers[group] ? "visible" : "none");
      }
    }
  }, [map, loaded, layers]);

  // --- Datos de capas opcionales (se piden sólo cuando la capa está activa) ---
  const filters = useQueryFilters();
  const viewport = useViewportCrashes(layers.clusters || drawerOpen);
  const risk = useQuery({
    queryKey: ["risk-grid"], queryFn: ({ signal }) => crashService.riskGrid(signal), enabled: layers.risk, staleTime: Infinity,
  });
  const permits = useQuery({
    queryKey: ["permits", filters.bounds, filters.endDate],
    queryFn: ({ signal }) => crashService.permits(filters.bounds ?? null, filters.endDate, signal),
    enabled: layers.permits && !!filters.bounds,
  });
  const hotspots = useQuery({
    queryKey: ["hotspots", filters],
    queryFn: ({ signal }) => crashService.hotspots(filters, signal),
    enabled: layers.hotspots && !!filters.bounds,
  });
  const { segments } = useTopSegments(layers.segments);
  const aadt = useQuery({
    queryKey: ["aadt"], queryFn: ({ signal }) => crashService.aadt(signal), enabled: layers.aadt, staleTime: Infinity,
  });

  useEffect(() => { if (map && loaded && viewport.data) setClusterData(map, viewport.data); }, [map, loaded, viewport.data]);
  useEffect(() => { if (map && loaded && risk.data) setRiskData(map, risk.data); }, [map, loaded, risk.data]);
  useEffect(() => { if (map && loaded && permits.data) setPermitData(map, permits.data); }, [map, loaded, permits.data]);
  useEffect(() => { if (map && loaded && hotspots.data) setHotspotData(map, hotspots.data); }, [map, loaded, hotspots.data]);
  useEffect(() => { if (map && loaded && aadt.data) setAadtData(map, aadt.data); }, [map, loaded, aadt.data]);
  useEffect(() => { if (map && loaded && segments.data) setSegmentData(map, segments.data); }, [map, loaded, segments.data]);

  // Enfoque solicitado desde paneles externos (p. ej. lista de tramos prioritarios)
  useEffect(() => {
    if (map && loaded && focusPoint) map.flyTo({ center: focusPoint, zoom: 16.5, speed: 1.4 });
  }, [map, loaded, focusPoint]);

  // --- Interacción: popup, expansión de clusters, selección para el simulador ---
  const pickingRef = useRef(pickingPoint);
  pickingRef.current = pickingPoint;
  useEffect(() => {
    if (!map || !loaded) return;
    const onPoint = (e: MapLayerMouseEvent) => {
      if (pickingRef.current) return;
      const f = e.features?.[0] as MapGeoJSONFeature | undefined;
      if (!f) return;
      const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];
      selectCrash(String(f.properties.id), coords, false);
    };
    const onCluster = async (e: MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f || pickingRef.current) return;
      const src = map.getSource(CLUSTER_SOURCE) as GeoJSONSource | undefined;
      try {
        // Si los datos del cluster cambiaron mientras tanto (el usuario movió el mapa), se ignora
        const zoom = await src?.getClusterExpansionZoom(f.properties.cluster_id as number);
        if (zoom !== undefined) map.easeTo({ center: (f.geometry as GeoJSON.Point).coordinates as [number, number], zoom });
      } catch {
        /* cluster ya no existe */
      }
    };
    const onMapClick = (e: MapLayerMouseEvent) => {
      if (pickingRef.current) setSimulatorPoint([Number(e.lngLat.lng.toFixed(6)), Number(e.lngLat.lat.toFixed(6))]);
    };
    const pointer = () => { map.getCanvas().style.cursor = "pointer"; };
    const reset = () => { map.getCanvas().style.cursor = pickingRef.current ? "crosshair" : ""; };
    const onSegment = (e: MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f || pickingRef.current) return;
      // La predicción explicada de la cuadra se muestra en el panel lateral
      const coordinates = (f.geometry as GeoJSON.Point).coordinates as [number, number];
      selectSegment({ ...(f.properties as SegmentProps), coordinates });
    };
    map.on("click", SEGMENT_LAYER, onSegment);
    map.on("click", POINTS_LAYER, onPoint);
    map.on("click", CLUSTER_LAYER, onCluster);
    map.on("click", onMapClick);
    for (const id of [POINTS_LAYER, CLUSTER_LAYER, SEGMENT_LAYER]) {
      map.on("mouseenter", id, pointer);
      map.on("mouseleave", id, reset);
    }
    return () => {
      map.off("click", SEGMENT_LAYER, onSegment);
      map.off("click", POINTS_LAYER, onPoint);
      map.off("click", CLUSTER_LAYER, onCluster);
      map.off("click", onMapClick);
      for (const id of [POINTS_LAYER, CLUSTER_LAYER, SEGMENT_LAYER]) {
        map.off("mouseenter", id, pointer);
        map.off("mouseleave", id, reset);
      }
    };
  }, [map, loaded, selectCrash, setSimulatorPoint, selectSegment]);

  useEffect(() => {
    if (map) map.getCanvas().style.cursor = pickingPoint ? "crosshair" : "";
  }, [map, pickingPoint]);

  // --- Predicción puntual al pasar el cursor por una cuadra (sin abrir el panel) ---
  useEffect(() => {
    if (!map || !loaded) return;
    const hover = new Popup({ closeButton: false, closeOnClick: false, offset: 10, className: "segment-hover", maxWidth: "240px" });
    // Un único contenido reutilizado: sólo se reescribe el texto al cambiar de cuadra
    const box = document.createElement("div");
    const title = document.createElement("p");
    title.className = "font-semibold text-slate-100";
    const body = document.createElement("p");
    body.className = "text-slate-300";
    const hint = document.createElement("p");
    hint.className = "text-slate-400";
    hint.textContent = "Clic para ver por qué";
    box.append(title, body, hint);
    hover.setDOMContent(box);
    let current: string | null = null;
    const onMove = (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties as SegmentProps | undefined;
      if (!p || pickingRef.current) return;
      if (p.segment_id !== current) {
        current = p.segment_id;
        title.textContent = p.segment_id;
        body.textContent = `${pct(Number(p.p_alto))} de probabilidad de riesgo Alto en 12 meses · prioridad #${Number(p.priority_rank).toLocaleString("es")}`;
      }
      hover.setLngLat(e.lngLat);
      if (!hover.isOpen()) hover.addTo(map);
    };
    const onLeave = () => {
      current = null;
      hover.remove();
    };
    map.on("mousemove", SEGMENT_LAYER, onMove);
    map.on("mouseleave", SEGMENT_LAYER, onLeave);
    return () => {
      map.off("mousemove", SEGMENT_LAYER, onMove);
      map.off("mouseleave", SEGMENT_LAYER, onLeave);
      hover.remove();
    };
  }, [map, loaded]);

  // --- Resaltado: una sola fuente de verdad (siniestro, cuadra, punto enfocado o del simulador) ---
  useEffect(() => {
    if (!map || !loaded) return;
    setHighlight(map, selectedCoords ?? selectedSegment?.coordinates ?? focusPoint ?? simulatorPoint);
    if (selectedCoords && flyOnSelect) map.flyTo({ center: selectedCoords, zoom: Math.max(map.getZoom(), 16), speed: 1.4 });
  }, [map, loaded, selectedCoords, flyOnSelect, simulatorPoint, selectedSegment, focusPoint]);

  const closePopup = useCallback(() => selectCrash(null), [selectCrash]);

  // Estado de las capas activas: cargando o con error (antes un fallo dejaba el mapa vacío sin aviso)
  const layerQueries: [LayerId, { isFetching: boolean; isError: boolean; refetch: () => unknown }][] = [
    ["segments", segments], ["risk", risk], ["permits", permits], ["hotspots", hotspots], ["aadt", aadt], ["clusters", viewport],
  ];
  const active = layerQueries.filter(([id]) => layers[id]);
  const fetching = active.some(([, q]) => q.isFetching);
  const failed = active.filter(([, q]) => q.isError);

  return (
    <MapProvider value={{ map, loaded }}>
      <div className="relative h-full w-full" data-tour="map">
        <div ref={containerRef} className="absolute inset-0" data-testid="map-canvas" role="region" aria-label="Mapa de riesgo vial de Chicago" />
        {!webGlSupported && (
          <div className="absolute inset-0 grid place-items-center bg-slate-950 p-6 text-center text-slate-300">
            Este navegador no soporta WebGL2. Active la aceleración por hardware para visualizar el mapa.
          </div>
        )}
        {webGlSupported && !loaded && (
          <div className="absolute inset-0 grid place-items-center text-xs text-slate-400" aria-live="polite">Cargando mapa…</div>
        )}
        <div className="pointer-events-none absolute left-1/2 top-3 z-10 flex -translate-x-1/2 flex-col items-center gap-1.5">
          {contextLost && (
            <p className="rounded bg-amber-500/90 px-3 py-1 text-xs text-slate-900">Contexto WebGL perdido. Recuperando…</p>
          )}
          {basemapFallback && (
            <p role="status" className="rounded bg-slate-900/95 px-3 py-1 text-xs text-amber-300 border border-amber-700/60" data-testid="basemap-fallback">
              Mapa base no disponible (sin conexión con CARTO): se muestran sólo los datos del proyecto.
            </p>
          )}
          {failed.length > 0 && (
            <p role="alert" className="pointer-events-auto flex items-center gap-2 rounded border border-amber-700/60 bg-slate-900/95 px-3 py-1 text-xs text-amber-300">
              No se pudo cargar: {failed.map(([id]) => LAYER_NAMES[id]).join(", ")}.
              <button onClick={() => failed.forEach(([, q]) => void q.refetch())} className="rounded border border-slate-700 px-1.5 text-slate-200 hover:bg-slate-800">
                Reintentar
              </button>
            </p>
          )}
        </div>
        {fetching && (
          <div className="absolute right-3 top-3 rounded-full border border-slate-700 bg-slate-900/90 px-3 py-1 text-xs text-cyan-300" aria-live="polite">
            Cargando datos…
          </div>
        )}
        {loaded && selectedCrashId && selectedCoords && (
          <MapPopup crashId={selectedCrashId} coordinates={selectedCoords} onClose={closePopup} />
        )}
        {loaded && children}
      </div>
    </MapProvider>
  );
}
