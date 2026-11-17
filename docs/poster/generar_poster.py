"""Genera el póster final (90 × 120 cm) en PPTX y PDF.

    python docs/poster/generar_poster.py --datos <carpeta con crashes_puntos.csv.gz y gold_segment_risk.parquet>

Cifras: docs/informe/cifras_informe.json y backend/app/ml/models/*_report.json.
Salida: docs/poster/Poster_Chicago_Road_Risk_final.{pptx,pdf,png} y mapa_prioridad.png.

Principios aplicados (MIT CommLab, #betterposter):
* el hallazgo central se lee a 3 m, en una franja propia bajo el título;
* el mapa es la figura central (el proyecto es geoespacial);
* los títulos de sección dicen la conclusión;
* texto corto: cuerpo de 30 pt, nada por debajo de 20 pt;
* un solo color de énfasis (naranja) y el resto en navy, teal y gris;
* dos QR: la página del proyecto (demo y capturas) y el informe completo.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import qrcode  # noqa: E402
from PIL import Image  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN  # noqa: E402
from pptx.util import Cm, Pt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIGDIR = HERE / "figuras_poster"
NAME = "Poster_Chicago_Road_Risk_final"

PAGE_URL = "https://deividcardenas.github.io/proyecto_final_espe/"
INFORME_URL = "https://github.com/DeividCardenas/proyecto_final_espe/blob/master/docs/INFORME_RESULTADOS.md"

FONT = "Inter"  # libre (Google Fonts); el PDF la incrusta, para editar el PPTX instálela
NAVY, INK, MUTED = RGBColor(0x0F, 0x1F, 0x2E), RGBColor(0x13, 0x21, 0x2E), RGBColor(0x5B, 0x6B, 0x78)
TEAL, TEAL_SOFT = RGBColor(0x0B, 0x7A, 0x85), RGBColor(0xE3, 0xF2, 0xF3)
ORANGE, ORANGE_SOFT = RGBColor(0xD9, 0x60, 0x0F), RGBColor(0xFC, 0xEB, 0xDF)
PANEL, WHITE, RULE = RGBColor(0xF4, 0xF6, 0xF8), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xDF, 0xE5, 0xEA)
OK, BAD = RGBColor(0x1D, 0x7A, 0x46), RGBColor(0xB4, 0x23, 0x18)

W, H, M = 90.0, 120.0, 3.0  # cm


def fmt(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calle(s: str) -> str:
    """'0 W 87TH ST' -> '0 W 87th St'."""
    import re
    return re.sub(r"(\d)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), s.title())


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# --------------------------------------------------------------------------- figuras
def load_figuras_module():
    spec = importlib.util.spec_from_file_location("gf", ROOT / "docs" / "informe" / "generar_figuras.py")
    gf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gf)
    gf.OUT = FIGDIR
    gf.DPI = 400
    return gf


def mapa(datos: Path, seg_top: pd.DataFrame, out: Path) -> None:
    pts = pd.read_csv(datos / "crashes_puntos.csv.gz")
    fig = plt.figure(figsize=(9, 12), facecolor="#0b1722")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#0b1722")
    ax.scatter(pts["longitude"], pts["latitude"], s=0.5, c="#4fa3ad", alpha=0.30, linewidths=0, rasterized=True)
    ax.scatter(seg_top["lon"], seg_top["lat"], s=6 + 60 * seg_top["p_alto"] ** 2, c="#f08a45", alpha=0.85,
               linewidths=0, rasterized=True)
    top10 = seg_top.head(10)
    ax.scatter(top10["lon"], top10["lat"], s=520, facecolors="none", edgecolors="white", linewidths=2.2)
    placed: list[tuple[float, float]] = []
    for i, r in enumerate(top10.itertuples(), start=1):
        # Si ya hay una etiqueta muy cerca, esta va a la izquierda para que no se encimen
        near = any(abs(r.lon - x) < 0.02 and abs(r.lat - y) < 0.015 for x, y in placed)
        placed.append((r.lon, r.lat))
        ax.annotate(str(i), (r.lon, r.lat), xytext=(-30, -4) if near else (14, 10), textcoords="offset points",
                    color="white", fontsize=22, fontweight="bold", fontfamily="Inter",
                    ha="right" if near else "left")
    ax.set_xlim(pts["longitude"].quantile(0.0005) - 0.01, pts["longitude"].quantile(0.9995) + 0.01)
    ax.set_ylim(pts["latitude"].quantile(0.0005) - 0.005, pts["latitude"].quantile(0.9995) + 0.005)
    ax.set_aspect(1 / 0.745)  # cos(41,8°)
    ax.axis("off")
    fig.savefig(out, dpi=320, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def segmentos_alto(datos: Path) -> pd.DataFrame:
    df = pd.read_parquet(datos / "gold_segment_risk.parquet")
    cols = {c.lower(): c for c in df.columns}
    lon = next(cols[c] for c in ("lon", "longitude", "x", "centroid_lon") if c in cols)
    lat = next(cols[c] for c in ("lat", "latitude", "y", "centroid_lat") if c in cols)
    p = next(cols[c] for c in ("p_alto", "p_high", "prob_high", "p_riesgo_alto") if c in cols)
    sid = next(cols[c] for c in ("segment_id", "segmento", "cuadra") if c in cols)
    out = df.rename(columns={lon: "lon", lat: "lat", p: "p_alto", sid: "segment_id"})
    out = out.dropna(subset=["lon", "lat"]).sort_values("p_alto", ascending=False)
    return out.head(int(len(out) * 0.10))


def qr(url: str, out: Path) -> None:
    img = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1, box_size=20)
    img.add_data(url)
    img.make(fit=True)
    img.make_image(fill_color="#0f1f2e", back_color="white").save(out)


# --------------------------------------------------------------------------- PPTX helpers
def _no_style(shape) -> None:
    """Quita el estilo del tema (sombra y contorno) para un acabado plano."""
    st = shape._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if st is not None:
        shape._element.remove(st)

class Poster:
    def __init__(self) -> None:
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Cm(W), Cm(H)
        self.s = self.prs.slides.add_slide(self.prs.slide_layouts[6])

    def rect(self, x, y, w, h, fill, line=None, radius=None):
        shape = self.s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                        Cm(x), Cm(y), Cm(w), Cm(h))
        if radius:
            shape.adjustments[0] = radius
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        if line:
            shape.line.color.rgb = line
            shape.line.width = Pt(1.5)
        else:
            shape.line.fill.background()
        _no_style(shape)
        return shape

    def text(self, x, y, w, h, runs, size=30, color=INK, bold=False, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, spacing=1.08, after=0):
        """runs: str, o lista de párrafos; cada párrafo es str o lista de (texto, {opciones})."""
        tb = self.s.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        paras = runs if isinstance(runs, list) else [runs]
        for i, para in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.line_spacing = spacing
            p.space_after = Pt(after)
            for t, o in ([(para, {})] if isinstance(para, str) else para):
                r = p.add_run()
                r.text = t
                f = r.font
                f.name = FONT
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.color.rgb = o.get("color", color)
        return tb

    def image(self, path, x, y, w=None, h=None):
        return self.s.shapes.add_picture(str(path), Cm(x), Cm(y), Cm(w) if w else None, Cm(h) if h else None)

    def section(self, x, y, w, num, title, color=TEAL):
        c = self.s.shapes.add_shape(MSO_SHAPE.OVAL, Cm(x), Cm(y), Cm(2.2), Cm(2.2))
        c.fill.solid()
        c.fill.fore_color.rgb = color
        c.line.fill.background()
        _no_style(c)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(num)
        r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(36), True, FONT, WHITE
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        self.text(x + 3.0, y - 0.05, w - 3.0, 2.4, title, size=50, bold=True, color=INK, anchor=MSO_ANCHOR.MIDDLE)


# --------------------------------------------------------------------------- póster
def build(datos: Path) -> None:
    FIGDIR.mkdir(exist_ok=True)
    c = json.loads((ROOT / "docs" / "informe" / "cifras_informe.json").read_text(encoding="utf-8"))
    rep = json.loads((ROOT / "backend/app/ml/models/model_report.json").read_text(encoding="utf-8"))
    seg = json.loads((ROOT / "backend/app/ml/models/segment_model_report.json").read_text(encoding="utf-8"))
    td = rep["models"][rep["winner"]]["test_decision"]
    lr = seg["models"][seg["winner"]]["temporal_test"]
    boot = seg["bootstrap_top10_capture"]
    fc = seg["forecast"]

    gf = load_figuras_module()
    gf.fig_captura_cuadras(seg)
    gf.fig_velocidad(c)

    top = segmentos_alto(datos)
    mapa(datos, top, FIGDIR / "mapa_prioridad.png")
    qr(PAGE_URL, FIGDIR / "qr_pagina.png")
    qr(INFORME_URL, FIGDIR / "qr_informe.png")
    logo = Image.open(HERE / "logo_cesmag.jpg").convert("RGB")
    from PIL import ImageDraw
    ImageDraw.Draw(logo).rectangle((430, 300, logo.width, logo.height), fill="white")  # sin NIT ni «Vigilada»
    logo.crop((0, 0, logo.width, logo.height)).save(FIGDIR / "logo.png")

    P = Poster()
    cw = W - 2 * M

    # ---- Cabecera
    HB = 14.0
    P.rect(0, 0, W, HB, NAVY)
    P.rect(M, 2.2, 21, 7.3, WHITE, radius=0.08)
    P.image(FIGDIR / "logo.png", M + 0.8, 2.75, w=19.4)
    P.text(M, 10.3, 21, 1.4, "Especialización en Big Data", size=28, bold=True, color=RGBColor(0x7F, 0xD3, 0xDA),
           align=PP_ALIGN.CENTER)
    P.text(M, 11.75, 21, 1.2, "Sustentación final · noviembre 2026", size=22, color=RGBColor(0xC9, 0xD6, 0xE0),
           align=PP_ALIGN.CENTER)
    tx = M + 21 + 3.0
    P.text(tx, 0.9, W - tx - M, 4.6, "Chicago Road Risk", size=120, bold=True, color=WHITE)
    P.text(tx, 7.0, W - tx - M, 3.0, "Big Data y modelado predictivo geoespacial para priorizar intervenciones "
           "de seguridad vial en la Ciudad de Chicago", size=29, color=RGBColor(0xDD, 0xE6, 0xEE))
    P.text(tx, 9.7, W - tx - M, 1.6, "Deivid Julian Cardenas Melo  ·  Dillan Alexander Cardenas Melo", size=28, bold=True, color=WHITE)
    P.text(tx, 11.8, W - tx - M, 1.3, "Universidad CESMAG · San Juan de Pasto, Colombia", size=24,
           color=RGBColor(0xC9, 0xD6, 0xE0))

    # ---- Hallazgo central (legible a 3 m) + QR
    HY, HH = HB, 11.2
    P.rect(0, HY, W, HH, ORANGE_SOFT)
    cap = boot[seg["winner"]]["capture"]
    qr_w = 7.8
    qx0 = W - M - 2 * qr_w - 1.6
    P.text(M, HY + 1.2, qx0 - M - 1.5, 7.4, [[("El ", {}), ("10 % de las cuadras", {"color": ORANGE}),
                                             (" concentra ", {}), ("4 de cada 10", {"color": ORANGE}),
                                             (" siniestros graves del año siguiente", {})]],
           size=74, bold=True, color=INK, spacing=0.93)
    P.text(M, HY + 8.1, qx0 - M - 1.5, 2.8,
           f"Validado con un año que el modelo nunca vio (nov 2025 – nov 2026): {fmt(cap * 100)} % de los graves "
           f"cayó en el 10 % de cuadras priorizadas ({fmt(cap * 10)} veces el azar).",
           size=25, color=MUTED)
    for i, (img, label) in enumerate([("qr_pagina.png", "Demo y capturas"), ("qr_informe.png", "Informe completo")]):
        x = qx0 + i * (qr_w + 1.6)
        P.rect(x - 0.3, HY + 0.9, qr_w + 0.6, qr_w + 0.6, WHITE, radius=0.05)
        P.image(FIGDIR / img, x, HY + 1.2, w=qr_w)
        P.text(x - 0.6, HY + 1.2 + qr_w + 0.45, qr_w + 1.2, 1.3, label, size=22, bold=True, align=PP_ALIGN.CENTER)

    # ---- Columna izquierda: problema, datos, método
    y0, lw = HY + HH + 1.6, 27.5
    P.section(M, y0, lw, 1, "El problema")
    P.text(M, y0 + 3.0, lw, 5.0,
           f"En casi cuatro años Chicago registró {thousands(c['crashes']['n'])} siniestros y "
           f"{c['crashes']['fatalities']} fallecidos. Los graves son pocos (1,6 %) y están dispersos; el "
           "presupuesto para reformar vías solo alcanza para algunos tramos.", size=25)
    P.rect(M, y0 + 8.6, lw, 5.6, NAVY, radius=0.06)
    P.text(M + 1.0, y0 + 9.1, lw - 2.0, 4.8,
           [[("Pregunta de decisión", {"size": 24, "bold": True, "color": RGBColor(0x7F, 0xD3, 0xDA)})],
            "¿Cómo usar un modelo predictivo para priorizar intervenciones preventivas en los tramos de mayor riesgo?"],
           size=24, color=WHITE, after=4)

    y1 = y0 + 15.1
    P.section(M, y1, lw, 2, "Datos abiertos integrados")
    tiles = [(thousands(c["silver_counts"]["silver_crashes"]), "siniestros"),
             (thousands(c["silver_counts"]["silver_people"]), "personas (anonimizadas)"),
             (thousands(c["silver_counts"]["silver_vehicles"]), "vehículos"),
             (thousands(c["silver_counts"]["silver_road_permits"]), "permisos de obra")]
    tw = (lw - 1.0) / 2
    for i, (v, l) in enumerate(tiles):
        tx_, ty = M + (i % 2) * (tw + 1.0), y1 + 3.0 + (i // 2) * 4.1
        P.rect(tx_, ty, tw, 3.7, PANEL, radius=0.08)
        P.text(tx_ + 0.8, ty + 0.25, tw - 1.6, 1.9, v, size=42, bold=True, color=TEAL)
        P.text(tx_ + 0.8, ty + 2.15, tw - 1.6, 1.4, l, size=21, color=MUTED)
    P.text(M, y1 + 11.4, lw, 1.3, "Chicago Data Portal (API SODA) · enero 2023 – noviembre 2026", size=20,
           color=MUTED)

    y2 = y1 + 13.2
    P.section(M, y2, lw, 3, "Cómo se hizo")
    steps = [("Bronze", "descarga incremental de 5 fuentes"),
             ("Silver", "PostGIS: depuración, cuarentena y anonimización"),
             ("Integración", "aforo más cercano y obras a 250 m"),
             ("Gold", "DuckDB y variables de 12 meses por cuadra"),
             ("Modelos", "logística, RF y XGBoost; validación temporal y espacial"),
             ("Aplicación", "FastAPI + React + MapLibre GL JS")]
    for i, (a, b) in enumerate(steps):
        sy = y2 + 3.0 + i * 1.95
        P.rect(M, sy + 0.1, 0.45, 1.8, ORANGE if a == "Modelos" else TEAL)
        P.text(M + 1.1, sy, lw - 1.1, 2.2, [[(a + "  ", {"bold": True}), (b, {"color": MUTED})]], size=23)
    body_end = y2 + 3.0 + 6 * 1.95

    # ---- Columna derecha: mapa
    mx = M + lw + 2.0
    mw = W - M - mx
    P.section(mx, y0, mw, 4, "Dónde intervenir primero", color=ORANGE)
    map_h = body_end - (y0 + 3.0)
    P.rect(mx, y0 + 3.0, mw, map_h, RGBColor(0x0B, 0x17, 0x22), radius=0.03)
    mimg = Image.open(FIGDIR / "mapa_prioridad.png")
    img_w = (map_h - 1.0) * mimg.width / mimg.height
    P.image(FIGDIR / "mapa_prioridad.png", mx + 0.5, y0 + 3.5, h=map_h - 1.0)
    lx = mx + 0.5 + img_w + 0.5
    lw2 = mx + mw - lx - 0.8
    LIGHT, ACC, AQUA = RGBColor(0xC9, 0xD6, 0xE0), RGBColor(0xF0, 0x8A, 0x45), RGBColor(0x7F, 0xD3, 0xDA)
    top_y, bot_y = y0 + 4.4, y0 + 3.0 + map_h - 1.0
    P.text(lx, top_y, lw2, 3.6, thousands(len(top)), size=96, bold=True, color=ACC)
    P.text(lx, top_y + 4.3, lw2, 3.4, "cuadras priorizadas: el 10 % con mayor probabilidad de riesgo Alto en los "
           "próximos 12 meses", size=24, color=WHITE)
    P.rect(lx, top_y + 8.2, lw2, 0.08, RGBColor(0x2A, 0x3D, 0x4D))
    P.text(lx, top_y + 8.6, lw2, 1.6, "Las 10 primeras", size=26, bold=True, color=AQUA)
    P.text(lx, top_y + 8.75, lw2, 1.4, "P(Alto)", size=20, color=LIGHT, align=PP_ALIGN.RIGHT)
    legend_h = 5.2
    row0 = top_y + 10.7
    step = (bot_y - legend_h - row0) / 10
    for i, t in enumerate(fc["top10"], start=1):
        ry = row0 + (i - 1) * step
        if i % 2 == 1:
            P.rect(lx - 0.3, ry - 0.25, lw2 + 0.6, step - 0.05, RGBColor(0x12, 0x22, 0x31), radius=0.15)
        P.text(lx, ry, lw2 - 4.0, step,
               [[(f"{i:>2}   ", {"bold": True, "color": ACC}), (calle(t["segment_id"]), {})]], size=23, color=WHITE)
        P.text(lx + lw2 - 4.0, ry, 4.0, step, f"{round(t['p_alto'] * 100)} %", size=23, bold=True,
               color=LIGHT, align=PP_ALIGN.RIGHT)
    P.text(lx, bot_y - legend_h + 0.6, lw2, legend_h,
           [[("● ", {"color": ACC}), ("cuadra priorizada (mayor = más probable)", {})],
            [("● ", {"color": RGBColor(0x4F, 0xA3, 0xAD)}), ("siniestro 2023–2026", {})],
            [("○ ", {"color": WHITE}), ("las 10 primeras, numeradas", {})]],
           size=21, color=LIGHT, after=5)

    # ---- Resultados
    y3 = body_end + 1.3
    P.section(M, y3, cw, 5, "Resultados: el riesgo de una cuadra persiste año a año")
    fig_w = 38.0
    pic = P.image(FIGDIR / "01_captura_top10_cuadras.png", M, y3 + 3.0, w=fig_w)
    res_end = y3 + 3.0 + pic.height / 360000
    rx = M + fig_w + 2.0
    rw = W - M - rx
    P.rect(rx, y3 + 3.0, rw, 6.0, ORANGE_SOFT, radius=0.05)
    hist = boot["historial_siniestros"]["capture"]
    P.text(rx + 1.0, y3 + 3.5, rw - 2.0, 5.2,
           [[("Con honestidad", {"bold": True, "color": ORANGE, "size": 26})],
            f"La regla «más siniestros el año anterior» capta {fmt(hist * 100)} %, un poco más que el modelo "
            f"({fmt(cap * 100)} %). El modelo aporta la probabilidad calibrada de cada cuadra y por qué es riesgosa."],
           size=23, after=4)
    rows = [("OE1", "Base geoespacial integrada", "0 geometrías inválidas", True),
            ("OE2", "Depuración > 95 %", "98,9 %", True),
            ("OE3", "AUC ≥ 0,70", f"{fmt(lr['auc_roc_ovr_macro'], 2)} cuadra · {fmt(td['auc_roc_ovr_macro'], 2)} siniestro", True),
            ("OE3", "Recall grave ≥ 0,60", f"{fmt(td['recall_critical'], 2)} siniestro · {fmt(lr['recall_high'], 2)} cuadra", False),
            ("OE4", "Despliegue < 2 min · < 2 s", "19 s · 0,76 s", True)]
    P.text(rx, y3 + 10.0, rw, 1.5, "Cumplimiento de objetivos", size=24, bold=True)
    for i, (oe, ind, res, ok) in enumerate(rows):
        ry = y3 + 11.7 + i * 2.1
        P.rect(rx, ry, rw, 1.95, PANEL if i % 2 == 0 else WHITE)
        P.text(rx + 0.5, ry + 0.25, 2.8, 1.3, oe, size=20, bold=True, color=TEAL)
        P.text(rx + 3.2, ry + 0.25, 13.0, 1.3, ind, size=20)
        P.text(rx + 16.0, ry + 0.25, rw - 18.4, 1.3, res, size=20, color=MUTED)
        P.text(rx + rw - 2.0, ry + 0.05, 1.6, 1.6, "✓" if ok else "✗", size=26, bold=True,
               color=OK if ok else BAD, align=PP_ALIGN.CENTER)
    res_end = max(res_end, y3 + 11.7 + 5 * 2.1)

    # ---- Hallazgos para la ciudad
    y4 = res_end + 1.0
    P.section(M, y4, cw, 6, "Hallazgos para la ciudad")
    vul = c["vulnerable"]["PEDESTRIAN"]["critical_rate"] / c["crashes"]["critical_rate"]
    sp = {s["mph"]: s["critical_rate"] for s in c["speed"]}
    wz = {w["active_workzone"]: w["critical_rate"] for w in c["workzone"]}
    corr = ", ".join(x["street"].title() for x in c["corridors"][:5])
    cards = [("Peatones", f"{fmt(vul, 0)}×", f"un atropello termina en lesión grave {fmt(vul, 0)} veces más que la media", ORANGE_SOFT, ORANGE),
             ("Velocidad", f"{fmt(sp[15] * 100)} → {fmt(sp[40] * 100)} %", "de siniestros graves, de 15 a 40 mph", ORANGE_SOFT, ORANGE),
             ("Corredores", "5 avenidas", corr, TEAL_SOFT, TEAL),
             ("Obras", "≈ igual", f"con cierre de calzada no aumentan la gravedad ({fmt(wz[True] * 100, 2)} % vs {fmt(wz[False] * 100, 2)} %)", TEAL_SOFT, TEAL)]
    cw4 = (cw - 3 * 1.2) / 4
    for i, (t, v, d, bg, fg) in enumerate(cards):
        cx = M + i * (cw4 + 1.2)
        P.rect(cx, y4 + 3.0, cw4, 6.8, bg, radius=0.06)
        P.text(cx + 0.9, y4 + 3.5, cw4 - 1.8, 1.4, t, size=24, bold=True)
        P.text(cx + 0.9, y4 + 4.9, cw4 - 1.8, 2.3, v, size=44, bold=True, color=fg)
        P.text(cx + 0.9, y4 + 7.1, cw4 - 1.8, 2.6, d, size=20, color=MUTED)

    # ---- Conclusiones
    y5 = y4 + 10.9
    P.section(M, y5, cw, 7, "Conclusiones")
    concl = ["Intervenir el 10 % de cuadras priorizadas cubre cerca del 42 % de los siniestros graves del año siguiente.",
             "El historial reciente ya prioriza bien; el modelo suma la probabilidad calibrada y el porqué de cada cuadra.",
             "Lo más respaldado: bajar de 30 a 25 mph y proteger los cruces peatonales en las cuadras priorizadas.",
             f"Límite: el recall de la clase grave ({fmt(td['recall_critical'], 2)}) quedó bajo la meta; los graves son el 1,6 %."]
    half = (cw - 2.0) / 2
    for i, x in enumerate(concl):
        P.text(M + (i % 2) * (half + 2.0), y5 + 3.0 + (i // 2) * 3.0, half, 3.0,
               [[("•  ", {"color": ORANGE, "bold": True}), (x, {})]], size=24)

    # ---- Referencias
    P.rect(0, H - 4.0, W, 4.0, PANEL)
    P.text(M, H - 3.5, cw, 3.0,
           "City of Chicago (2026). Traffic Crashes: Crashes, Vehicles y People; CDOT Permits [Datos]. Chicago Data Portal. · "
           "Chen, T. y Guestrin, C. (2016). XGBoost. Proc. KDD '16, 785–794. · Breiman, L. (2001). Random forests. "
           "Machine Learning, 45(1), 5–32. · Pedregosa, F. et al. (2011). Scikit-learn. JMLR, 12, 2825–2830. · "
           "Código: github.com/DeividCardenas/proyecto_final_espe",
           size=20, color=MUTED, spacing=1.1)
    print(f"  fin del contenido: {y5 + 3.0 + 2 * 3.0:.1f} cm (referencias desde {H - 4.0:.1f} cm)")

    pptx_path = HERE / f"{NAME}.pptx"
    P.prs.save(pptx_path)
    pdf_filter = ('pdf:impress_pdf_Export:{"ReduceImageResolution":{"type":"boolean","value":"false"},'
                  '"Quality":{"type":"long","value":"95"}}')
    subprocess.run(["soffice", "--headless", "--convert-to", pdf_filter, "--outdir", str(HERE), str(pptx_path)],
                   check=True, capture_output=True)
    subprocess.run(["pdftoppm", "-png", "-r", "40", "-singlefile", str(HERE / f"{NAME}.pdf"),
                    str(HERE / f"{NAME}_preview")], check=True)
    print("Listo:", pptx_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, required=True)
    build(ap.parse_args().datos)
