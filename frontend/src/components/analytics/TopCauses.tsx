import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { Card, fmtPct } from "@/components/ui";

export function TopCauses() {
  const f = useQueryFilters();
  const { data = [] } = useQuery({
    queryKey: ["causes", f],
    queryFn: () => crashService.causes(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const max = Math.max(1, ...data.map((d) => d.crashes));
  return (
    <Card title="Causas contributivas principales">
      <ul className="space-y-1.5">
        {data.map((d) => (
          <li key={d.cause} className="text-[11px]">
            <div className="flex justify-between gap-2 text-slate-300">
              <span className="truncate" title={d.cause}>{d.cause.toLowerCase()}</span>
              <span className="shrink-0 tabular-nums text-slate-500">{d.crashes.toLocaleString("es")} · <b className="text-red-300">{fmtPct(d.critical_rate)}</b></span>
            </div>
            <div className="mt-0.5 h-1 rounded bg-slate-800">
              <div className="h-1 rounded bg-indigo-500" style={{ width: `${(d.crashes / max) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
