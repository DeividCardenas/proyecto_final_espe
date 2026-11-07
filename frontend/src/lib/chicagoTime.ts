/**
 * Fechas en la hora de Chicago, independientes de la zona horaria del navegador.
 *
 * El simulador manda «when» sin zona (YYYY-MM-DDTHH:00:00): la API lo interpreta como
 * hora local de Chicago. Si se mandara toISOString() (UTC), un usuario en Bogotá que
 * elige las 18:00 obtendría la predicción de las 17:00 de Chicago (o otra, según el país).
 */
export const CHICAGO_TZ = "America/Chicago";

/** Fecha (YYYY-MM-DD) y hora (0-23) actuales en Chicago. */
export function chicagoNow(now: Date = new Date()): { date: string; hour: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: CHICAGO_TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return { date: `${get("year")}-${get("month")}-${get("day")}`, hour: Number(get("hour")) % 24 };
}

/** Momento local de Chicago sin zona horaria, p. ej. "2026-11-07T18:00:00". */
export function chicagoLocalIso(date: string, hour: number): string {
  return `${date}T${String(hour).padStart(2, "0")}:00:00`;
}
