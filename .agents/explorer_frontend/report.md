# Deep Technical Architecture Analysis & Best-Practice Assessment: Frontend & Geospatial Visualization Stack

**Project**: Big Data & Predictive Geospatial Modeling of Urban Mobility and Road Risks (City of Chicago)  
**Document Author**: Explorer Frontend Agent (`explorer_frontend`)  
**Target Environment**: React 18 / Vite / TypeScript / MapLibre GL JS v4 / TailwindCSS / Docker Nginx  
**Date**: September 2026  

---

## 1. Executive Summary & Technical Context

The frontend platform for the **Chicago Traffic Safety and Predictive Road Risk System** must bridge two historically conflicting domains:
1. **Massive Geospatial Big Data**: Visualizing and filtering over **850,000 traffic crash records**, **1.7 million involved vehicles**, **2 million involved individuals**, thousands of active **CDOT road closures**, and citywide **AADT traffic volume stations**.
2. **Fluid, Low-Latency Web UX**: Delivering 60 frames-per-second (FPS) pan/zoom interactions, instant multi-attribute spatial filtering (<100ms response), predictive ML risk heatmaps, virtualized tabular inspection, and analytical charts without browser freezing or memory leaks.

While preliminary project documentation initially cited *Leaflet.js*, our rigorous architecture analysis reveals that **DOM/Canvas-based libraries like Leaflet are fundamentally unviable** for datasets exceeding 2,000 to 5,000 features. Instead, the production stack must standardize on **MapLibre GL JS v4 (WebGL2)** integrated into a **React 18.3 + TypeScript** single-page application (SPA), built with **Vite**, orchestrated via **Zustand** (UI/map state) and **TanStack Query v5** (server state), and containerized using a **multi-stage Docker build serving via Nginx Alpine with an embedded reverse proxy**.

This report delivers a deep technical assessment of risks, architectural blueprints, dependency rubrics, container configurations, and an actionable, phased implementation roadmap.

---

## 2. Technical Viability & Risk Analysis

```
+---------------------------------------------------------------------------------------------------+
|                                  RISK MATRIX: FRONTEND & GIS STACK                               |
+----------------------------------------------------+----------+------------+---------------------+
| Risk Domain                                        | Severity | Likelihood | Architectural Impact|
+----------------------------------------------------+----------+------------+---------------------+
| 1. WebGL Context Leaks & Canvas Loss               | CRITICAL | HIGH       | Total UI Blank/Crash|
| 2. GeoJSON Memory Overhead & GC Freezes (>10k pts) | CRITICAL | HIGH       | Browser Tab Hang    |
| 3. React Re-render Thrashing with Map State        | HIGH     | HIGH       | Frame Drops (<15fps)|
| 4. Tile Pipeline Bottlenecks (MVT vs GeoJSON)      | HIGH     | MEDIUM     | Network Saturation  |
| 5. React 19 Peer Dependency Collisions             | HIGH     | HIGH       | Broken npm install  |
| 6. CORS & Container Network Routing Nuances        | MEDIUM   | MEDIUM     | Blocked API Requests|
+----------------------------------------------------+----------+------------+---------------------+
```

### Risk 1: WebGL Context Limits & Lifecycle Management in React
* **The Mechanism**: Modern browsers (Blink/Chromium, WebKit, Gecko) impose a strict hard limit of **8 to 16 concurrent WebGL contexts per process/origin**. When a React component tree mounts, unmounts, or hot-reloads a component containing a MapLibre instance without explicit destruction, the browser keeps the GPU context alive until garbage collection occurs. If users navigate between views, toggle tabs, or trigger HMR during development, the error `Error: Too many active WebGL contexts. Oldest context will be lost` is thrown, turning maps into black, unresponsive rectangles.
* **Mitigation Strategy**:
  1. **Deterministic Teardown**: The MapLibre map instance must never be instantiated directly inside an uncontrolled component body. It must be managed inside a `useEffect` hook whose cleanup function deterministically invokes `map.remove()`.
  2. **Singleton / Ref-Preservation Pattern**: Store the active map instance in a React `useRef` or a dedicated Map Context provider rather than React component state. This ensures that parent component re-renders do not trigger map re-instantiation.
  3. **Canvas Loss Handler**: Attach event listeners for `webglcontextlost` and `webglcontextrestored`:
     ```typescript
     canvas.addEventListener('webglcontextlost', (event) => {
       event.preventDefault();
       console.warn('[MapLibre] WebGL Context Lost. Pausing rendering pipeline.');
     }, false);
     canvas.addEventListener('webglcontextrestored', () => {
       console.info('[MapLibre] WebGL Context Restored. Reloading sources & layers.');
       map.triggerRepaint();
     }, false);
     ```

