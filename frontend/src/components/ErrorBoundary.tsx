import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props {
  /** Qué parte de la interfaz protege (aparece en el mensaje) */
  area: string;
  children: ReactNode;
  className?: string;
  /** Cambiar esta clave reinicia el límite (p. ej. al cambiar de sección) */
  resetKey?: unknown;
}

interface State { error: Error | null }

/**
 * Límite de errores: si una parte falla al pintarse o al cargar su módulo, se muestra un
 * aviso con «Reintentar» en lugar de desmontar toda la aplicación (pantalla en blanco).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.MODE !== "test") console.error(`[${this.props.area}]`, error, info.componentStack);
  }

  componentDidUpdate(prev: Props) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    const chunk = isChunkError(this.state.error);
    return (
      <div role="alert" className={this.props.className ?? "m-3 rounded-xl border border-red-900/60 bg-slate-900/90 p-3 text-xs text-slate-300"}>
        <p className="flex items-center gap-1.5 font-semibold text-slate-100">
          <AlertTriangle size={14} className="text-amber-400" />
          {chunk ? `No se pudo cargar «${this.props.area}»` : `Algo falló en «${this.props.area}»`}
        </p>
        <p className="mt-1 text-slate-400">
          {chunk ? "Puede que la aplicación se haya actualizado. Recarga la página." : "El resto de la plataforma sigue funcionando."}
        </p>
        <button
          onClick={() => (chunk ? window.location.reload() : this.setState({ error: null }))}
          className="mt-2 inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800"
        >
          <RotateCcw size={12} />{chunk ? "Recargar" : "Reintentar"}
        </button>
      </div>
    );
  }
}

export function isChunkError(e: unknown): boolean {
  const msg = e instanceof Error ? `${e.name} ${e.message}` : String(e);
  return /dynamically imported module|Importing a module script failed|ChunkLoadError|Loading chunk/i.test(msg);
}
