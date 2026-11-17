"""Genera las figuras del informe de resultados (y del póster) a partir de los reportes.

    python docs/informe/generar_figuras.py

Lee backend/app/ml/models/*_report.json y data/processed/cifras_informe.json (o, si no existe,
la copia versionada docs/informe/cifras_informe.json del 17 nov 2026)
(se crea con `docker compose run --rm etl python -m app.reports.cifras_informe`).
Escribe PNG (200 dpi) y SVG en docs/informe/figuras/.

Criterios de diseño: el título dice la conclusión; un solo color de énfasis (naranja) y el
resto en gris; etiquetas directas en vez de leyendas; sin rejilla ni marcos innecesarios;
un solo eje por gráfica; las cifras en formato español (coma decimal).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "figuras"
MODELS = ROOT / "backend" / "app" / "ml" / "models"
_LIVE = ROOT / "data" / "processed" / "cifras_informe.json"
CIFRAS = Path(sys.argv[1]) if len(sys.argv) > 1 else (_LIVE if _LIVE.exists() else Path(__file__).resolve().parent / "cifras_informe.json")

INK = "#13212e"       # texto principal
MUTED = "#5b6b78"     # texto secundario
GRAY = "#b4bec7"      # marcas de contexto
EMPH = "#d9600f"      # énfasis (hallazgo)
NAVY = "#0f3b57"      # referencia destacada
RULE = "#dfe5ea"

for f in ("Inter", "DejaVu Sans"):
    if any(f in x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break
plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": RULE, "axes.labelcolor": MUTED, "xtick.color": MUTED,
    "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlelocation": "left", "axes.titleweight": "semibold", "axes.titlesize": 13,
    "axes.titlecolor": INK, "figure.dpi": 100, "savefig.bbox": "tight", "savefig.pad_inches": 0.15,
})


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}".replace(".", ",") + " %"


def num(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    title, sub = getattr(fig, "_heading", (None, None))
    if title:
        # Deja sitio a las etiquetas del eje y para que todo quede dentro de la figura, y alinea
        # título y subtítulo con el borde izquierdo real del contenido.
        w, h = fig.get_size_inches()
        fig.canvas.draw()
        bb = fig.get_tightbbox(fig.canvas.get_renderer())
        left = fig.subplotpars.left - bb.x0 / w + 0.01
        fig.subplots_adjust(left=left, top=1 - 0.95 / h)
        fig.text(0.01, 1 - 0.12 / h, title, color=INK, fontsize=13.5, fontweight="semibold", va="top", ha="left")
        fig.text(0.01, 1 - 0.46 / h, sub, color=MUTED, fontsize=10, va="top", ha="left")
    fig.savefig(OUT / f"{name}.png", dpi=200, facecolor="white")
    fig.savefig(OUT / f"{name}.svg", facecolor="white")
    plt.close(fig)
    print("  ", name)


def heading(fig, title: str, sub: str) -> None:
    """Título (la conclusión) y subtítulo alineados al borde izquierdo de la figura."""
    fig._heading = (title, sub)


# ---------------------------------------------------------------------------
def fig_captura_cuadras(seg: dict) -> None:
    b = seg["bootstrap_top10_capture"]
    rows = [
        ("Random Forest", "random_forest", GRAY),
        ("Regla: más siniestros el año anterior", "historial_siniestros", NAVY),
        ("XGBoost", "xgboost", GRAY),
        ("Regresión logística (modelo elegido)", "logistic_regression", EMPH),
        ("Regla: más lesionados el año anterior", "historial_lesionados", GRAY),
        ("Regla: más siniestros graves el año anterior", "historial_graves", GRAY),
    ]
    rows.sort(key=lambda r: b[r[1]]["capture"])
    fig, ax = plt.subplots(figsize=(8.2, 3.9))
    for i, (label, key, color) in enumerate(rows):
        c, (lo, hi) = b[key]["capture"], b[key]["ci95"]
        ax.plot([lo, hi], [i, i], color=color, lw=2.2, solid_capstyle="round", alpha=0.55)
        ax.plot(c, i, "o", ms=9, color=color, mec="white", mew=1.5, zorder=3)
        ax.text(hi + 0.008, i, pct(c), va="center", color=INK, fontsize=10.5,
                fontweight="semibold" if color != GRAY else "normal")
    ax.axvline(0.10, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.text(0.104, len(rows) - 0.55, "azar: 10 %", color=MUTED, fontsize=9.5, va="center")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xlim(0, 0.55)
    ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5], ["0 %", "10 %", "20 %", "30 %", "40 %", "50 %"])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Siniestros graves del año siguiente captados en el 10 % de cuadras priorizadas")
    heading(fig, "Cuatro de cada diez siniestros graves ocurren en el 10 % de las cuadras", "Punto: captura en el año de prueba · línea: intervalo de confianza del 95 % (bootstrap)")
    save(fig, "01_captura_top10_cuadras")


def fig_modelo_siniestro(rep: dict) -> None:
    td = rep["models"][rep["winner"]]["test_decision"]
    abl = rep["ablation_pre_crash_only"]["auc_roc_ovr_macro"]
    fig, ax = plt.subplots(figsize=(8.2, 2.9))
    rows = [("Solo condiciones previas al choque", abl, GRAY),
            ("Con el mecanismo del siniestro (modelo final)", td["auc_roc_ovr_macro"], EMPH)]
    for i, (label, v, color) in enumerate(rows):
        ax.barh(i, v - 0.5, left=0.5, height=0.5, color=color)
        ax.text(v + 0.004, i, num(v, 3), va="center", color=INK, fontsize=10.5,
                fontweight="semibold" if color == EMPH else "normal")
    ax.axvline(0.70, color=NAVY, lw=1.2, ls=(0, (3, 3)))
    ax.text(0.702, 1.45, "meta OE3: 0,70", color=NAVY, fontsize=9.5)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xticks([0.5, 0.6, 0.7, 0.8], ["0,5", "0,6", "0,7", "0,8"])
    ax.set_xlim(0.5, 0.8)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("AUC-ROC macro en el año de prueba (0,5 = azar)")
    heading(fig, "El tipo de choque explica buena parte de la severidad", "Modelo por siniestro (XGBoost), partición temporal")
    save(fig, "02_auc_modelo_siniestro")


def fig_calibracion(rep: dict) -> None:
    cal = rep["models"][rep["winner"]]["calibration_critical"]
    pts = cal["reliability"]
    x = [p["mean_predicted"] for p in pts]
    y = [p["observed_rate"] for p in pts]
    top = max(max(x), max(y)) * 1.08
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    ax.plot([0, top], [0, top], color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.text(top * 0.30, top * 0.40, "calibración perfecta", color=MUTED, fontsize=9.5, rotation=38)
    ax.plot(x, y, color=EMPH, lw=2, marker="o", ms=7, mec="white", mew=1.3)
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    ticks = [t for t in (0, 0.05, 0.10, 0.15, 0.20, 0.25) if t <= top]
    ax.set_xticks(ticks, [pct(t, 0) for t in ticks])
    ax.set_yticks(ticks, [pct(t, 0) for t in ticks])
    ax.set_xlabel("Probabilidad predicha de siniestro crítico")
    ax.set_ylabel("Proporción observada")
    heading(fig, "Las probabilidades son confiables",
            f"Modelo por siniestro, año de prueba, deciles · ECE {num(cal['ece'], 3)} · Brier {num(cal['brier'], 3)}")
    save(fig, "06_calibracion_siniestro")


# ---------------------------------------------------------------------------
def fig_velocidad(c: dict) -> None:
    sp = [s for s in c["speed"] if s["n"] >= 1000]
    x = [s["mph"] for s in sp]
    y = [s["critical_rate"] for s in sp]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.plot(x, y, color=EMPH, lw=2.2, marker="o", ms=8, mec="white", mew=1.5)
    for xi, yi in zip(x, y):
        ax.text(xi, yi + 0.0018, pct(yi), ha="center", color=INK, fontsize=10)
    ax.axhline(c["crashes"]["critical_rate"], color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.text(x[-1] + 1.2, c["crashes"]["critical_rate"], f"media de la ciudad\n{pct(c['crashes']['critical_rate'])}",
            color=MUTED, fontsize=9.5, va="center")
    ax.set_xlim(x[0] - 2, x[-1] + 7)
    ax.set_xticks(x, [f"{v} mph" for v in x])
    ax.set_ylim(0, max(y) * 1.2)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    heading(fig, "A más velocidad señalizada, más siniestros graves", "Proporción de siniestros con fallecidos o lesiones incapacitantes, por límite de velocidad")
    save(fig, "03_velocidad_tasa_critica")


def fig_vulnerables(c: dict) -> None:
    base = c["crashes"]["critical_rate"]
    rows = [("Todos los siniestros", base, GRAY),
            ("Con ciclista", c["vulnerable"]["PEDALCYCLIST"]["critical_rate"], EMPH),
            ("Atropello a peatón", c["vulnerable"]["PEDESTRIAN"]["critical_rate"], EMPH)]
    fig, ax = plt.subplots(figsize=(8.2, 3.1))
    for i, (label, v, color) in enumerate(rows):
        ax.barh(i, v, height=0.5, color=color)
        extra = f"  ({num(v / base, 1)} veces la media)" if color == EMPH else ""
        ax.text(v + 0.002, i, pct(v) + extra, va="center", color=INK, fontsize=10.5)
    ax.set_yticks(range(3), [r[0] for r in rows])
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, max(r[1] for r in rows) * 1.6)
    heading(fig, "Peatones y ciclistas: el riesgo de lesión grave se multiplica", "Proporción de siniestros con fallecidos o lesiones incapacitantes")
    save(fig, "04_usuarios_vulnerables")


def fig_corredores(c: dict) -> None:
    top = c["corridors"][:8][::-1]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    vmax = max(t["critical"] for t in top)
    for i, t in enumerate(top):
        color = EMPH if i >= len(top) - 5 else GRAY
        ax.barh(i, t["critical"], height=0.6, color=color)
        ax.text(t["critical"] + vmax * 0.01, i, f"{t['critical']}  ·  {t['fatalities']} fallecidos",
                va="center", color=INK, fontsize=10)
    ax.set_yticks(range(len(top)), [t["street"].title() for t in top])
    ax.set_xticks([])
    ax.set_xlim(0, vmax * 1.4)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    heading(fig, "Cinco avenidas concentran la mayor cantidad de siniestros graves", "Siniestros con fallecidos o lesiones incapacitantes por vía (todo el periodo)")
    save(fig, "05_corredores")


def main() -> None:
    print("Figuras en", OUT)
    fig_captura_cuadras(json.loads((MODELS / "segment_model_report.json").read_text(encoding="utf-8")))
    rep = json.loads((MODELS / "model_report.json").read_text(encoding="utf-8"))
    fig_modelo_siniestro(rep)
    fig_calibracion(rep)
    if CIFRAS.exists():
        c = json.loads(CIFRAS.read_text(encoding="utf-8"))
        fig_velocidad(c)
        fig_vulnerables(c)
        fig_corredores(c)
    else:
        print(f"  (sin {CIFRAS}: se omiten las figuras de datos)")


if __name__ == "__main__":
    main()