### Risk 2: Client-side GeoJSON Payload & Browser Memory Thrashing
* **The Mechanism**: A GeoJSON `FeatureCollection` of 100,000 crashes consumes ~50MB to 75MB in uncompressed JSON text. Once parsed by V8 into JavaScript objects, its memory footprint expands to **350MB - 500MB on the JavaScript heap**. Passing this volume through React state triggers deep object traversals, massive memory churn, and frequent Garbage Collection (GC) pauses lasting 800ms to 2500ms, causing noticeable UI stutter. Furthermore, calling `map.getSource('crashes').setData(geojson)` transfers data over a Web Worker message channel, which serializes and deserializes the entire payload.
* **Threshold & Tiering Matrix**:
  - **Tier 1 (0 – 5,000 points / polygons)**: Direct client-side GeoJSON via `map.getSource().setData()`. Zero noticeable overhead; sub-millisecond shader dispatch.
  - **Tier 2 (5,000 – 30,000 points)**: GeoJSON with **client-side clustering** via MapLibre's built-in Supercluster worker (`cluster: true, clusterRadius: 50, clusterMaxZoom: 14`). Only visible clusters and unclustered points are processed by the render loop.
  - **Tier 3 (> 30,000 to 850,000+ points / complex road networks)**: **Client-side GeoJSON is prohibited**. The architecture must adopt one of two vector tile approaches:
    1. **Dynamic Vector Tiles (MVT)** generated server-side via PostGIS `ST_AsMVT()` served by FastAPI or `pg_tileserv` at `/api/v1/tiles/{z}/{x}/{y}.pbf`. Tiles are transferred in lightweight Protocol Buffers (20KB - 120KB per tile) and rendered on-demand directly by the GPU.
    2. **Dynamic Bounding Box (BBOX) Queries**: When users zoom into an intersection or corridor, FastAPI returns only features inside the current map extent (`ST_Intersects(geom, ST_MakeEnvelope(...))`), capped at a maximum of 5,000 records.

### Risk 3: Reactivity Bottlenecks with High-Frequency Filter Updates
* **The Mechanism**: The dashboard features high-frequency controls: an hour-of-day slider (0–23h), date range selectors, and severity checkboxes. If each slider movement dispatches an API request or triggers a full `setData()` reload, the network and WebGL worker thread queue up hundreds of stale tasks, locking the browser UI.
* **Mitigation Strategy (Decoupled Filter Architecture)**:
  - **GPU-Level Immediate Filtering (0ms Latency)**: For already-loaded vector data (or vector tiles with feature properties), use **MapLibre GL Expressions** via `map.setFilter(layerId, filterExpression)`. This adjusts GPU shader uniforms directly in WebGL without modifying source data or touching the JS heap.
    ```typescript
    // Example: GPU-accelerated real-time filter executed at 60 FPS
    map.setFilter('crashes-circle', [
      'all',
      ['>=', ['get', 'crash_hour'], currentHourRange[0]],
      ['<=', ['get', 'crash_hour'], currentHourRange[1]],
      ['in', ['get', 'crash_type'], ['literal', selectedTypes]]
    ]);
    ```
  - **Debounced Server Queries (250ms Debounce)**: For heavy backend analytics aggregations (KPI cards, charts, tabular data), debounce user input by 250ms using TanStack Query, canceling in-flight HTTP requests via `AbortController`.

### Risk 4: MapLibre GL JS (v3 vs v4) & Wrapper Assessment
* **MapLibre GL JS v4 vs v3**:
  - **v4 Transition**: Released in 2024, MapLibre GL JS v4 migrated completely to **WebGL2**, dropping legacy WebGL1 fallbacks and obsolete browser polyfills. It introduces substantial performance enhancements for vector tile decoding, better memory deallocation, support for modern 3D terrain/globe projections, and streamlined web workers.
  - **Decision**: Standardize on **MapLibre GL JS `v4.7.1`**.
