import { Crosshair, Minus, Plus, Rotate3d } from "lucide-react";
import { useMapInstance } from "@/context/MapContext";
import { CHICAGO_CENTER } from "@/stores/useMapStore";

export function MapControls() {
  const { map } = useMapInstance();
  const btn = "grid h-9 w-9 place-items-center rounded-lg border border-slate-700 bg-slate-900/90 text-slate-200 hover:bg-slate-800";
  return (
    <div className="absolute right-3 top-14 flex flex-col gap-1.5">
      <button className={btn} aria-label="Acercar" onClick={() => map?.zoomIn()}><Plus size={16} /></button>
      <button className={btn} aria-label="Alejar" onClick={() => map?.zoomOut()}><Minus size={16} /></button>
      <button className={btn} aria-label="Inclinar" title="Alternar vista 3D"
        onClick={() => map?.easeTo({ pitch: map.getPitch() > 0 ? 0 : 50 })}><Rotate3d size={16} /></button>
      <button className={btn} aria-label="Centrar en Chicago" title="Volver a Chicago"
        onClick={() => map?.flyTo({ center: CHICAGO_CENTER, zoom: 10.5, pitch: 0, bearing: 0 })}><Crosshair size={16} /></button>
    </div>
  );
}
