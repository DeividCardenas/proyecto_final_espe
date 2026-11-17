import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Compass } from "lucide-react";
import { useTopSegments } from "@/hooks/useTopSegments";
import { useKpis } from "@/hooks/useKpis";
import { useTheme } from "@/stores/useThemeStore";
import { markGuideSeen, startFullTour } from "@/components/tour/launcher";
import { cn } from "@/components/ui";
import type { ThemeDef } from "@/theme/themes";

/** Se muestra una vez por sesión del navegador: cada pestaña nueva (p. ej. en la expo) vuelve a abrir con ella. */
export const INTRO_SEEN_KEY = "chicago-road-risk-intro-seen";

export function introSeen(): boolean {
  try {
    if (new URLSearchParams(window.location.search).get("intro") === "0") return true;
    return sessionStorage.getItem(INTRO_SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

function markIntroSeen() {
  try {
    sessionStorage.setItem(INTRO_SEEN_KEY, "1");
  } catch {
    /* sólo en memoria */
  }
}

const reducedMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Cuenta de 0 al valor con desaceleración; sin animación si el usuario la desactivó. */
function useCountUp(target: number | null, delay = 0, ms = 1600) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (target === null) return;
    if (reducedMotion()) {
      setV(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now() + delay;
    const tick = (now: number) => {
      const k = Math.min(1, Math.max(0, (now - t0) / ms));
      setV(target * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, delay, ms]);
  return v;
}

const es = (n: number, d = 0) => n.toLocaleString("es", { minimumFractionDigits: d, maximumFractionDigits: d });

interface Pt { x: number; y: number; p: number; rank: number; delay: number }

// Encuadre de la ciudad (lon/lat) y centro del Loop, desde donde se «enciende» el mapa
const LON = [-87.94, -87.52];
const LAT = [41.64, 42.03];
const LOOP = [-87.63, 41.88];

/**
 * Fondo animado con datos reales: las cuadras prioritarias del modelo se encienden desde el
 * centro hacia afuera y dibujan Chicago; las de mayor riesgo emiten pulsos.
 */
function CityCanvas({ points, theme, top1, label }: { points: { lon: number; lat: number; p: number; rank: number }[]; theme: ThemeDef; top1: number; label: string | null }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || points.length === 0) return;
    const accent = theme.swatch[1];
    const critical = theme.severity[2];
    const still = reducedMotion();
    let raf = 0;
    let pts: Pt[] = [];
    let W = 0;
    let H = 0;
    const rings: { x: number; y: number; t0: number }[] = [];

    const layout = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // La ciudad ocupa la mitad derecha en pantallas anchas y todo el fondo en las angostas
      const wide = W >= 900;
      const boxW = wide ? W * 0.55 : W;
      const boxH = H * 0.92;
      const kx = Math.cos((41.85 * Math.PI) / 180);
      const spanX = (LON[1] - LON[0]) * kx;
      const spanY = LAT[1] - LAT[0];
      const s = Math.min(boxW / spanX, boxH / spanY);
      const ox = (wide ? W * 0.44 : 0) + (boxW - spanX * s) / 2;
      const oy = (H - spanY * s) / 2;
      const proj = (lon: number, lat: number) => [ox + (lon - LON[0]) * kx * s, oy + (LAT[1] - lat) * s];
      const [cx, cy] = proj(LOOP[0], LOOP[1]);
      const maxD = Math.hypot(W, H) * 0.6;
      pts = points.map((q) => {
        const [x, y] = proj(q.lon, q.lat);
        return { x, y, p: q.p, rank: q.rank, delay: (Math.hypot(x - cx, y - cy) / maxD) * 1800 + Math.random() * 250 };
      });
    };
    layout();
    const t0 = performance.now();
    const hot = () => pts.filter((q) => q.rank <= Math.max(20, top1 / 3));

    const draw = (now: number) => {
      const t = still ? 1e9 : now - t0;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const q of pts) {
        const k = Math.min(1, Math.max(0, (t - q.delay) / 500));
        if (k <= 0) continue;
        const top = q.rank <= top1;
        const r = top ? 2.6 : 1.5;
        ctx.globalAlpha = k * (top ? 0.95 : 0.55);
        ctx.fillStyle = top ? critical : accent;
        ctx.beginPath();
        ctx.arc(q.x, q.y, r, 0, Math.PI * 2);
        ctx.fill();
        if (top) {
          ctx.globalAlpha = k * 0.18;
          ctx.beginPath();
          ctx.arc(q.x, q.y, r * 3.2, 0, Math.PI * 2);
          ctx.fill();
        }
        // Destello al encenderse
        if (k < 1) {
          ctx.globalAlpha = (1 - k) * 0.6;
          ctx.fillStyle = "#ffffff";
          ctx.beginPath();
          ctx.arc(q.x, q.y, r * 2.4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      // Pulsos sobre las cuadras más riesgosas
      if (!still && t > 1600 && Math.random() < 0.045) {
        const h = hot();
        const q = h[Math.floor(Math.random() * h.length)];
        if (q) rings.push({ x: q.x, y: q.y, t0: t });
      }
      ctx.strokeStyle = critical;
      ctx.lineWidth = 1.5;
      for (let i = rings.length - 1; i >= 0; i--) {
        const a = (t - rings[i].t0) / 1600;
        if (a >= 1) {
          rings.splice(i, 1);
          continue;
        }
        ctx.globalAlpha = (1 - a) * 0.8;
        ctx.beginPath();
        ctx.arc(rings[i].x, rings[i].y, 4 + a * 34, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
      // Rótulo de la cuadra n.º 1 una vez encendido el mapa (sólo en pantallas anchas)
      const first = pts.find((q) => q.rank === 1);
      if (label && first && W >= 900) {
        const a = Math.min(1, Math.max(0, (t - 2600) / 600));
        if (a > 0) {
          const font = getComputedStyle(canvas).getPropertyValue("--font-body") || "Inter";
          ctx.font = `600 15px ${font}, Inter, sans-serif`;
          const tw = ctx.measureText(label).width;
          // A la derecha del punto si cabe; si no, a la izquierda
          const right = first.x + 64 + tw < W - 24;
          const dir = right ? 1 : -1;
          const lx = first.x + dir * 46;
          const ly = first.y - 46;
          ctx.globalAlpha = a;
          ctx.strokeStyle = critical;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(first.x + dir * 4, first.y - 4);
          ctx.lineTo(lx, ly);
          ctx.lineTo(lx + dir * 12, ly);
          ctx.stroke();
          ctx.textAlign = right ? "left" : "right";
          const tx = lx + dir * 18;
          ctx.fillStyle = critical;
          ctx.font = `600 11px ${font}, Inter, sans-serif`;
          ctx.fillText("CUADRA N.º 1 DEL MODELO", tx, ly - 6);
          ctx.fillStyle = "#ffffff";
          ctx.font = `600 15px ${font}, Inter, sans-serif`;
          ctx.fillText(label, tx, ly + 12);
          ctx.textAlign = "left";
          ctx.globalAlpha = 1;
        }
      }
      if (!still) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    const onResize = () => layout();
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [points, theme, top1, label]);

  return <canvas ref={ref} aria-hidden className="absolute inset-0 h-full w-full" />;
}

function Stat({ value, label, delay, className }: { value: string; label: string; delay: number; className?: string }) {
  return (
    <div className="intro-rise" style={{ animationDelay: `${delay}ms` }}>
      <p className={cn("hud-kpi hud-title text-3xl font-semibold tabular-nums text-slate-50 sm:text-4xl", className)}>{value}</p>
      <p className="mt-1 text-xs uppercase tracking-wider text-slate-400 sm:text-[13px]">{label}</p>
    </div>
  );
}

/**
 * Portada de la aplicación: lo primero que se ve al abrirla. Presenta la pregunta, el
 * hallazgo principal con cifras reales de la API y lleva al mapa (que ya cargó detrás).
 */
export function IntroScreen({ onClose }: { onClose: () => void }) {
  const theme = useTheme();
  const { metrics, segments } = useTopSegments();
  const { city } = useKpis();
  const [leaving, setLeaving] = useState(false);
  const enterRef = useRef<HTMLButtonElement>(null);

  const m = metrics.data;
  const win = m?.comparison?.[m.winner];
  const total = city.data?.total_crashes ?? null;
  const from = city.data?.first_date?.slice(0, 4);
  const to = city.data?.last_date?.slice(0, 4);

  const nCrashes = useCountUp(total, 500);
  const nSegments = useCountUp(m?.forecast.segments_scored ?? null, 700);
  const capture = useCountUp(win ? win.top10_capture_severe * 100 : null, 900);
  const lift = useCountUp(win ? win.top10_lift : null, 1100);

  const first = segments.data?.features.find((f) => f.properties.priority_rank === 1)?.properties;
  // Memorizado: si el arreglo cambiara en cada render (los contadores re-renderizan por cuadro) la animación se reiniciaría
  const points = useMemo(() => segments.data?.features.map((f) => ({
    lon: f.geometry.coordinates[0],
    lat: f.geometry.coordinates[1],
    p: f.properties.p_alto,
    rank: f.properties.priority_rank,
  })) ?? [], [segments.data]);

  const close = (tour = false) => {
    if (leaving) return;
    markIntroSeen();
    if (tour) markGuideSeen();
    setLeaving(true);
    window.setTimeout(() => {
      onClose();
      if (tour) void startFullTour();
    }, reducedMotion() ? 0 : 650);
  };

  useEffect(() => {
    enterRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="intro-title" data-testid="intro-screen"
      className={cn("intro-screen fixed inset-0 z-[60] overflow-hidden bg-slate-950 text-slate-100", leaving && "intro-leave")}>
      <div className="intro-grid absolute inset-0" />
      <CityCanvas points={points} theme={theme} top1={Math.ceil((m?.forecast.segments_scored ?? 0) * 0.01)}
        label={first ? `${first.segment_id} · P(alto) ${es(first.p_alto * 100)} %` : null} />
      <div className="intro-vignette absolute inset-0" />

      <div className="relative z-10 flex h-full flex-col justify-between px-6 py-6 sm:px-12 sm:py-10 lg:px-20">
        <header className="intro-rise flex items-center gap-3" style={{ animationDelay: "0ms" }}>
          <span className="intro-dot h-2.5 w-2.5 rounded-full" />
          <span className="hud-title text-xs font-semibold uppercase tracking-[0.25em] text-cyan-300 sm:text-sm">Chicago Road Risk</span>
          <span className="hidden text-xs text-slate-400 sm:inline">· Especialización en Big Data · UNICESMAG 2026</span>
        </header>

        <main className="max-w-3xl lg:max-w-[46vw]">
          <h1 id="intro-title" className="hud-title intro-title intro-rise text-4xl font-bold leading-[1.05] tracking-tight text-slate-50 sm:text-6xl xl:text-7xl"
            style={{ animationDelay: "120ms" }}>
            ¿Dónde será el próximo <span className="intro-hl">siniestro grave</span> en Chicago?
          </h1>
          <p className="intro-rise mt-5 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-xl" style={{ animationDelay: "260ms" }}>
            Un modelo de machine learning entrenado con los siniestros reales de la ciudad señala
            las cuadras donde conviene intervenir primero. Cada punto del fondo es una de ellas.
          </p>

          <div className="mt-8 grid max-w-2xl grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4 lg:max-w-none">
            <Stat delay={420} value={total !== null ? es(nCrashes) : "…"} label={from && to ? `siniestros ${from}–${to}` : "siniestros analizados"} />
            <Stat delay={520} value={m ? es(nSegments) : "…"} label="cuadras evaluadas" />
            <Stat delay={620} value={win ? `${es(capture)}%` : "…"} label="de los graves, en el 10 % señalado" className="intro-critical" />
            <Stat delay={720} value={win ? `${es(lift, 1)}×` : "…"} label="mejor que elegir al azar" />
          </div>

          <div className="intro-rise mt-10 flex flex-wrap items-center gap-4" style={{ animationDelay: "880ms" }}>
            <button ref={enterRef} onClick={() => close()} data-testid="intro-enter"
              className="intro-cta group flex items-center gap-3 rounded-full bg-cyan-500 px-7 py-3.5 text-base font-semibold text-slate-950 transition hover:bg-cyan-400 sm:text-lg">
              Explorar el mapa
              <ArrowRight size={20} className="transition-transform group-hover:translate-x-1" />
            </button>
            <button onClick={() => close(true)}
              className="flex items-center gap-2 rounded-full border border-slate-600 px-5 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-400 hover:text-cyan-200 sm:text-base">
              <Compass size={18} /> Recorrido guiado de 1 minuto
            </button>
          </div>
        </main>

        <footer className="intro-rise flex flex-wrap items-end justify-between gap-3 text-xs text-slate-400 sm:text-sm" style={{ animationDelay: "1000ms" }}>
          <span>Deivid Julian Cardenas Melo · Dillan Alexander Cardenas Melo</span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1.5"><i className="intro-key-dot" style={{ background: theme.severity[2] }} /> top 1 % de riesgo</span>
            <span className="flex items-center gap-1.5"><i className="intro-key-dot" style={{ background: theme.swatch[1] }} /> top 10 %</span>
            <span className="hidden md:inline">· Enter para entrar</span>
          </span>
        </footer>
      </div>
    </div>
  );
}
