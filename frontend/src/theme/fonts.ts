import type { ThemeId } from "./themes";

/**
 * Fuentes de cada piel, cargadas sólo al elegirla (y sólo el subconjunto latino, que
 * incluye tildes y eñe). Antes se importaban todas al arrancar: 154 @font-face y un CSS
 * de ~250 KB que bloqueaba el primer render aunque el tema por defecto sólo use Inter.
 */
const rajdhani = () => Promise.all([
  import("@fontsource/rajdhani/latin-500.css"),
  import("@fontsource/rajdhani/latin-600.css"),
  import("@fontsource/rajdhani/latin-700.css"),
]);
const mono = () => import("@fontsource/share-tech-mono/latin-400.css");

const LOADERS: Record<ThemeId, () => Promise<unknown>> = {
  classic: () => Promise.resolve(), // Inter ya va en el paquete principal (main.tsx)
  tron: () => Promise.all([
    import("@fontsource/orbitron/latin-500.css"),
    import("@fontsource/orbitron/latin-700.css"),
    rajdhani(),
    mono(),
  ]),
  cyberpunk: () => Promise.all([rajdhani(), mono()]),
  nerv: () => Promise.all([
    import("@fontsource/shippori-mincho-b1/latin-800.css"),
    import("@fontsource/barlow-condensed/latin-400.css"),
    import("@fontsource/barlow-condensed/latin-600.css"),
    mono(),
  ]),
};

const loaded = new Map<ThemeId, Promise<unknown>>();

/** Carga (una sola vez) las fuentes del tema. Si fallan, se usan las de respaldo del sistema. */
export function loadThemeFonts(id: ThemeId): Promise<unknown> {
  let p = loaded.get(id);
  if (!p) {
    p = LOADERS[id]().catch(() => loaded.delete(id));
    loaded.set(id, p);
  }
  return p;
}
