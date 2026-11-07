import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setWorkerUrl } from "maplibre-gl";
// MapLibre v6 usa un Web Worker en módulo separado: Vite lo empaqueta como chunk propio
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import App from "./App";
// Sólo la fuente del tema por defecto (Clásico); las demás se cargan al elegir su tema
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-600.css";
import "./index.css";

setWorkerUrl(maplibreWorkerUrl);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
