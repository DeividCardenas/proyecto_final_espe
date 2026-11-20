"""Póster completo (90 × 120 cm): cuenta la historia entera y deja el mapa grande para el stand.

    python docs/poster/generar_poster_completo.py

Recupera las secciones explicativas de los pósters anteriores (introducción, problema, objetivos,
metodología, resultados, hallazgos, conclusiones) con las cifras del reentrenamiento del 12 nov 2026.
El mapa queda reducido a una tarjeta que remite al mapa impreso del stand (60 × 80 cm).

Usa las figuras ya generadas en docs/poster/figuras_poster/ (no necesita los datos crudos).
Salida: docs/poster/poster_completo/Poster_Chicago_Road_Risk_completo.{pptx,pdf} y _preview.png.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIG = HERE / "figuras_poster"
OUT = HERE / "poster_completo"
NAME = "Poster_Chicago_Road_Risk_completo"

_spec = importlib.util.spec_from_file_location("gp", HERE / "generar_poster.py")
gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gp)
from pptx.dml.color import RGBColor  # noqa: E402

Poster, fmt, thousands, calle = gp.Poster, gp.fmt, gp.thousands, gp.calle
NAVY, INK, MUTED, TEAL, TEAL_SOFT = gp.NAVY, gp.INK, gp.MUTED, gp.TEAL, gp.TEAL_SOFT
ORANGE, ORANGE_SOFT, PANEL, WHITE, RULE, OK, BAD = (gp.ORANGE, gp.ORANGE_SOFT, gp.PANEL, gp.WHITE, gp.RULE,
                                                    gp.OK, gp.BAD)
W, H, M = gp.W, gp.H, gp.M
AQUA, LIGHT, ACC = RGBColor(0x7F, 0xD3, 0xDA), RGBColor(0xC9, 0xD6, 0xE0), RGBColor(0xF0, 0x8A, 0x45)
MAPBG = RGBColor(0x0B, 0x17, 0x22)


def fig_captura_poster(boot: dict, out: Path, w_cm: float, h_cm: float) -> None:
    """La gráfica de captura, dibujada al tamaño real del póster para que se lea a 2 m."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    INKc, MUTEDc, GRAYc, EMPHc, NAVYc = "#13212e", "#5b6b78", "#b4bec7", "#d9600f", "#0f3b57"
    plt.rcParams.update({"font.family": "Inter", "font.size": 24, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.spines.left": False, "axes.edgecolor": "#dfe5ea"})
    rows = [("Random Forest", "random_forest", GRAYc),
            ("Regla: más siniestros el año anterior", "historial_siniestros", NAVYc),
            ("XGBoost", "xgboost", GRAYc),
            ("Regresión logística (elegido)", "logistic_regression", EMPHc),
            ("Regla: más lesionados el año anterior", "historial_lesionados", GRAYc),
            ("Regla: más graves el año anterior", "historial_graves", GRAYc)]
    rows.sort(key=lambda r: boot[r[1]]["capture"])
    fig, ax = plt.subplots(figsize=(w_cm / 2.54, h_cm / 2.54))
    for i, (label, key, color) in enumerate(rows):
        c, (lo, hi) = boot[key]["capture"], boot[key]["ci95"]
        ax.plot([lo, hi], [i, i], color=color, lw=5, solid_capstyle="round", alpha=0.5)
        ax.plot(c, i, "o", ms=20, color=color, mec="white", mew=2.5, zorder=3)
        ax.text(hi + 0.012, i, fmt(c * 100) + " %", va="center", color=INKc, fontsize=26,
                fontweight="bold" if color != GRAYc else "normal")
    ax.axvline(0.10, color=MUTEDc, lw=2, ls=(0, (4, 4)))
    ax.text(0.108, len(rows) - 0.45, "al azar: 10 %", color=MUTEDc, fontsize=22, va="center")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    for t, r in zip(ax.get_yticklabels(), rows):
        t.set_color(INKc if r[2] != GRAYc else MUTEDc)
        t.set_fontweight("bold" if r[2] != GRAYc else "normal")
    ax.set_xlim(0, 0.56)
    ax.set_ylim(-0.6, len(rows) - 0.2)
    ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5], ["0 %", "10 %", "20 %", "30 %", "40 %", "50 %"])
    ax.tick_params(axis="y", length=0, pad=12)
    ax.tick_params(axis="x", colors=MUTEDc, labelsize=21)
    fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def build() -> None:
    OUT.mkdir(exist_ok=True)
    c = json.loads((ROOT / "docs/informe/cifras_informe.json").read_text(encoding="utf-8"))
    rep = json.loads((ROOT / "backend/app/ml/models/model_report.json").read_text(encoding="utf-8"))
    seg = json.loads((ROOT / "backend/app/ml/models/segment_model_report.json").read_text(encoding="utf-8"))
    td = rep["models"][rep["winner"]]["test_decision"]
    win = seg["models"][seg["winner"]]
    lr, scv = win["temporal_test"], win["spatial_cv"]
    boot = seg["bootstrap_top10_capture"]
    fc = seg["forecast"]
    sc = c["silver_counts"]
    q = c["quality_report"]["datasets"]["crashes"]
    cap = boot[seg["winner"]]["capture"]
    n_prio = int(fc["segments_scored"] * 0.10)  # 2.117, igual que el póster final

    P = Poster()
    cw = W - 2 * M

    # ------------------------------------------------------------------ cabecera (igual al póster final)
    HB = 14.0
    P.rect(0, 0, W, HB, NAVY)
    P.rect(M, 2.2, 21, 7.3, WHITE, radius=0.08)
    P.image(FIG / "logo.png", M + 0.8, 2.75, w=19.4)
    P.text(M, 10.3, 21, 1.4, "Especialización en Big Data", size=28, bold=True, color=AQUA, align=PP_ALIGN.CENTER)
    P.text(M, 11.75, 21, 1.2, "Sustentación final · noviembre 2026", size=22, color=LIGHT, align=PP_ALIGN.CENTER)
    tx = M + 21 + 3.0
    P.text(tx, 0.9, W - tx - M, 4.6, "Chicago Road Risk", size=120, bold=True, color=WHITE)
    P.text(tx, 7.0, W - tx - M, 3.0, "Big Data y modelado predictivo geoespacial para priorizar intervenciones "
           "de seguridad vial en la Ciudad de Chicago", size=29, color=RGBColor(0xDD, 0xE6, 0xEE))
    P.text(tx, 9.7, W - tx - M, 1.6, "Deivid Julian Cardenas Melo  ·  Dillan Alexander Cardenas Melo", size=28,
           bold=True, color=WHITE)
    P.text(tx, 11.8, W - tx - M, 1.3, "Universidad CESMAG · San Juan de Pasto, Colombia", size=24, color=LIGHT)

    # ------------------------------------------------------------------ hallazgo central + QR
    HY, HH = HB, 10.4
    P.rect(0, HY, W, HH, ORANGE_SOFT)
    qr_w = 7.2
    qx0 = W - M - 2 * qr_w - 1.6
    P.text(M, HY + 1.0, qx0 - M - 1.5, 7.0, [[("El ", {}), ("10 % de las cuadras", {"color": ORANGE}),
                                             (" concentra ", {}), ("4 de cada 10", {"color": ORANGE}),
                                             (" siniestros graves del año siguiente", {})]],
           size=70, bold=True, color=INK, spacing=0.93)
    P.text(M, HY + 7.5, qx0 - M - 1.5, 2.6,
           f"Validado con un año que el modelo nunca vio (nov 2025 – nov 2026): {fmt(cap * 100)} % de los graves "
           f"cayó en el 10 % de cuadras priorizadas ({fmt(cap * 10)} veces el azar).", size=24, color=MUTED)
    for i, (img, label) in enumerate([("qr_pagina.png", "Demo y capturas"), ("qr_informe.png", "Informe completo")]):
        x = qx0 + i * (qr_w + 1.6)
        P.rect(x - 0.3, HY + 0.7, qr_w + 0.6, qr_w + 0.6, WHITE, radius=0.05)
        P.image(FIG / img, x, HY + 1.0, w=qr_w)
        P.text(x - 0.6, HY + 1.0 + qr_w + 0.35, qr_w + 1.2, 1.3, label, size=21, bold=True, align=PP_ALIGN.CENTER)

    # ------------------------------------------------------------------ fila 1: problema, datos, objetivos
    # Una idea por sección; el título dice la conclusión; el dato va en grande y el texto en una línea.
    y0 = HY + HH + 1.3
    gap = 2.0
    c3 = (cw - 2 * gap) / 3
    x1, x2, x3 = M, M + c3 + gap, M + 2 * (c3 + gap)

    P.section(x1, y0, c3, 1, "El problema")
    P.text(x1, y0 + 3.0, c3, 3.4, "Los siniestros graves son pocos y dispersos; el presupuesto solo alcanza "
           "para algunos tramos.", size=28)
    kt = [(thousands(c["crashes"]["n"]), "siniestros", TEAL, PANEL),
          (str(c["crashes"]["fatalities"]), "fallecidos", ORANGE, ORANGE_SOFT),
          (f"{fmt(c['crashes']['critical_rate'] * 100)} %", "graves", TEAL, PANEL)]
    kw = (c3 - 2 * 0.8) / 3
    for i, (v, l, fg, bg) in enumerate(kt):
        kx = x1 + i * (kw + 0.8)
        P.rect(kx, y0 + 6.8, kw, 4.4, bg, radius=0.08)
        P.text(kx, y0 + 7.2, kw, 2.0, v, size=40, bold=True, color=fg, align=PP_ALIGN.CENTER)
        P.text(kx, y0 + 9.5, kw, 1.3, l, size=21, color=MUTED, align=PP_ALIGN.CENTER)
    P.rect(x1, y0 + 12.0, c3, 4.8, NAVY, radius=0.08)
    P.text(x1 + 1.0, y0 + 12.4, c3 - 2.0, 4.2,
           [[("Pregunta de decisión", {"size": 22, "bold": True, "color": AQUA})],
            [("¿Qué tramos intervenir primero?", {"size": 32, "bold": True})]], color=WHITE, after=6)

    P.section(x2, y0, c3, 2, "5 fuentes, 1 base")
    fuentes = [("Siniestros", sc["silver_crashes"]), ("Vehículos", sc["silver_vehicles"]),
               ("Personas (anónimas)", sc["silver_people"]), ("Permisos de obra", sc["silver_road_permits"]),
               ("Aforos vehiculares", sc["silver_traffic_counts"])]
    for i, (n, v) in enumerate(fuentes):
        ry = y0 + 3.2 + i * 2.15
        P.rect(x2, ry, c3, 2.0, PANEL if i % 2 == 0 else WHITE)
        P.text(x2 + 0.7, ry + 0.4, c3 - 1.4, 1.4, n, size=24)
        P.text(x2 + 0.7, ry + 0.3, c3 - 1.4, 1.5, thousands(v), size=28, bold=True, color=TEAL,
               align=PP_ALIGN.RIGHT)
    total = sum(v for _, v in fuentes)
    P.text(x2, y0 + 14.3, c3, 2.4, f"Chicago Data Portal · ene 2023 – nov 2026 · {fmt(total / 1e6)} millones "
           "de registros depurados", size=21, color=MUTED)

    P.section(x3, y0, c3, 3, "4 de 5 metas")
    metas = [("OE1", "Base geoespacial", "0 inválidas", True),
             ("OE2", "Depuración > 95 %", "98,9 %", True),
             ("OE3", "AUC ≥ 0,70", f"{fmt(lr['auc_roc_ovr_macro'], 2)} por cuadra", True),
             ("OE3", "Recall grave ≥ 0,60", fmt(td["recall_critical"], 2), False),
             ("OE4", "Respuesta < 2 s", "0,76 s", True)]
    for i, (oe, meta, res, ok) in enumerate(metas):
        ry = y0 + 3.2 + i * 2.7
        P.rect(x3, ry, c3, 2.5, PANEL if ok else ORANGE_SOFT, radius=0.08)
        P.text(x3 + 0.6, ry, 2.8, 2.5, oe, size=21, bold=True, color=TEAL, anchor=MSO_ANCHOR.MIDDLE)
        P.text(x3 + 3.6, ry, c3 - 9.0, 2.5, meta, size=23, anchor=MSO_ANCHOR.MIDDLE)
        P.text(x3 + c3 - 9.6, ry, 6.6, 2.5, res, size=22, bold=True, color=INK if ok else BAD,
               align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        P.text(x3 + c3 - 2.6, ry, 2.2, 2.5, "✓" if ok else "✗", size=30, bold=True, color=OK if ok else BAD,
               align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    row1_end = y0 + 17.4

    # ------------------------------------------------------------------ fila 2: metodología (solo el flujo)
    y1 = row1_end + 1.4
    P.section(M, y1, cw, 4, "Del dato abierto a la decisión")
    pipe = [("API SODA", "5 fuentes abiertas", "descarga incremental"),
            ("Bronze", "Parquet crudo", "copia fiel de la fuente"),
            ("Silver", "PostGIS", "limpieza, cruce a 250 m"),
            ("Gold", "DuckDB", "12 meses por cuadra"),
            ("Modelos", "Logística · RF · XGBoost", "validación temporal y espacial"),
            ("Aplicación", "FastAPI + React", "mapa con MapLibre")]
    ag = 1.3
    bw = (cw - 5 * ag) / 6
    by = y1 + 3.0
    for i, (t, s1, s2) in enumerate(pipe):
        bx = M + i * (bw + ag)
        hot = t == "Modelos"
        P.rect(bx, by, bw, 6.6, ORANGE if hot else NAVY, radius=0.08)
        P.text(bx, by + 0.6, bw, 1.8, t, size=32, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        P.text(bx + 0.4, by + 2.8, bw - 0.8, 1.5, s1, size=23, bold=True, color=WHITE if hot else AQUA,
               align=PP_ALIGN.CENTER)
        P.text(bx + 0.4, by + 4.4, bw - 0.8, 1.5, s2, size=22, color=WHITE if hot else LIGHT, align=PP_ALIGN.CENTER)
        if i < 5:
            a = P.s.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Cm(bx + bw + 0.35), Cm(by + 2.85), Cm(0.6), Cm(0.9))
            a.rotation = 90
            a.fill.solid()
            a.fill.fore_color.rgb = RGBColor(0x9A, 0xA7, 0xB2)
            a.line.fill.background()
            gp._no_style(a)
    row2_end = by + 6.6

    # ------------------------------------------------------------------ fila 3: resultados
    y3 = row2_end + 1.4
    hist = boot["historial_siniestros"]["capture"]
    P.section(M, y3, cw, 5, "Resultados: prioriza como el historial, y explica por qué")
    fig_w = 43.0
    P.text(M, y3 + 3.1, fig_w, 1.6, [[("Siniestros graves captados en el 10 % de cuadras priorizadas", {"bold": True}),
                                      ("   (línea = margen de error)", {"color": MUTED, "size": 21})]], size=25)
    fig_captura_poster(boot, OUT / "captura_poster.png", fig_w, 18.5)
    pic = P.image(OUT / "captura_poster.png", M, y3 + 5.0, w=fig_w)
    hy = y3 + 5.0 + pic.height / 360000 + 0.4
    P.text(M, hy, fig_w, 2.6,
           [[("Con honestidad: ", {"bold": True, "color": ORANGE}),
             (f"la regla «más siniestros el año anterior» capta {fmt(hist * 100)} % y el modelo {fmt(cap * 100)} %; "
              "el modelo suma la probabilidad y el porqué de cada cuadra.", {})]], size=23)
    res_end = hy + 2.6
    rx = M + fig_w + 2.0
    rw = W - M - rx
    km = [(fmt(lr["auc_roc_ovr_macro"], 2), "de acierto al ordenar cuadras por riesgo", "AUC · 0,5 = azar, 1 = perfecto",
           TEAL_SOFT, TEAL),
          (thousands(n_prio), "cuadras priorizadas para los próximos 12 meses", "el 10 % de 21.179 evaluadas",
           ORANGE_SOFT, ORANGE)]
    box_h = 6.4
    kh3 = (res_end - (y3 + 3.2) - 2 * 0.8 - box_h) / 2
    for i, (v, l, n, bg, fg) in enumerate(km):
        ky3 = y3 + 3.2 + i * (kh3 + 0.8)
        P.rect(rx, ky3, rw, kh3, bg, radius=0.06)
        P.text(rx + 1.2, ky3, 17.5, kh3, v, size=88, bold=True, color=fg, anchor=MSO_ANCHOR.MIDDLE)
        P.text(rx + 18.5, ky3, rw - 19.5, kh3, [l, [(n, {"size": 20, "color": MUTED})]], size=27,
               color=INK, anchor=MSO_ANCHOR.MIDDLE, after=6)
    py = y3 + 3.2 + 2 * (kh3 + 0.8)
    P.rect(rx, py, rw, res_end - py, PANEL, radius=0.06)
    P.text(rx + 1.2, py, rw - 2.4, res_end - py,
           [[("Y un segundo modelo, por siniestro", {"bold": True, "color": TEAL})],
            "Estima qué tan grave sería un choque según hora, clima, vía y tipo de choque. Alimenta el Simulador de la app."],
           size=24, after=6, anchor=MSO_ANCHOR.MIDDLE)

    # ------------------------------------------------------------------ fila 4: hallazgos
    y4 = res_end + 1.4
    P.section(M, y4, cw, 6, "Qué hace más grave un siniestro")
    vul = c["vulnerable"]["PEDESTRIAN"]["critical_rate"] / c["crashes"]["critical_rate"]
    sp = {s["mph"]: s["critical_rate"] for s in c["speed"]}
    wz = {w["active_workzone"]: w["critical_rate"] for w in c["workzone"]}
    cards = [("Peatones", f"{fmt(vul, 0)}×", "más lesiones graves en un atropello", ORANGE_SOFT, ORANGE),
             ("Velocidad", f"{fmt(sp[15] * 100)} → {fmt(sp[40] * 100)} %", "de graves, de 15 a 40 mph", ORANGE_SOFT, ORANGE),
             ("Corredores", "5 avenidas", "Western, Cicero, Pulaski, Halsted y Ashland", TEAL_SOFT, TEAL),
             ("Obras", "≈ igual", f"{fmt(wz[True] * 100, 1)} % con obra vs {fmt(wz[False] * 100, 1)} % sin obra", TEAL_SOFT, TEAL)]
    cw4 = (cw - 3 * 1.2) / 4
    for i, (t, v, d, bg, fg) in enumerate(cards):
        cx = M + i * (cw4 + 1.2)
        P.rect(cx, y4 + 3.0, cw4, 8.4, bg, radius=0.06)
        P.text(cx + 0.9, y4 + 3.6, cw4 - 1.8, 1.5, t, size=27, bold=True)
        P.text(cx + 0.9, y4 + 5.2, cw4 - 1.8, 2.6, v, size=58, bold=True, color=fg)
        P.text(cx + 0.9, y4 + 8.2, cw4 - 1.8, 2.6, d, size=23, color=MUTED)

    # ------------------------------------------------------------------ fila 5: conclusiones + puente al mapa
    y5 = y4 + 12.6
    foot_y = H - 3.2
    card_w = 38.0
    lw5 = cw - card_w - 2.0
    P.section(M, y5, lw5, 7, "Conclusiones")
    concl = [(f"≈ {fmt(cap * 100, 0)} %", "de los siniestros graves se cubre interviniendo el 10 % de cuadras.",
              ORANGE_SOFT, ORANGE),
             ("30 → 25", "mph y cruces peatonales protegidos: la medida con más respaldo.", ORANGE_SOFT, ORANGE),
             (fmt(td["recall_critical"], 2), "de recall en graves: el límite, justo bajo la meta de 0,60.", PANEL, BAD)]
    cg5 = 1.0
    cy5 = y5 + 3.2
    ch5 = (foot_y - 0.6 - cy5 - 2 * cg5) / 3
    for i, (v, d, bg, fg) in enumerate(concl):
        ry5 = cy5 + i * (ch5 + cg5)
        P.rect(M, ry5, lw5, ch5, bg, radius=0.08)
        P.text(M + 1.2, ry5, 15.5, ch5, v, size=60, bold=True, color=fg, anchor=MSO_ANCHOR.MIDDLE)
        P.text(M + 17.0, ry5, lw5 - 18.2, ch5, d, size=27, color=INK, anchor=MSO_ANCHOR.MIDDLE)

    kx = M + lw5 + 2.0
    ky = y5 + 0.2
    kh = foot_y - 0.6 - ky
    P.rect(kx, ky, card_w, kh, MAPBG, radius=0.04)
    from PIL import Image
    mimg = Image.open(FIG / "mapa_prioridad.png")
    mh = kh - 1.0
    mw = mh * mimg.width / mimg.height
    P.image(FIG / "mapa_prioridad.png", kx + 0.5, ky + 0.5, h=mh)
    tx2 = kx + 0.5 + mw + 0.6
    tw2 = kx + card_w - tx2 - 0.8
    P.text(tx2, ky + 0.9, tw2, 1.4, "Dónde intervenir primero", size=22, bold=True, color=AQUA)
    P.text(tx2, ky + 2.6, tw2, 2.8, thousands(n_prio), size=64, bold=True, color=ACC)
    P.text(tx2, ky + 5.4, tw2, 2.6, "cuadras priorizadas para los próximos 12 meses", size=21, color=WHITE)
    P.rect(tx2, ky + kh - 4.2, tw2, 3.4, ACC, radius=0.12)
    P.text(tx2, ky + kh - 4.2, tw2, 3.4, "Mapa completo y demo en el stand →", size=22, bold=True,
           color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # ------------------------------------------------------------------ referencias
    P.rect(0, foot_y, W, H - foot_y, PANEL)
    P.text(M, foot_y + 0.35, cw, H - foot_y - 0.5,
           "City of Chicago (2026). Traffic Crashes: Crashes, Vehicles y People; CDOT Permits [Datos]. Chicago Data Portal. · "
           "Chen, T. y Guestrin, C. (2016). XGBoost. Proc. KDD '16, 785–794. · Breiman, L. (2001). Random forests. "
           "Machine Learning, 45(1), 5–32. · Pedregosa, F. et al. (2011). Scikit-learn. JMLR, 12, 2825–2830. · "
           "Código: github.com/DeividCardenas/proyecto_final_espe",
           size=20, color=MUTED, spacing=1.1)
    print(f"fila1 {row1_end:.1f} · fila2 {row2_end:.1f} · resultados {res_end:.1f} · conclusiones {y5:.1f}–{foot_y - 0.6:.1f}")

    pptx_path = OUT / f"{NAME}.pptx"
    P.prs.save(pptx_path)
    pdf_filter = ('pdf:impress_pdf_Export:{"ReduceImageResolution":{"type":"boolean","value":"false"},'
                  '"Quality":{"type":"long","value":"95"}}')
    subprocess.run(["soffice", "--headless", "--convert-to", pdf_filter, "--outdir", str(OUT), str(pptx_path)],
                   check=True, capture_output=True)
    subprocess.run(["pdftoppm", "-png", "-r", "40", "-singlefile", str(OUT / f"{NAME}.pdf"),
                    str(OUT / f"{NAME}_preview")], check=True)
    print("Listo:", pptx_path)


if __name__ == "__main__":
    build()
