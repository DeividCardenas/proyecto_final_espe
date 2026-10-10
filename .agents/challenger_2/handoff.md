# HANDOFF REPORT — CHALLENGER 2
## Empirical Frontend, Peer-Deps & Spatial Math Verification

- **Role:** critic, specialist (Challenger 2)
- **Handoff Type:** Hard (Task complete)
- **Target Recipient:** parent (`7113e5ec-e138-4537-a946-a3b08ebfac68`), Lead Architect (`worker_1`)
- **Date:** 2026-09-12T14:15:00Z
- **Verdict:** ⚠️ **REQUEST_CHANGES**

---

### 1. Observation

Direct observations from `c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md` and related agent artifacts (`explorer_frontend/report.md`):

1. **Async Map Load Race in `useMapLibre.ts`:**
   In `explorer_frontend/report.md`, Lines 367-377 and referenced in `plan_de_implementacion_fases.md` (Lines 174-183, 1137-1140):
   ```typescript
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
   ```
   There is no check whether the component is still mounted when `map.on('load')` fires asynchronously.

2. **Unimplemented WebGL Context Restoration Claim:**
   In `plan_de_implementacion_fases.md`, Section 2.6, Lines 181-182:
   > "2. Suscripción a eventos webglcontextlost y webglcontextrestored para pausar y reanudar el bucle de renderizado con elegancia si el sistema operativo reclama memoria de video."
   In the actual code implementation of `useMapLibre.ts` (Lines 323-382 of `explorer_frontend/report.md`), neither `webglcontextlost` nor `webglcontextrestored` listeners are attached.

3. **Missing WebGL2 Hardware Capability Check:**
   In `plan_de_implementacion_fases.md`, Section 2.5 (Lines 160-170) and Section 6 Phase 5 (Lines 1137-1140), `new maplibregl.Map(...)` is instantiated without checking `maplibregl.supported()`, which causes an unhandled fatal error in browsers without WebGL2 support.

4. **Circular Structure in Zustand State:**
   In `plan_de_implementacion_fases.md`, Section 2.6 (Line 183) and Section 5 (Line 823):
   > "useMapStore.ts: Estado del viewport, mapa activo y capas visibles"
   Storing the MapLibre `Map` class instance in the reactive state tree triggers circular structure errors (`Converting circular structure to JSON`) when devtools are enabled.

5. **Loose Bounding Box for Data Cleaning:**
   In `plan_de_implementacion_fases.md`, Section 6 Phase 2, Line 947:
   > "latitudes válidas: 41.60° a 42.10°; longitudes válidas: -88.10° a -87.40°"
   The actual geographic bounding envelope for the City of Chicago is Lat: $\sim 41.644^\circ$ to $42.023^\circ\text{ N}$; Lon: $\sim -87.940^\circ$ to $-87.524^\circ\text{ W}$. The Western limit $-88.10^\circ$ extends $>13\text{ km}$ into DuPage County.

6. **Missing React Types in Phase 5 CLI Command:**
   In `plan_de_implementacion_fases.md`, Section 6 Phase 5, Lines 1166-1167:
   ```bash
   npm install -D @types/geojson@7946.0.14 @types/node@22.5.5 tailwindcss@3.4.11 postcss@8.4.47 autoprefixer@10.4.20 vite-plugin-compression@0.5.1
   ```
   `@types/react@18.3.10` and `@types/react-dom@18.3.0` are present in `package.json` (Lines 294-295) but omitted from this step-by-step CLI command.

7. **Exact Metric Equivalence for 250m Buffer:**
   In `plan_de_implementacion_fases.md`, Section 2.1 (Lines 102-108) and Section 6 Phase 2 (Line 968):
   ```sql
   ST_DWithin(ST_Transform(c.geom, 3435), ST_Transform(p.geom, 3435), 820.21)
   ```
   1 US Survey Foot $= 1200 / 3937\text{ m} \approx 0.3048006096\text{ m}$. $250 / (1200/3937) = 820.208333...\text{ survey feet} \approx 820.21\text{ ftUS}$.