* **Integration Strategy: `react-map-gl/maplibre` vs Native Hook Architecture**:
  - `react-map-gl` (v7.1+) provides declarative React wrappers (`<Map><Source><Layer /></Source></Map>`). However, our evaluation identifies significant drawbacks for high-performance GIS:
    1. Prop reconciliation overhead: Imperative MapLibre methods (`setFilter`, `setPaintProperty`) are mediated by React's diffing engine, creating a layer of lag.
    2. Version locking & peer dependency frictions during ecosystem updates.
    3. Friction when integrating custom deck.gl layers, third-party tile protocols (e.g. `pmtiles`), or custom WebGL canvas layers.
  - **Recommended Approach**: **Native MapLibre with Custom Hook / Ref Architecture**. A custom `<MapView />` component maintains a direct `maplibre-gl.Map` instance ref. A lightweight Zustand store exposes map control actions (`flyTo`, `setFilter`, `toggleLayer`) to all UI controls cleanly, achieving superior performance, full lifecycle control, and zero wrapper baggage.

### Risk 5: React 18.3 vs React 19 Compatibility Assessment
* **The Issue**: React 19 introduces breaking internal changes to ref callbacks, context mechanics, and library internals. In the current npm ecosystem (Q3/Q4 2026), several core geospatial, charting, and headless UI packages (including specific Radix primitives, Recharts v2.x, and geospatial extensions) have peer dependency definitions pinned to `"react": "^18.0.0"`. Attempting to install React 19 leads to `ERESOLVE` peer dependency failures, requiring `--legacy-peer-deps` or `--force`, which risks silent runtime errors.
* **Architectural Decision**: Pin production to **React `18.3.1`** and **React-DOM `18.3.1`**. This provides complete stability, full Concurrent Mode features (`useTransition`, `useDeferredValue`), seamless compatibility with TanStack Query v5, Zustand v5, and Radix UI primitives. A clear upgrade path to React 19 is defined once library maintainers publish universal React 19 stable peer definitions.

---

## 3. UI/UX Architecture & Responsive Layout Blueprint

```
+----------------------------------------------------------------------------------------------------+
|                                    APPLICATION LAYOUT BLUEPRINT                                   |
+----------------------------------------------------------------------------------------------------+
| [HEADER] Brand Logo | Title: Chicago Traffic Risk Analytics | Global Search | Presets | Dark/Light |
+----------------------------------------------------------------------------------------------------+
| [LEFT SIDEBAR]             | [MAP CANVAS: Full-Viewport WebGL2 MapLibre]     | [RIGHT ANALYTICS]   |
| (Collapsible: 360px -> 0)  | - Base Layers (Dark Matter, Positron, Satellite)| (Slide-out / Dock)  |
|                            | - Heatmap: Crash Density                        | - Total Crashes     |
| [Tab 1: Filters]           | - Clusters: High-density collisions             | - Fatalities / Inj. |
|  * Date Range Picker       | - Road Segments: ML Predicted Risk (Choropleth) | - Risk Score Avg    |
|  * Hour Slider (0-23h)     | - CDOT Road Closures (Buffer & Lines)           | - Hourly Trend Chart|
|  * Severity Checkboxes     | - Traffic AADT Counters (Proportional circles)  | - Weather Bar Chart |
|  * Weather / Surface       |                                                 | - AADT vs Collisions|
|                            | [FLOATING CONTROLS: Top-Right]                  |                     |
| [Tab 2: Layers & Legend]   |  * Zoom In/Out | Reset Bearing | Chicago Extent |                     |
|  * Opacity Sliders         |  * Basemap Switcher | Layer Quick-Toggle        |                     |
|  * Color Ramps & Scales    |                                                 |                     |
|                            | [BOTTOM DRAWER: Tabular Data Inspection]        |                     |
| [Tab 3: ML Simulator]      | (Collapsible: 48px Header <-> 320px Virtualized Data Table)           |
|  * Road Segment Inputs     | - TanStack Virtual Table: 850k records scrollable at 60 FPS           |
|  * Predict Risk on-the-fly | - Columns: Date, Street, Speed, Severity, Weather, Predicted Risk     |
|  * Real-time Score Gauge   | - Actions: Export CSV | Export GeoJSON | Zoom to Selected Feature     |
+----------------------------------------------------------------------------------------------------+
```

### Component Hierarchy (Atomic Design Structure)

