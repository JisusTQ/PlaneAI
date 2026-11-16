"""
Análisis de la evaluación de usabilidad SUS (OE4).

Indicador OE4: puntaje SUS ≥ 68 (Brooke, 1996) con al menos 15 estudiantes, y
reporte de hallazgos con acciones de mejora.

Uso (desde backend/):
    python scripts/analizar_sus.py ruta/planeai-sus.csv [otro.csv ...]
Acepta uno o varios CSV exportados desde la vista Evaluación → Resultados
(columnas participante, fecha, p1..p10, puntaje_sus, comentario); elimina
duplicados y recalcula cada puntaje desde los ítems.
Salida: docs/resultados/oe4_sus.md y oe4_sus.json
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "resultados"
META, MIN_PARTICIPANTES = 68, 15

ITEMS = [
    "Me gustaría usar PlaneAI con frecuencia.",
    "Encontré PlaneAI innecesariamente complejo.",
    "PlaneAI fue fácil de usar.",
    "Necesitaría apoyo técnico para usar PlaneAI.",
    "Las funciones de PlaneAI están bien integradas.",
    "Hay demasiada inconsistencia en PlaneAI.",
    "La mayoría aprendería a usar PlaneAI rápido.",
    "PlaneAI es muy engorroso de usar.",
    "Me sentí seguro usando PlaneAI.",
    "Necesité aprender mucho antes de usar PlaneAI.",
]
# Valores críticos t de Student (dos colas, 95 %) para gl = 1..30.
T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
       2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def puntaje(r: list[int]) -> float:
    return 2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(r))


def adjetivo(p: float) -> str:
    """Escala adjetiva de Bangor, Kortum y Miller (2009)."""
    if p >= 85.5:
        return "Excelente"
    if p >= 71.4:
        return "Bueno"
    if p >= 50.9:
        return "Aceptable (OK)"
    if p >= 35.7:
        return "Pobre"
    return "Muy pobre"


def leer(rutas: list[str]) -> list[dict]:
    vistos, filas = set(), []
    for ruta in rutas:
        with open(ruta, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                try:
                    resp = [int(r[f"p{i}"]) for i in range(1, 11)]
                except (KeyError, ValueError):
                    continue
                if not all(1 <= x <= 5 for x in resp):
                    continue
                clave = (r.get("participante", ""), r.get("fecha", ""), tuple(resp))
                if clave in vistos:
                    continue
                vistos.add(clave)
                filas.append({"participante": r.get("participante", ""), "respuestas": resp, "puntaje": puntaje(resp), "comentario": (r.get("comentario") or "").strip()})
    return filas


def analizar(filas: list[dict]) -> dict:
    p = [f["puntaje"] for f in filas]
    n = len(p)
    media = statistics.mean(p) if p else 0.0
    de = statistics.stdev(p) if n > 1 else 0.0
    t = T95[min(n - 1, 30) - 1] if n > 1 and n <= 31 else 1.96
    margen = t * de / n**0.5 if n > 1 else 0.0
    items = [round(statistics.mean(f["respuestas"][i] for f in filas), 2) if filas else 0 for i in range(10)]
    contrib = [round(statistics.mean(((f["respuestas"][i] - 1) if i % 2 == 0 else (5 - f["respuestas"][i])) for f in filas), 2) if filas else 0 for i in range(10)]
    return {
        "n": n,
        "media": round(media, 1),
        "desviacion": round(de, 1),
        "mediana": round(statistics.median(p), 1) if p else 0,
        "minimo": min(p, default=0),
        "maximo": max(p, default=0),
        "ic95": [round(media - margen, 1), round(media + margen, 1)],
        "sobre_meta": sum(1 for x in p if x >= META),
        "adjetivo": adjetivo(media),
        "items_media": items,
        "items_contribucion": contrib,
        "cumple_indicador": n >= MIN_PARTICIPANTES and media >= META,
        "comentarios": [f["comentario"] for f in filas if f["comentario"]],
    }


def main(rutas: list[str]) -> None:
    filas = leer(rutas)
    a = analizar(filas)
    a["fecha"] = date.today().isoformat()
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "oe4_sus.json").write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    debiles = sorted(range(10), key=lambda i: a["items_contribucion"][i])[:3]
    tabla_items = "\n".join(f"| {i + 1} | {ITEMS[i]} | {a['items_media'][i]} | {a['items_contribucion'][i]} / 4 |" for i in range(10))
    md = f"""# OE4 — Evaluación de usabilidad (SUS)

Análisis del {a['fecha']} con `backend/scripts/analizar_sus.py` sobre {len(rutas)} archivo(s) CSV.

| Indicador | Resultado | Meta |
|---|---|---|
| Participantes | {a['n']} | ≥ {MIN_PARTICIPANTES} |
| Puntaje SUS promedio | **{a['media']}** (IC 95 %: {a['ic95'][0]}–{a['ic95'][1]}) | ≥ {META} |
| Desviación estándar / mediana | {a['desviacion']} / {a['mediana']} | |
| Rango | {a['minimo']}–{a['maximo']} | |
| Participantes con puntaje ≥ {META} | {a['sobre_meta']} de {a['n']} | |
| Calificación adjetiva (Bangor et al., 2009) | {a['adjetivo']} | |
| Indicador del OE4 | {'Cumplido' if a['cumple_indicador'] else 'No cumplido aún'} | |

## Resultados por ítem

La contribución va de 0 a 4 (4 es la mejor percepción, ya invertida para los ítems negativos pares).

| # | Afirmación | Media (1–5) | Contribución |
|---|---|---|---|
{tabla_items}

Ítems con menor contribución (prioridades de mejora): {', '.join(f'{i + 1} ({ITEMS[i]})' for i in debiles) if a['n'] else '—'}.

## Comentarios de los participantes

{chr(10).join('- ' + c for c in a['comentarios']) or 'Sin comentarios.'}

## Hallazgos y acciones de mejora

> Completar por el equipo a partir de los ítems más débiles, los comentarios y las observaciones de las sesiones guiadas.

| Hallazgo | Evidencia | Acción de mejora | Prioridad |
|---|---|---|---|
| | | | |
"""
    (SALIDA / "oe4_sus.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/analizar_sus.py planeai-sus.csv [otro.csv ...]")
    main(sys.argv[1:])