8. **Metric Distortion in EPSG:4326:**
   At Latitude $41.8781^\circ\text{ N}$, $1^\circ\text{ Lat} \approx 111.07\text{ km}$, $1^\circ\text{ Lon} \approx 82.89\text{ km}$. Distortion is $(111.07 - 82.89) / 111.07 = 25.37\%$.

9. **Dependency Matrix Verification:**
   React 18.3.1 is pinned in `frontend/package.json` (Line 272). Radix UI primitives, Recharts 2.12.7, TanStack Table 8.20.5, TanStack Virtual 3.10.8, and Zustand 5.0.0 all declare peer dependencies satisfying React 18.x.

---

### 2. Logic Chain

1. **Premise 1 (From Obs 1):** In React 18 `StrictMode` (standard in Vite development) or when users navigate away quickly during page load, components unmount immediately while HTTP requests for map styles/tiles are in flight.
2. **Premise 2 (From Obs 1):** `useMapLibre` executes `map.remove()` on unmount, destroying the WebGL context. When the style load finishes, the un-guarded `map.on('load')` fires, passing the destroyed map into `useMapStore.setMapInstance(map)`.
3. **Inference 1:** Downstream components call methods on this destroyed map instance, causing runtime crashes (`Map has been removed`), while the store retains references preventing garbage collection of WebGL memory buffers.
4. **Premise 3 (From Obs 2):** When a laptop sleeps or switches GPUs, the browser sends `webglcontextlost`. Because no listener exists to call `event.preventDefault()`, the WebGL2 context is permanently dropped, resulting in a black canvas.
5. **Premise 4 (From Obs 3):** Machines without WebGL2 crash synchronously when calling `new maplibregl.Map()`.
6. **Premise 5 (From Obs 5):** An overly wide bounding box in `data_cleaner.py` allows non-Chicago data into the dataset, skewing feature distributions for machine learning.
7. **Premise 6 (From Obs 7, 8, 9):** Spatial transformations to `EPSG:3435` with an 820.21 ft buffer, the 25.37% distortion claim for `EPSG:4326`, and the pinned React 18.3.1 dependency matrix are mathematically sound and robust.
8. **Deduction:** The architecture is structurally sound, but critical frontend lifecycle flaws and boundary inconsistencies require amendments before code generation begins.

---

### 3. Caveats

- **No Caveats.** All spatial math was verified using geodesic conversion formulas (NIST / US Survey Foot definitions and WGS84 ellipsoid parameters). Peer dependency contracts were analyzed against the official npm semver specifications.

---

### 4. Conclusion

- **Verdict:** **REQUEST_CHANGES**.
- **Assessment:** The implementation plan cannot be approved unconditionally. It requires 6 specific amendments to guarantee stability during development (React 18 StrictMode), prevent WebGL memory leaks/context loss, ensure clean data ingestion, and guarantee reproducible CLI installation.

---

### 5. Verification Method

To independently verify these findings:

1. **Verify StrictMode Race Condition:**
   Create a test React 18 component with `<React.StrictMode>` invoking the un-guarded `useMapLibre` hook. In the browser console, observe that `map.remove()` runs before `map.on('load')` fires, and inspect that `useMapStore.getState().mapInstance` holds an instance where `_removed === true`.
2. **Verify Spatial Buffer Conversion:**
   Execute in any calculator / python REPL:
   `250 * (3937 / 1200)` $\rightarrow$ yields `820.2083333333334`, which rounds to `820.21` survey feet.
3. **Verify WGS84 Degree Distortion at Chicago:**
   Execute:
   `import math; lat = math.radians(41.8781); 111.07; lon_km = 111.32 * math.cos(lat); (111.07 - lon_km) / 111.07` $\rightarrow$ yields `0.2537` (25.37%).
4. **Verify Missing CLI Types:**
   Inspect Line 1167 of `plan_de_implementacion_fases.md` and verify absence of `@types/react` and `@types/react-dom`.

**Invalidation Condition:**
This challenge is invalidated if `useMapLibre.ts` is updated to include the `isMounted` guard, desubscription, `webglcontextlost` handling, and `maplibregl.supported()` check, and if the data cleaning BBOX and CLI commands are corrected in `plan_de_implementacion_fases.md`.