```
src/
├── app/
│   ├── App.tsx                     # Root application container & QueryClientProvider
│   ├── main.tsx                    # Vite entry point
│   └── routes.tsx                  # Client router (Dashboard, Analytics, Scenario Simulator)
├── components/
│   ├── common/                     # Design system primitives (Button, Slider, Modal, Tooltip)
│   ├── layout/
│   │   ├── Header.tsx              # Top navigation bar with status indicators & presets
│   │   ├── Sidebar.tsx             # Collapsible multi-tab filter & layer configuration panel
│   │   ├── AnalyticsPanel.tsx      # Slide-over analytics drawer with KPI cards & Recharts
│   │   └── DataDrawer.tsx          # Resizable bottom drawer housing the virtualized data table
│   ├── map/
│   │   ├── MapContainer.tsx        # MapLibre GL WebGL2 viewport container & lifecycle hook
│   │   ├── MapControls.tsx         # Floating zoom, pitch, reset Chicago bounds, basemap selector
│   │   ├── MapLegend.tsx           # Dynamic choropleth color scale and layer opacity toggles
│   │   ├── MapPopup.tsx            # Feature detail popup on hover/click (HTML overlay)
│   │   └── layers/
│   │       ├── CrashHeatmapLayer.ts      # WebGL density heatmap layer
│   │       ├── CrashClusterLayer.ts      # Supercluster circle & count symbol layers
│   │       ├── RiskChoroplethLayer.ts    # ML road segment risk vector layer with color ramps
│   │       ├── RoadClosureLayer.ts       # CDOT construction work zones & buffer areas
│   │       └── TrafficAADTLayer.ts       # Proportional circle markers for traffic volume
│   ├── analytics/
│   │   ├── KpiSummaryCards.tsx     # Total crashes, fatalities, high-risk tramos, active permits
│   │   ├── HourlyDistribution.tsx  # Temporal crash distribution bar chart
│   │   ├── WeatherImpactChart.tsx  # Donut chart showing surface/lighting condition correlation
│   │   └── RiskCorrelationPlot.tsx # Scatter plot: AADT traffic volume vs accident severity
│   └── table/
│       ├── VirtualCrashTable.tsx   # TanStack Table + Virtual scrolling for 10,000+ records
│       └── TableExportBar.tsx      # CSV and GeoJSON client-side export triggers
├── hooks/
│   ├── useMapLibre.ts              # Core hook managing MapLibre GL instance, events & lifecycle
│   ├── useSpatialFilters.ts        # Coordinates filter state with MapLibre setFilter expressions
│   └── useDebounce.ts              # Input debouncer for server query dispatching
├── stores/
│   ├── useMapStore.ts              # Zustand store for map viewport, active layers, basemap
│   ├── useFilterStore.ts           # Zustand store for date, hour, severity, weather filters
│   └── useUiStore.ts               # Zustand store for sidebar, bottom drawer, panel visibility
├── services/
│   ├── api.ts                      # Axios / Fetch client with baseURL & error interceptors
│   ├── crashService.ts             # REST endpoints for crashes, BBOX queries, aggregations
│   ├── predictionService.ts        # FastAPI ML model scoring & scenario simulation endpoint
│   └── tileService.ts              # MVT endpoint definitions & metadata
└── types/
    ├── geojson.d.ts                # TypeScript interfaces for Chicago crashes, roads, AADT
    └── api.d.ts                    # Backend request/response DTO schemas
```

### Responsive Design & Breakpoint Strategy

1. **Desktop Display (≥ 1280px / Full HD & 2K)**:
   - Left Sidebar remains docked (380px fixed width).
   - Map Canvas spans remaining viewport.
   - Analytics Panel can be docked side-by-side or toggled as a semi-transparent floating glassmorphic card.
   - Bottom Data Drawer rests at 44px minimized height, expandable to 380px with full virtual scroll.
2. **Tablet & Laptop (768px – 1279px)**:
   - Left Sidebar collapses to a vertical icon navigation rail (60px). Clicking an icon pops out a floating drawer.
   - Map Canvas maintains primary focus.
   - Analytics Panel slides out as a modal drawer over the right half of the screen.
3. **Mobile Display (< 768px)**:
   - Full-bleed map view.
   - Bottom navigation tab bar (Map / Filters / Metrics / Data).
   - Tapping "Filters" opens a full-screen mobile bottom sheet (using Radix Dialog/Drawer).
   - Floating map controls repositioned to the bottom-right above the navigation bar.

---

## 4. Complete package.json Specification & Dependency Matrix

### Production `package.json`

