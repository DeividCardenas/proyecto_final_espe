import { useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { Popup } from "maplibre-gl";
import { useQuery } from "@tanstack/react-query";
import { useMapInstance } from "@/context/MapContext";
import { crashService } from "@/services/crashService";
import { SEVERITY_LABELS, severityClass } from "@/components/ui";

interface Props {
  crashId: string;
  coordinates: [number, number];
  onClose: () => void;
}

/** Tarjeta emergente con el detalle de un siniestro (React portal dentro de maplibregl.Popup). */
export function MapPopup({ crashId, coordinates, onClose }: Props) {
  const { map } = useMapInstance();
  const node = useMemo(() => document.createElement("div"), []);
  const { data, isLoading } = useQuery({ queryKey: ["crash", crashId], queryFn: () => crashService.detail(crashId) });

  useEffect(() => {
    if (!map) return;
    const popup = new Popup({ maxWidth: "320px", className: "crash-popup", closeOnClick: false })
      .setLngLat(coordinates)
      .setDOMContent(node)
      .addTo(map);
    popup.on("close", onClose);
    return () => {
      popup.off("close", onClose);
      popup.remove();
    };
  }, [map, node, coordinates, onClose]);

  return createPortal(
    <div className="text-slate-100 text-xs space-y-2 min-w-[240px]">
      {isLoading || !data ? (
        <p className="text-slate-400">Cargando detalle…</p>
      ) : (
        <>
          <div className="flex items-center justify-between gap-2">
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${severityClass(data.severity)}`}>
              {SEVERITY_LABELS[data.severity]}
            </span>
            <span className="text-slate-400">{data.date.replace("T", " ")}</span>
          </div>
          <p className="font-semibold text-sm leading-tight">{data.street || "Ubicación sin dirección"}</p>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1">
            <dt className="text-slate-400">Tipo</dt><dd>{data.crash_type ?? "—"}</dd>
            <dt className="text-slate-400">Causa</dt><dd className="truncate" title={data.cause ?? ""}>{data.cause ?? "—"}</dd>
            <dt className="text-slate-400">Lesionados</dt><dd>{data.injuries} {data.fatal > 0 && <b className="text-red-400">({data.fatal} fatal)</b>}</dd>
            <dt className="text-slate-400">Clima / luz</dt><dd>{data.weather ?? "—"} / {data.lighting ?? "—"}</dd>
            <dt className="text-slate-400">Velocidad</dt><dd>{data.speed ?? "—"} mph</dd>
            <dt className="text-slate-400">AADT</dt><dd>{data.aadt?.toLocaleString("es") ?? "—"}</dd>
            <dt className="text-slate-400">Obra CDOT</dt><dd>{data.workzone ? `Sí (${data.permit})` : "No"}</dd>
            <dt className="text-slate-400">Unidades</dt><dd>{data.vehicles.length} · {data.people.length} personas</dd>
          </dl>
        </>
      )}
    </div>,
    node,
  );
}
