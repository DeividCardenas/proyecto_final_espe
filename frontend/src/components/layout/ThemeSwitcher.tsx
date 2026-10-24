import { useEffect, useRef, useState } from "react";
import { Palette } from "lucide-react";
import { THEME_ORDER, THEMES } from "@/theme/themes";
import { useThemeStore } from "@/stores/useThemeStore";
import { cn } from "@/components/ui";

/** Selector de piel visual: The Grid (TRON), Night City (Cyberpunk), NERV/MAGI (Evangelion) y Clásico. */
export function ThemeSwitcher() {
  const { themeId, setTheme } = useThemeStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Cambiar tema visual"
        className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
      >
        <Palette size={14} className="text-cyan-400" />
        {THEMES[themeId].name}
      </button>
      {open && (
        <ul role="listbox" className="hud-panel absolute right-0 top-10 z-50 w-64 space-y-1 border border-slate-700 bg-slate-900 p-1.5 shadow-2xl">
          {THEME_ORDER.map((id) => {
            const t = THEMES[id];
            return (
              <li key={id}>
                <button
                  role="option"
                  aria-selected={id === themeId}
                  onClick={() => { setTheme(id); setOpen(false); }}
                  className={cn("flex w-full items-center gap-3 rounded px-2 py-1.5 text-left hover:bg-slate-800",
                    id === themeId && "bg-slate-800")}
                >
                  <span className="flex shrink-0 overflow-hidden rounded-sm border border-slate-600">
                    {t.swatch.map((c) => <i key={c} className="block h-6 w-3" style={{ background: c }} />)}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-xs font-semibold text-slate-100">{t.name}</span>
                    <span className="block truncate text-[10px] text-slate-500">{t.tagline}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