```json
{
  "name": "chicago-traffic-risk-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "maplibre-gl": "4.7.1",
    "zustand": "5.0.0",
    "@tanstack/react-query": "5.56.2",
    "@tanstack/react-table": "8.20.5",
    "@tanstack/react-virtual": "3.10.8",
    "clsx": "2.1.1",
    "tailwind-merge": "2.5.2",
    "lucide-react": "0.446.0",
    "@radix-ui/react-slider": "1.2.0",
    "@radix-ui/react-tabs": "1.1.0",
    "@radix-ui/react-dialog": "1.1.1",
    "@radix-ui/react-popover": "1.1.1",
    "@radix-ui/react-tooltip": "1.1.2",
    "@radix-ui/react-dropdown-menu": "2.1.1",
    "@radix-ui/react-checkbox": "1.1.1",
    "recharts": "2.12.7",
    "axios": "1.7.7",
    "date-fns": "3.6.0"
  },
  "devDependencies": {
    "@types/react": "18.3.10",
    "@types/react-dom": "18.3.0",
    "@types/geojson": "7946.0.14",
    "@types/node": "22.5.5",
    "@vitejs/plugin-react": "4.3.1",
    "typescript": "5.6.2",
    "vite": "5.4.6",
    "vite-plugin-compression": "0.5.1",
    "tailwindcss": "3.4.11",
    "postcss": "8.4.47",
    "autoprefixer": "10.4.20",
    "eslint": "8.57.1",
    "eslint-plugin-react-hooks": "4.6.2",
    "eslint-plugin-react-refresh": "0.4.12"
  }
}
```

### Dependency Compatibility Rubric & Peer Conflict Assessment

| Package | Version | Compatibility Assessment & Peer Conflict Audit |
|---|---|---|
| `react` / `react-dom` | `18.3.1` | **Gold Standard Stability**. Eliminates peer dependency collisions across Radix UI and Recharts. Full support for concurrent rendering. |
| `maplibre-gl` | `4.7.1` | **WebGL2 Core Engine**. Native ES modules, zero React peer dependencies. Bundles high-performance Supercluster and GeoJSON-VT workers. |
| `zustand` | `5.0.0` | Ultra-lightweight (~1.2KB). Zero boilerplate, clean selector subscriptions, works flawlessly outside React render loops. |
| `@tanstack/react-query` | `5.56.2` | Universal server-state management. Built-in query cancellation via `AbortSignal`, garbage collection, and stale-time caching. |
| `@tanstack/react-table` + `@tanstack/react-virtual` | `8.20.5` / `3.10.8` | Headless virtualization pairing. Handles 50,000+ in-memory records with only ~30 DOM nodes rendered in the viewport. |
| `recharts` | `2.12.7` | Standard SVG/declarative charting. Fully verified against React 18.3.1. |
| `@radix-ui/*` primitives | `1.x` | Accessible, unstyled UI primitives. Zero styling lock-in, fully styled with Tailwind utility classes. |
| `tailwindcss` | `3.4.11` | Battle-tested utility framework. JIT compiler ensures production CSS output remains under 25KB. |

### Vite Bundle Splitting Configuration (`vite.config.ts`)

To avoid monolithic bundle sizes and ensure sub-second initial paint times, Vite must split vendor chunks logically:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import compression from 'vite-plugin-compression';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    // Pre-compress assets with Gzip and Brotli for Nginx static serving
    compression({ algorithm: 'gzip', ext: '.gz' }),
    compression({ algorithm: 'brotliCompress', ext: '.br' })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    target: 'es2022',
    sourcemap: false,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'zustand'],
          'vendor-maplibre': ['maplibre-gl'],
          'vendor-tanstack': ['@tanstack/react-query', '@tanstack/react-table', '@tanstack/react-virtual'],
          'vendor-charts': ['recharts'],
          'vendor-radix': [
            '@radix-ui/react-slider',
            '@radix-ui/react-dialog',
            '@radix-ui/react-tabs',
            '@radix-ui/react-popover',
            '@radix-ui/react-tooltip'
          ]
        }
      }
    }
  }
});
```

---

## 5. Core Geospatial & State Integration Architecture

### The Custom `useMapLibre` Lifecycle Hook Pattern

Rather than wrestling with third-party wrappers, the application encapsulates MapLibre GL JS within a robust custom hook that guarantees WebGL context disposal and exposes the map instance to Zustand:

```typescript
// src/hooks/useMapLibre.ts
import { useEffect, useRef } from 'react';
import maplibregl, { Map as MapLibreMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMapStore } from '@/stores/useMapStore';

