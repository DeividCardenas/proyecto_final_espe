import { useCallback, useEffect, useRef, type ReactNode } from "react";
import { Popup, type GeoJSONSource, type MapGeoJSONFeature, type MapLayerMouseEvent, type Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useQuery } from "@tanstack/react-query";
import { MapProvider } from "@/context/MapContext";
import { BASEMAP_STYLE, useMapLibre } from "@/hooks/useMapLibre";
import { useSpatialFilters } from "@/hooks/useSpatialFilters";
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

/** Tarjeta DOM (sin innerHTML: evita inyección desde los datos) para un tramo. */
function segmentCard(p: Record<string, number | string>): HTMLElement {
  const el = document.createElement("div");
  el.className = "text-xs text-slate-100 space-y-1";
  const pct = (v: number | string) => (Number(v) * 100).toFixed(1) + "%";
  const rows: [string, string][] = [
    ["Prioridad", "#" + p.priority_rank + " (top " + pct(p.priority_pct) + ")"],
    ["P(riesgo Alto)", pct(p.p_alto)],
    ["Siniestros 12 meses", String(p.crashes)],
    ["Graves / fatales", p.severe_crashes + " / " + p.fatalities],
    ["Peatones / ciclistas", p.ped_crashes + " / " + p.bike_crashes],
  ];
  const title = document.createElement("p");
  title.className = "font-semibold text-sm";
  title.textContent = String(p.segment_id);
  el.appendChild(title);
  for (const [k, v] of rows) {
    const r = document.createElement("p");
    const b = document.createElement("span");
    b.className = "text-slate-400";
    b.textContent = k + ": ";
    r.append(b, document.createTextNode(v));
    el.appendChild(r);
  }
  return el;
}

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

export function MapContainer({ children }: { children?: ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { map, loaded, webGlSupported, contextLost } = useMapLibre(containerRef, {
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
  const startDate = useFilterStore((s) => s.startDate);
  const endDate = useFilterStore((s) => s.endDate);
  const drawerOpen = useUiStore((s) => s.drawerOpen);
  const { selectedCrashId, selectedCoords, flyOnSelect, selectCrash, pickingPoint, setSimulatorPoint, simulatorPoint } =
    useUiStore();

  // --- Inicialización de capas y sincronización del viewport ---
  useEffect(() => {
    if (!map || !loaded) return;
    initLayers(map, crashService.tileUrl(useFilterStore.getState().startDate, useFilterStore.getState().endDate));
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

  // --- Rango de fechas: filtro en servidor sobre las teselas MVT ---
  useEffect(() => {
    if (map && loaded) setCrashTileUrl(map, crashService.tileUrl(startDate, endDate));
  }, [map, loaded, startDate, endDate]);

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
  const risk = useQuery({ queryKey: ["risk-grid"], queryFn: crashService.riskGrid, enabled: layers.risk, staleTime: Infinity });
  const permits = useQuery({
    queryKey: ["permits", filters.bounds, filters.endDate],
    queryFn: () => crashService.permits(filters.bounds ?? null, filters.endDate),
    enabled: layers.permits && !!filters.bounds,
  });
  const hotspots = useQuery({ queryKey: ["hotspots", filters], queryFn: () => crashService.hotspots(filters), enabled: layers.hotspots && !!filters.bounds });
  const segments = useQuery({ queryKey: ["segments"], queryFn: () => crashService.segments(), enabled: layers.segments, staleTime: Infinity });
  const aadt = useQuery({ queryKey: ["aadt"], queryFn: crashService.aadt, enabled: layers.aadt, staleTime: Infinity });

  useEffect(() => { if (map && loaded && viewport.data) setClusterData(map, viewport.data); }, [map, loaded, viewport.data]);
  useEffect(() => { if (map && loaded && risk.data) setRiskData(map, risk.data); }, [map, loaded, risk.data]);
  useEffect(() => { if (map && loaded && permits.data) setPermitData(map, permits.data); }, [map, loaded, permits.data]);
  useEffect(() => { if (map && loaded && hotspots.data) setHotspotData(map, hotspots.data); }, [map, loaded, hotspots.data]);
  useEffect(() => { if (map && loaded && aadt.data) setAadtData(map, aadt.data); }, [map, loaded, aadt.data]);
  useEffect(() => { if (map && loaded && segments.data) setSegmentData(map, segments.data); }, [map, loaded, segments.data]);

  // Enfoque solicitado desde paneles externos (p. ej. lista de tramos prioritarios)
  const focusPoint = useUiStore((s) => s.focusPoint);
  useEffect(() => {
    if (map && loaded && focusPoint) {
      map.flyTo({ center: focusPoint, zoom: 16.5, speed: 1.4 });
      setHighlight(map, focusPoint);
    }
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
      const src = map.getSource(CLUSTER_SOURCE) as GeoJSONSource;
      const zoom = await src.getClusterExpansionZoom(f.properties.cluster_id as number);
      map.easeTo({ center: (f.geometry as GeoJSON.Point).coordinates as [number, number], zoom });
    };
    const onMapClick = (e: MapLayerMouseEvent) => {
      if (pickingRef.current) setSimulatorPoint([Number(e.lngLat.lng.toFixed(6)), Number(e.lngLat.lat.toFixed(6))]);
    };
    const pointer = () => { map.getCanvas().style.cursor = "pointer"; };
    const reset = () => { map.getCanvas().style.cursor = pickingRef.current ? "crosshair" : ""; };
    const onSegment = (e: MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f || pickingRef.current) return;
      new Popup({ className: "crash-popup", maxWidth: "280px" })
        .setLngLat(e.lngLat)
        .setDOMContent(segmentCard(f.properties as Record<string, number | string>))
        .addTo(map);
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
  }, [map, loaded, selectCrash, setSimulatorPoint]);

  useEffect(() => {
    if (map) map.getCanvas().style.cursor = pickingPoint ? "crosshair" : "";
  }, [map, pickingPoint]);

  // --- Selección bidireccional tabla <-> mapa ---
  useEffect(() => {
    if (!map || !loaded) return;
    setHighlight(map, selectedCoords ?? simulatorPoint);
    if (selectedCoords && flyOnSelect) map.flyTo({ center: selectedCoords, zoom: Math.max(map.getZoom(), 16), speed: 1.4 });
  }, [map, loaded, selectedCoords, flyOnSelect, simulatorPoint]);

  const closePopup = useCallback(() => selectCrash(null), [selectCrash]);

  return (
    <MapProvider value={{ map, loaded }}>
      <div className="relative h-full w-full">
        <div ref={containerRef} className="absolute inset-0" data-testid="map-canvas" />
        {!webGlSupported && (
          <div className="absolute inset-0 grid place-items-center bg-slate-950 text-slate-300 p-6 text-center">
            Este navegador no soporta WebGL2. Active la aceleración por hardware para visualizar el mapa.
          </div>
        )}
        {contextLost && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 rounded bg-amber-500/90 px-3 py-1 text-xs text-slate-900">
            Contexto WebGL perdido. Recuperando…
          </div>
        )}
        {(viewport.isFetching || permits.isFetching || hotspots.isFetching || risk.isFetching) && (
          <div className="absolute top-3 right-3 rounded-full bg-slate-900/90 px-3 py-1 text-xs text-cyan-300 border border-slate-700">
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
