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

    # ------------------------------------------------------------------ fila 1: introducción, problema, objetivos
    y0 = HY + HH + 1.3
    gap = 2.0
    c3 = (cw - 2 * gap) / 3
    x1, x2, x3 = M, M + c3 + gap, M + 2 * (c3 + gap)

    P.section(x1, y0, c3, 1, "Introducción")
    P.text(x1, y0 + 3.0, c3, 6.4,
           "Chicago publica a diario sus siniestros viales, los permisos de obra y los aforos vehiculares. Son "
           "datos abiertos, pero viven en fuentes separadas, con errores de ubicación y sin cruzarse. Los "
           "integramos para responder una pregunta práctica: dónde conviene intervenir primero.", size=23)
    fuentes = [("Siniestros", sc["silver_crashes"]), ("Vehículos", sc["silver_vehicles"]),
               ("Personas (anonimizadas)", sc["silver_people"]), ("Permisos de obra CDOT", sc["silver_road_permits"]),
               ("Aforos vehiculares (AADT)", sc["silver_traffic_counts"])]
    ty = y0 + 9.8
    P.rect(x1, ty, c3, 1.6, TEAL)
    P.text(x1 + 0.6, ty + 0.25, c3 - 1.2, 1.2, "Fuente (Chicago Data Portal)", size=21, bold=True, color=WHITE)
    P.text(x1 + 0.6, ty + 0.25, c3 - 1.2, 1.2, "Registros", size=21, bold=True, color=WHITE, align=PP_ALIGN.RIGHT)
    for i, (n, v) in enumerate(fuentes):
        ry = ty + 1.6 + i * 1.5
        P.rect(x1, ry, c3, 1.5, PANEL if i % 2 == 0 else WHITE)
        P.text(x1 + 0.6, ry + 0.25, c3 - 1.2, 1.2, n, size=21)
        P.text(x1 + 0.6, ry + 0.25, c3 - 1.2, 1.2, thousands(v), size=21, bold=True, color=TEAL,
               align=PP_ALIGN.RIGHT)
    total = sum(v for _, v in fuentes)
    P.text(x1, ty + 1.6 + 5 * 1.5 + 0.4, c3, 1.2,
           f"Enero 2023 – noviembre 2026 · {fmt(total / 1e6)} millones de registros depurados", size=20, color=MUTED)
    row1_end = ty + 1.6 + 5 * 1.5 + 1.8

    P.section(x2, y0, c3, 2, "El problema")
    P.text(x2, y0 + 3.0, c3, 4.2,
           "En casi cuatro años la ciudad acumuló más de 424 mil siniestros. Los graves son pocos y están "
           "dispersos, y el presupuesto para reformar vías solo alcanza para algunos tramos.", size=23)
    kt = [(thousands(c["crashes"]["n"]), "siniestros", TEAL, PANEL),
          (str(c["crashes"]["fatalities"]), "fallecidos", ORANGE, ORANGE_SOFT),
          (f"{fmt(c['crashes']['critical_rate'] * 100)} %", "graves o fatales", TEAL, PANEL)]
    kw = (c3 - 2 * 0.8) / 3
    for i, (v, l, fg, bg) in enumerate(kt):
        kx = x2 + i * (kw + 0.8)
        P.rect(kx, y0 + 7.6, kw, 4.4, bg, radius=0.08)
        P.text(kx, y0 + 8.0, kw, 2.0, v, size=40, bold=True, color=fg, align=PP_ALIGN.CENTER)
        P.text(kx, y0 + 10.3, kw, 1.3, l, size=20, color=MUTED, align=PP_ALIGN.CENTER)
    P.rect(x2, y0 + 12.8, c3, 6.4, NAVY, radius=0.06)
    P.text(x2 + 1.0, y0 + 13.4, c3 - 2.0, 5.6,
           [[("Pregunta de decisión", {"size": 23, "bold": True, "color": AQUA})],
            "¿Cómo usar los resultados de un modelo predictivo para priorizar las intervenciones preventivas en "
            "los tramos viales de mayor riesgo?"], size=24, color=WHITE, after=4)

    P.section(x3, y0, c3, 3, "Objetivos")
    P.text(x3, y0 + 3.0, c3, 4.2,
           [[("General. ", {"bold": True}),
             ("Desarrollar una plataforma analítica que identifique y clasifique los tramos viales de mayor riesgo "
              "en Chicago, como apoyo a la toma de decisiones en seguridad vial.", {})]], size=23)
    oes = [("OE1", "Construir una base de datos geoespacial integrada.", "meta: + del 95 % de registros válidos indexados"),
           ("OE2", "Automatizar la integración y depuración de los datos.", "meta: + del 95 % procesado con éxito"),
           ("OE3", "Clasificar los segmentos viales por nivel de riesgo.", "meta: AUC ≥ 0,70 y recall ≥ 0,60"),
           ("OE4", "Visualizar los resultados en una aplicación web.", "meta: despliegue < 2 min, respuesta < 2 s")]
    for i, (oe, t, m) in enumerate(oes):
        oy = y0 + 7.6 + i * 2.95
        P.rect(x3, oy, 3.4, 2.6, TEAL_SOFT, radius=0.1)
        P.text(x3, oy, 3.4, 2.6, oe, size=22, bold=True, color=TEAL, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        P.text(x3 + 4.0, oy + 0.05, c3 - 4.0, 2.6, [t, [(m, {"size": 20, "color": MUTED})]], size=22, spacing=1.0)
    row1_end = max(row1_end, y0 + 7.6 + 4 * 2.95, y0 + 19.2)

    # ------------------------------------------------------------------ fila 2: metodología
    y1 = row1_end + 0.6
    P.section(M, y1, cw, 4, "Metodología: de los datos abiertos a la decisión")
    pipe = [("API SODA", "5 fuentes abiertas"), ("Bronze", "Parquet crudo"), ("Silver", "PostgreSQL + PostGIS"),
            ("Gold", "DuckDB (OLAP)"), ("Modelos", "Logística · RF · XGBoost"), ("Aplicación web", "FastAPI + React + MapLibre")]
    ag = 1.3
    bw = (cw - 5 * ag) / 6
    by = y1 + 3.0
    for i, (t, s) in enumerate(pipe):
        bx = M + i * (bw + ag)
        P.rect(bx, by, bw, 3.6, ORANGE if t == "Modelos" else NAVY, radius=0.08)
        P.text(bx, by + 0.4, bw, 1.5, t, size=26, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        P.text(bx, by + 2.0, bw, 1.3, s, size=20, color=WHITE if t == "Modelos" else LIGHT, align=PP_ALIGN.CENTER)
        if i < 5:
            a = P.s.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Cm(bx + bw + 0.35), Cm(by + 1.35), Cm(0.6), Cm(0.9))
            a.rotation = 90
            a.fill.solid()
            a.fill.fore_color.rgb = RGBColor(0x9A, 0xA7, 0xB2)
            a.line.fill.background()
            gp._no_style(a)
    cards = [("Datos y calidad",
              f"Descarga paginada con reintentos. Validación de tipos, {thousands(q['duplicates_removed'])} duplicados "
              f"quitados y {thousands(q['quarantined'])} puntos fuera de Chicago en cuarentena. Sin datos personales."),
             ("Integración espacial",
              "Cada siniestro se une a la estación de aforo más cercana y a las obras con cierre vigentes a menos de "
              "250 m, en metros reales (EPSG:3435)."),
             ("Modelado",
              f"La unidad es la cuadra ({thousands(fc['segments_scored'])}). Con 12 meses de historia se anticipa su "
              "riesgo de los 12 siguientes: Bajo, Medio o Alto. Tres algoritmos y reglas simples de comparación."),
             ("Validación",
              "Fuera de tiempo: se entrena con nov 2023 → nov 2025 y se evalúa con el año siguiente, que el modelo "
              f"nunca vio. Además, CV espacial por bloques de 2 km (AUC {fmt(scv['auc_mean'], 2)} ± "
              f"{fmt(scv['auc_std'], 2)}).")]
    cg = 1.2
    cwid = (cw - 3 * cg) / 4
    cy = by + 4.4
    for i, (t, d) in enumerate(cards):
        cx = M + i * (cwid + cg)
        P.rect(cx, cy, cwid, 8.4, PANEL, radius=0.05)
        P.text(cx + 0.8, cy + 0.5, cwid - 1.6, 1.4, t, size=24, bold=True, color=TEAL)
        P.text(cx + 0.8, cy + 2.0, cwid - 1.6, 6.2, d, size=21, spacing=1.05)
    row2_end = cy + 8.4

    # ------------------------------------------------------------------ fila 3: resultados
    y3 = row2_end + 1.0
    P.section(M, y3, cw, 5, "Resultados: dos modelos, dos preguntas")
    fig_w = 37.0
    hist = boot["historial_siniestros"]["capture"]
    P.text(M, y3 + 3.0, fig_w, 1.4, [[("MODELO PRINCIPAL · POR CUADRA   ", {"bold": True, "color": TEAL, "size": 21}),
                                      ("¿dónde intervenir primero?", {"color": MUTED, "size": 21})]])
    pic = P.image(FIG / "01_captura_top10_cuadras.png", M, y3 + 4.6, w=fig_w)
    hy = y3 + 4.6 + pic.height / 360000 + 0.4
    P.rect(M, hy, fig_w, 4.4, ORANGE_SOFT, radius=0.06)
    P.text(M + 0.9, hy + 0.4, fig_w - 1.8, 3.8,
           [[("Con honestidad: ", {"bold": True, "color": ORANGE}),
             (f"la regla «más siniestros el año anterior» capta {fmt(hist * 100)} %, un poco más que el modelo "
              f"({fmt(cap * 100)} %). El modelo aporta la probabilidad calibrada de cada cuadra y por qué es riesgosa.", {})]],
           size=21)
    res_end = hy + 4.4
    rx = M + fig_w + 2.0
    rw = W - M - rx
    # métricas del modelo por cuadra
    P.rect(rx, y3 + 3.0, rw, 5.6, TEAL_SOFT, radius=0.06)
    km = [(fmt(lr["auc_roc_ovr_macro"], 2), "AUC por cuadra"), (f"{fmt(lr['top10_lift'], 1)}×", "mejor que el azar"),
          (thousands(n_prio), "cuadras priorizadas")]
    kw2 = (rw - 2.0) / 3
    for i, (v, l) in enumerate(km):
        P.text(rx + 1.0 + i * kw2, y3 + 3.5, kw2, 2.2, v, size=44, bold=True, color=TEAL)
        P.text(rx + 1.0 + i * kw2, y3 + 5.9, kw2 - 0.4, 2.4, l, size=20, color=MUTED)
    # modelo complementario
    py = y3 + 9.3
    P.rect(rx, py, rw, 8.8, PANEL, radius=0.05)
    P.text(rx + 1.0, py + 0.5, rw - 2.0, 2.6,
           [[("MODELO COMPLEMENTARIO · POR SINIESTRO", {"bold": True, "color": TEAL, "size": 21})],
            [("¿qué tan grave sería un choque aquí, ahora?", {"color": MUTED, "size": 21})]])
    kp = [(fmt(td["auc_roc_ovr_macro"], 2), "AUC (XGBoost)"), (f"{fmt(td['lift'], 1)}×", "lift en casos graves"),
          (fmt(rep["models"][rep["winner"]]["calibration_critical"]["ece"], 3), "error de calibración")]
    for i, (v, l) in enumerate(kp):
        P.text(rx + 1.0 + i * kw2, py + 3.3, kw2, 2.0, v, size=40, bold=True, color=NAVY)
        P.text(rx + 1.0 + i * kw2, py + 5.3, kw2 - 0.4, 1.3, l, size=19, color=MUTED)
    abl = rep["ablation_pre_crash_only"]["auc_roc_ovr_macro"]
    P.text(rx + 1.0, py + 6.7, rw - 2.0, 2.0,
           f"Alimenta el Simulador. Solo con hora, clima, luz y vía el AUC baja a {fmt(abl, 2)}.", size=20)
    oy = py + 9.5
    rows = [("OE1", "Base geoespacial integrada", "0 geometrías inválidas", True),
            ("OE2", "Depuración > 95 %", "98,9 %", True),
            ("OE3", "AUC ≥ 0,70", f"{fmt(lr['auc_roc_ovr_macro'], 2)} cuadra · {fmt(td['auc_roc_ovr_macro'], 2)} siniestro", True),
            ("OE3", "Recall grave ≥ 0,60", f"{fmt(td['recall_critical'], 2)} siniestro · {fmt(lr['recall_high'], 2)} cuadra", False),
            ("OE4", "Despliegue < 2 min · < 2 s", "19 s · 0,76 s", True)]
    P.text(rx, oy, rw, 1.5, "Cumplimiento de objetivos", size=24, bold=True)
    for i, (oe, ind, res, ok) in enumerate(rows):
        ry = oy + 1.7 + i * 1.95
        P.rect(rx, ry, rw, 1.8, PANEL if i % 2 == 0 else WHITE)
        P.text(rx + 0.5, ry + 0.25, 2.8, 1.3, oe, size=20, bold=True, color=TEAL)
        P.text(rx + 3.2, ry + 0.25, 15.0, 1.3, ind, size=20)
        P.text(rx + 18.0, ry + 0.25, rw - 20.4, 1.3, res, size=20, color=MUTED)
        P.text(rx + rw - 2.0, ry + 0.05, 1.6, 1.6, "✓" if ok else "✗", size=26, bold=True,
               color=OK if ok else BAD, align=PP_ALIGN.CENTER)
    res_end = max(res_end, oy + 1.7 + 5 * 1.95)

    # ------------------------------------------------------------------ fila 4: hallazgos
    y4 = res_end + 0.9
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
        P.rect(cx, y4 + 3.0, cw4, 6.3, bg, radius=0.06)
        P.text(cx + 0.9, y4 + 3.5, cw4 - 1.8, 1.4, t, size=24, bold=True)
        P.text(cx + 0.9, y4 + 4.9, cw4 - 1.8, 2.3, v, size=44, bold=True, color=fg)
        P.text(cx + 0.9, y4 + 6.9, cw4 - 1.8, 2.3, d, size=20, color=MUTED)

    # ------------------------------------------------------------------ fila 5: conclusiones + puente al mapa
    y5 = y4 + 10.2
    foot_y = H - 3.2
    card_w = 33.0
    lw5 = cw - card_w - 2.0
    P.section(M, y5, lw5, 7, "Conclusiones")
    concl = [f"Intervenir el 10 % de cuadras priorizadas cubre cerca del {fmt(cap * 100, 0)} % de los siniestros "
             "graves del año siguiente.",
             "El historial reciente ya prioriza bien; el modelo suma la probabilidad calibrada y el porqué de cada cuadra.",
             "Lo más respaldado: bajar de 30 a 25 mph y proteger los cruces peatonales en las cuadras priorizadas.",
             f"Límite: el recall de la clase grave ({fmt(td['recall_critical'], 2)}) quedó bajo la meta; los graves "
             f"son el {fmt(c['crashes']['critical_rate'] * 100)} %."]
    step = (foot_y - 0.6 - (y5 + 3.0)) / 4
    for i, x in enumerate(concl):
        P.text(M, y5 + 3.0 + i * step, lw5, step, [[("•  ", {"color": ORANGE, "bold": True}), (x, {})]], size=23)

    # tarjeta oscura: del póster al mapa del stand
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
    P.text(tx2, ky + 5.4, tw2, 2.6, "cuadras priorizadas para los próximos 12 meses", size=20, color=WHITE)
    P.rect(tx2, ky + kh - 4.2, tw2, 3.4, ACC, radius=0.12)
    P.text(tx2, ky + kh - 4.2, tw2, 3.4, "Mapa completo y demo en vivo en el stand →", size=21, bold=True,
           color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # ------------------------------------------------------------------ referencias
    P.rect(0, foot_y, W, H - foot_y, PANEL)
    P.text(M, foot_y + 0.35, cw, H - foot_y - 0.5,
           "City of Chicago (2026). Traffic Crashes: Crashes, Vehicles y People; CDOT Permits [Datos]. Chicago Data Portal. · "
           "Chen, T. y Guestrin, C. (2016). XGBoost. Proc. KDD '16, 785–794. · Breiman, L. (2001). Random forests. "
           "Machine Learning, 45(1), 5–32. · Pedregosa, F. et al. (2011). Scikit-learn. JMLR, 12, 2825–2830. · "
           "Código: github.com/DeividCardenas/proyecto_final_espe",
           size=20, color=MUTED, spacing=1.1)
    print(f"fila1 {row1_end:.1f} · fila2 {row2_end:.1f} · resultados {res_end:.1f} · hallazgos {y4 + 9.3:.1f} · "
          f"conclusiones {y5:.1f}–{foot_y - 0.6:.1f} (paso {step:.2f})")

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