interface UseMapLibreOptions {
  containerId: string;
  initialCenter?: [number, number]; // Chicago: [-87.6298, 41.8781]
  initialZoom?: number;
  styleUrl?: string;
}

export function useMapLibre({
  containerId,
  initialCenter = [-87.6298, 41.8781],
  initialZoom = 11,
  styleUrl = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
}: UseMapLibreOptions) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const setMapInstance = useMapStore((s) => s.setMapInstance);
  const clearMapInstance = useMapStore((s) => s.clearMapInstance);

  useEffect(() => {
    const container = document.getElementById(containerId);
    if (!container) return;

    const map = new maplibregl.Map({
      container,
      style: styleUrl,
      center: initialCenter,
      zoom: initialZoom,
      pitch: 35,
      bearing: 0,
      maxBounds: [
        [-88.1000, 41.6000], // Southwest Chicago bounds
        [-87.4000, 42.1000]  // Northeast Chicago bounds
      ],
      attributionControl: true
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

    map.on('load', () => {
      mapRef.current = map;
      setMapInstance(map);
    });

    // Cleanup: Mandatory WebGL context destruction
    return () => {
      clearMapInstance();
      map.remove();
      mapRef.current = null;
    };
  }, [containerId]);

  return { mapRef };
}
```

### High-Performance WebGL Layer Styling & Expressions

To display **ML Predicted Risk** alongside **Crash Clusters** and **CDOT Road Closures**, the following layer styles leverage MapLibre's hardware-accelerated expression engine:

```typescript
// src/components/map/layers/RiskChoroplethLayer.ts
import { Map as MapLibreMap } from 'maplibre-gl';

export function setupRoadRiskLayer(map: MapLibreMap, sourceId: string) {
  // Road segments line layer styled by ML Risk Score (0.0 to 1.0)
  map.addLayer({
    id: 'road-risk-segments',
    type: 'line',
    source: sourceId,
    'source-layer': 'road_segments', // If using MVT
    layout: {
      'line-join': 'round',
      'line-cap': 'round'
    },
    paint: {
      'line-width': [
        'interpolate', ['linear'], ['zoom'],
        10, 1.5,
        14, 3.5,
        18, 7.0
      ],
      'line-color': [
        'interpolate', ['linear'], ['get', 'predicted_risk_score'],
        0.00, '#10b981', // Low Risk: Emerald
        0.35, '#eab308', // Moderate Risk: Yellow
        0.65, '#f97316', // High Risk: Orange
        0.85, '#ef4444'  // Critical Risk: Crimson Red
      ],
      'line-opacity': 0.85
    }
  });

  // Highlight outline on feature hover
  map.addLayer({
    id: 'road-risk-highlight',
    type: 'line',
    source: sourceId,
    'source-layer': 'road_segments',
    paint: {
      'line-width': 6,
      'line-color': '#38bdf8', // Neon Sky Blue
      'line-opacity': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        1.0,
        0.0
      ]
    }
  });
}
```

---

## 6. Docker Containerization & Nginx Reverse Proxy Architecture

### Multi-Stage Production Dockerfile

The frontend build utilizes a **two-stage build**:
1. **Builder Stage (`node:20-alpine`)**: Installs exact locked dependencies via `npm ci`, compiles TypeScript, and runs Vite build with tree-shaking and pre-compression.
2. **Runtime Stage (`nginx:1.27-alpine`)**: Serves static artifacts with minimal footprint (<30MB image size), fortified security headers, and reverse proxying to FastAPI.

```dockerfile
# ==========================================
# Stage 1: Build & Assets Compilation
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Optimize build caching: copy package manifests first
COPY package.json package-lock.json ./

# Clean installation of locked dependencies
RUN npm ci --no-audit --prefer-offline

# Copy application source code
COPY . .

# Run type checks and production bundle creation
RUN npm run build

# ==========================================
# Stage 2: High-Performance Nginx Serving
# ==========================================
FROM nginx:1.27-alpine AS production

# Remove default nginx static web page
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA production assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom optimized Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Add healthcheck to verify container availability
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Production `nginx.conf` Specification

