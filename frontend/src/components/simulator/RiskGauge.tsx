import { useTheme } from "@/stores/useThemeStore";

/** Velocímetro semicircular: aguja según la probabilidad de la clase Crítica. */
export function RiskGauge({ score, max = 0.2, label }: { score: number; max?: number; label: string }) {
  const [lo, mid, hi] = useTheme().severity;
  const t = Math.min(score / max, 1);
  const angle = -90 + t * 180;
  const color = t > 0.66 ? hi : t > 0.33 ? mid : lo;
  const arc = (from: number, to: number) => {
    const p = (a: number) => {
      const r = ((a - 90) * Math.PI) / 180;
      return [100 + 80 * Math.cos(r), 100 + 80 * Math.sin(r)];
    };
    const [x1, y1] = p(from);
    const [x2, y2] = p(to);
    return `M ${x1} ${y1} A 80 80 0 0 1 ${x2} ${y2}`;
  };
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-[240px]" role="img" aria-label={`Riesgo ${label}`}>
      <path d={arc(-90, -30)} stroke={lo} strokeWidth="14" fill="none" />
      <path d={arc(-30, 30)} stroke={mid} strokeWidth="14" fill="none" />
      <path d={arc(30, 90)} stroke={hi} strokeWidth="14" fill="none" />
      <g transform={`rotate(${angle} 100 100)`} style={{ transition: "transform 400ms ease-out" }}>
        <line x1="100" y1="100" x2="100" y2="32" stroke="rgb(var(--slate-100))" strokeWidth="3" strokeLinecap="round" />
      </g>
      <circle cx="100" cy="100" r="6" fill="rgb(var(--slate-100))" />
      <text x="100" y="118" textAnchor="middle" fill={color} fontSize="13" fontWeight="700" style={{ fontFamily: "var(--font-display)" }}>{label}</text>
    </svg>
  );
}
