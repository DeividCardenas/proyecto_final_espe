/** Utilidades de fechas en formato YYYY-MM-DD (siempre como fecha de calendario, sin zona). */

/** "YYYY-MM-DD..." → Date local (new Date("YYYY-MM-DD") la leería en UTC y podría caer el día anterior). */
export function parseDay(s: string): Date {
  const [y, m, d] = s.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function isoDay(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export interface PeriodPreset { label: string; start: string | null }

/**
 * Atajos de periodo anclados al último dato disponible, no al día de hoy: si los datos
 * terminan el 23 oct, «30 días» es 24 sep – 23 oct aunque se consulte en noviembre.
 */
export function periodPresets(lastDate: string | null, today: Date = new Date()): PeriodPreset[] {
  const anchor = lastDate ? parseDay(lastDate) : today;
  const back = (days: number) => {
    const d = new Date(anchor);
    d.setDate(d.getDate() - days + 1);
    return isoDay(d);
  };
  const yearBack = () => {
    const d = new Date(anchor);
    d.setFullYear(d.getFullYear() - 1);
    d.setDate(d.getDate() + 1);
    return isoDay(d);
  };
  return [
    { label: "Todo", start: null },
    { label: "1 año", start: yearBack() },
    { label: "90 días", start: back(90) },
    { label: "30 días", start: back(30) },
  ];
}

/** Ordena un rango para que el inicio nunca sea posterior al final. */
export function orderedRange(start: string | null, end: string | null): [string | null, string | null] {
  return start && end && start > end ? [end, start] : [start, end];
}

/** "2026-10-23T14:05:00" → "23 oct 2026, 14:05" (la API entrega hora local de Chicago). */
export function fmtDateTime(s: string | null | undefined): string {
  if (!s) return "—";
  const [day, time] = s.split("T");
  const d = parseDay(day);
  if (Number.isNaN(d.getTime())) return s;
  const date = d.toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });
  return time ? `${date}, ${time.slice(0, 5)}` : date;
}