```nginx
# /etc/nginx/conf.d/default.conf

# Upstream definition for backend FastAPI service in Docker network
upstream backend_api {
    server backend:8000 max_fails=3 fail_timeout=10s;
    keepalive 32;
}

server {
    listen 80;
    server_name localhost;
    charset utf-8;

    # Maximum client payload size (useful for file uploads/filtering payloads)
    client_max_body_size 10M;

    # Root static directory
    root /usr/share/nginx/html;
    index index.html;

    # -------------------------------------------------------------
    # Gzip Compression for JSON, GeoJSON, MVT, SVG, and Assets
    # -------------------------------------------------------------
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/geo+json
        application/x-protobuf
        application/vnd.mapbox-vector-tile
        application/javascript
        application/x-javascript
        image/svg+xml;

    # -------------------------------------------------------------
    # Security Headers & Content Security Policy (CSP)
    # -------------------------------------------------------------
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # CSP specifically calibrated for MapLibre Web Workers & Tile CDNs
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; worker-src 'self' blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob: https://*.cartocdn.com https://*.openstreetmap.org https://data.cityofchicago.org; connect-src 'self' http://localhost:8000 http://backend:8000 https://*.cartocdn.com https://data.cityofchicago.org blob:;" always;

    # -------------------------------------------------------------
    # Static Assets Long-Term Caching
    # -------------------------------------------------------------
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
        access_log off;
        try_files $uri =404;
    }

    # -------------------------------------------------------------
    # Healthcheck Probe
    # -------------------------------------------------------------
    location /health {
        access_log off;
        return 200 '{"status":"UP","service":"frontend-web"}';
        add_header Content-Type application/json;
    }

    # -------------------------------------------------------------
    # Reverse Proxy to FastAPI Backend (Eliminates CORS entirely)
    # -------------------------------------------------------------
    location /api/ {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for heavy geospatial spatial joins / ML inference
        proxy_connect_timeout 15s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # -------------------------------------------------------------
    # Single Page Application (SPA) HTML5 Routing Fallback
    # -------------------------------------------------------------
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
```

---

## 7. Phased Frontend Implementation Roadmap

```
+----------------------------------------------------------------------------------------------------+
|                                    PHASED ROADMAP OVERVIEW                                         |
+---------+------------------------------------------+-----------+-----------------------------------+
| Phase   | Scope / Focus Area                       | Duration  | Key Milestone                     |
+---------+------------------------------------------+-----------+-----------------------------------+
| Phase 1 | Project Scaffolding, Tooling & Core Map  | 1.5 Weeks | MapLibre WebGL Canvas & Chicago   |
| Phase 2 | State Stores & Responsive UI Shell       | 2.0 Weeks | Dockable Sidebar & Controls       |
| Phase 3 | Geospatial Layer Pipeline & Expressions  | 2.0 Weeks | 60 FPS GPU Filtering & Heatmaps   |
| Phase 4 | Backend REST / MVT & Prediction Hookup   | 2.5 Weeks | Dynamic BBOX & Real-time Scoring  |
| Phase 5 | Analytics Dashboard & Table Virtualizer  | 2.0 Weeks | TanStack Virtual 50k & Recharts   |
| Phase 6 | Multi-Stage Docker, Nginx & Optimization | 1.5 Weeks | Production Container (<30MB)      |
+---------+------------------------------------------+-----------+-----------------------------------+
```

### Phase 1: Project Scaffolding, Tooling & Core Map Setup
* **Objectives**: Initialize TypeScript Vite project, install pinned dependencies, configure Tailwind, and instantiate native MapLibre GL instance centered on Chicago.
* **Exact Terminal Commands**:
  ```bash
  # Step 1.1: Create Vite project with React and TypeScript template
  npm create vite@latest frontend -- --template react-ts
  cd frontend

  # Step 1.2: Install pinned runtime and dev dependencies
  npm install react@18.3.1 react-dom@18.3.1 maplibre-gl@4.7.1 zustand@5.0.0 @tanstack/react-query@5.56.2 @tanstack/react-table@8.20.5 @tanstack/react-virtual@3.10.8 clsx@2.1.1 tailwind-merge@2.5.2 lucide-react@0.446.0 @radix-ui/react-slider@1.2.0 @radix-ui/react-tabs@1.1.0 @radix-ui/react-dialog@1.1.1 @radix-ui/react-popover@1.1.1 @radix-ui/react-tooltip@1.1.2 @radix-ui/react-dropdown-menu@2.1.1 @radix-ui/react-checkbox@1.1.1 recharts@2.12.7 axios@1.7.7 date-fns@3.6.0
  npm install -D @types/geojson@7946.0.14 @types/node@22.5.5 tailwindcss@3.4.11 postcss@8.4.47 autoprefixer@10.4.20 vite-plugin-compression@0.5.1

  # Step 1.3: Initialize Tailwind configuration
  npx tailwindcss init -p

  # Step 1.4: Launch development server
  npm run dev
  ```
* **Acceptance Gate**: Map renders centered on Chicago coordinates `[-87.6298, 41.8781]` with dark Carto tiles. Component unmounting properly calls `map.remove()` without WebGL memory leaks.

### Phase 2: State Management & Responsive UI Shell
* **Objectives**: Implement Zustand stores (`useMapStore`, `useFilterStore`, `useUiStore`), create the collapsible left sidebar, header with preset selectors, and floating map control buttons.
* **Acceptance Gate**: Sidebar cleanly toggles between desktop, tablet, and mobile views; zoom and Chicago extent reset buttons trigger smooth camera animations without React re-render lag.

### Phase 3: Geospatial Layer Pipeline & WebGL Expression Filtering
* **Objectives**: Implement MapLibre layers for Crash Heatmaps, Crash Clusters (Supercluster), CDOT Road Closures, and Traffic Count stations. Connect the hour slider and severity checkboxes directly to `map.setFilter()` expressions.
* **Acceptance Gate**: Dragging the hour slider adjusts visible crash points at a continuous 60 FPS without sending network requests or triggering V8 garbage collection pauses.

### Phase 4: Backend REST / MVT Integration & Predictive Scoring
* **Objectives**: Wire TanStack Query v5 to FastAPI endpoints for dynamic BBOX feature querying, spatial statistics, and real-time ML risk scoring.
* **Acceptance Gate**: Zooming into a Chicago corridor fetches GeoJSON or MVT tiles in <300ms; submitting scenario variables to `/api/v1/predict` renders predicted risk score badges in real time.

### Phase 5: Analytics Dashboard & Tabular Virtualization
* **Objectives**: Build the slide-out Analytics Panel with Recharts (temporal histograms, weather correlation donut, AADT vs collisions scatter plot) and the resizable bottom Data Drawer with `@tanstack/react-virtual` for 10,000+ records.
* **Acceptance Gate**: Bottom drawer scrolls smoothly through 10,000+ crash records with fewer than 35 DOM nodes active; clicking a table row flies the map camera directly to that crash coordinate and highlights it.

### Phase 6: Multi-Stage Docker, Nginx Reverse Proxy & Production Hardening
* **Objectives**: Write multi-stage `Dockerfile` and `nginx.conf`. Verify container build size, gzip/brotli compression, CSP headers, and internal proxying to `http://backend:8000`.
* **Exact Terminal Commands**:
  ```bash
  # Step 6.1: Build frontend Docker image locally
  docker build -t chicago-traffic-frontend:latest -f Dockerfile .

  # Step 6.2: Inspect container image size (must be < 40MB)
  docker images chicago-traffic-frontend:latest

  # Step 6.3: Run container in bridge mode with backend mock or network
  docker run -d --name test-frontend -p 8080:80 chicago-traffic-frontend:latest

  # Step 6.4: Validate healthcheck and HTTP headers
  curl -I http://localhost:8080/health
  curl -I http://localhost:8080/
  ```
* **Acceptance Gate**: Container image size under 35MB; health endpoint returns `200 OK`; Lighthouse performance score ≥ 90; CSP strictly prevents unapproved scripts while permitting MapLibre Web Workers.

---

## 8. Summary of Architectural Recommendations for Implementers

1. **Abandon Leaflet**: Standardize on **MapLibre GL JS v4 (WebGL2)**. Leaflet is incapable of rendering 850k crashes or complex choropleths without crashing the browser tab.
2. **Strict React 18.3.1 Pinned Stack**: Do not jump to React 19 until geospatial peer dependencies stabilize.
3. **Direct Ref / Custom Hook over Declarative Wrappers**: Manage MapLibre imperatively via `useMapLibre` and Zustand to prevent re-render loops and WebGL context limits.
4. **Decouple Data Fetching from Layer Filtering**: Use WebGL shader expressions (`setFilter`) for instantaneous slider interactions; reserve HTTP requests for server aggregations.
5. **Enforce Tiered Data Delivery**: Never push >25,000 raw GeoJSON features to the client. Leverage PostGIS `ST_AsMVT` vector tiles or BBOX queries.
6. **Deploy via Nginx Alpine with Reverse Proxy**: Multi-stage Docker builds eliminate CORS issues, protect backend topologies, and deliver compressed assets at sub-10ms latencies.
