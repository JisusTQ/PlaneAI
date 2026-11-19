"""
Ejecuta el banco de 40 preguntas contra el asistente desplegado (OE3).

Paso 1 — correr el banco (usa la API, y por tanto la cuota de Gemini):
    python scripts/evaluar_asistente.py --api https://planeai.onrender.com
  Escribe docs/resultados/oe3_banco.csv con la respuesta, las fuentes y la
  precalificación automática. La columna `correcta` se llena con la sugerencia
  automática ("sí"/"no").

Paso 2 — el equipo revisa cada fila contra `respuesta_esperada` y corrige la
  columna `correcta` donde haga falta.

Paso 3 — calcular el indicador con la hoja revisada:
    python scripts/evaluar_asistente.py --resumen
  Escribe docs/resultados/oe3_banco.md.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import date
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from app.services import evaluacion_service as ev  # noqa: E402

CSV = RAIZ / "docs" / "resultados" / "oe3_banco.csv"
MD = RAIZ / "docs" / "resultados" / "oe3_banco.md"
CAMPOS = [
    "id", "categoria", "pregunta", "respuesta_esperada", "respuesta", "fuentes", "trazable", "claves_faltantes",
    "precalificacion", "correcta", "observacion", "latencia_ms", "herramientas",
]


def correr(api: str, pausa: float, desde: int) -> None:
    api = api.rstrip("/")
    filas = {}
    if CSV.exists():  # permite reanudar si se corta (p. ej. por límite de cuota)
        with CSV.open(encoding="utf-8") as f:
            filas = {int(r["id"]): r for r in csv.DictReader(f)}
    for p in ev.banco()["preguntas"]:
        if p["id"] < desde or (p["id"] in filas and filas[p["id"]]["respuesta"]):
            continue
        for intento in range(3):
            try:
                t0 = time.perf_counter()
                r = requests.post(f"{api}/evaluacion/banco/{p['id']}", timeout=180)
                latencia = round((time.perf_counter() - t0) * 1000)
                if r.status_code == 200:
                    break
                print(f"  {p['id']}: HTTP {r.status_code} {r.text[:120]}")
            except requests.RequestException as exc:
                print(f"  {p['id']}: {exc}")
            time.sleep(pausa * (intento + 2))
        else:
            print(f"Pregunta {p['id']} sin respuesta; se puede reanudar con --desde {p['id']}.")
            break
        d = r.json()
        filas[p["id"]] = {
            "id": p["id"],
            "categoria": p["categoria"],
            "pregunta": p["pregunta"],
            "respuesta_esperada": p["respuesta_esperada"],
            "respuesta": d["respuesta"].strip(),
            "fuentes": " | ".join(f"{f['titulo']} ({f['detalle']})" if f.get("detalle") else f["titulo"] for f in d["fuentes"]),
            "trazable": "sí" if d["trazable"] else "no",
            "claves_faltantes": "; ".join(d["claves_faltantes"]),
            "precalificacion": "sí" if d["auto_correcta"] else "no",
            "correcta": "sí" if d["auto_correcta"] else "no",
            "observacion": "",
            "latencia_ms": latencia,
            "herramientas": " > ".join(x.get("herramienta", "") for x in d.get("pasos", [])),
        }
        print(f"{p['id']:>2} {'OK ' if d['auto_correcta'] else 'REV'} {'traza' if d['trazable'] else 'SIN TRAZA'}  {p['pregunta'][:60]}")
        CSV.parent.mkdir(parents=True, exist_ok=True)
        with CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            w.writeheader()
            w.writerows(filas[k] for k in sorted(filas))
        time.sleep(pausa)


def resumir() -> None:
    with CSV.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    res = ev.resumen(
        [{"correcta": None if not r["correcta"].strip() else r["correcta"].strip().lower() in {"si", "sí"}, "trazable": r["trazable"] == "sí"} for r in filas]
    )
    por_cat = {}
    for cat in ("malla", "reglamento"):
        sub = [r for r in filas if r["categoria"] == cat]
        ok = sum(1 for r in sub if r["correcta"].strip().lower() in {"si", "sí"})
        por_cat[cat] = f"{ok}/{len(sub)}"
    malas = [f"- P{r['id']}: {r['pregunta']} — {r['observacion'] or 'faltó: ' + r['claves_faltantes']}" for r in filas if r["correcta"].strip().lower() not in {"si", "sí"}]
    extra = ""
    lat = sorted(int(r["latencia_ms"]) for r in filas if (r.get("latencia_ms") or "").strip().isdigit())
    if lat:
        p90 = lat[min(len(lat) - 1, int(round(0.9 * len(lat))) - 1)]
        mediana = (lat[len(lat) // 2] + lat[(len(lat) - 1) // 2]) / 2
        extra += f"| Latencia de extremo a extremo (mediana / p90 / máx.) | {mediana / 1000:.1f} s / {p90 / 1000:.1f} s / {lat[-1] / 1000:.1f} s | |\n"
    pre = [r for r in filas if (r.get("precalificacion") or "").strip()]
    if pre:
        coinciden = sum(1 for r in pre if (r["precalificacion"].strip().lower() in {"si", "sí"}) == (r["correcta"].strip().lower() in {"si", "sí"}))
        extra += f"| Precalificación automática que coincide con la revisión humana | {coinciden}/{len(pre)} | |\n"
    sin_traza = [f"- P{r['id']}: {r['pregunta']}" for r in filas if r["trazable"] != "sí"]
    md = f"""# OE3 — Banco de 40 preguntas del asistente

Revisión del {date.today().isoformat()} sobre `docs/resultados/oe3_banco.csv`.

| Indicador | Resultado | Meta |
|---|---|---|
| Preguntas evaluadas | {res['evaluadas']} de {res['preguntas']} | 40 |
| Respuestas correctas | **{res['porcentaje_correctas']} %** ({res['correctas']}) | ≥ 85 % |
| Respuestas con la fuente esperada | **{res['porcentaje_trazables']} %** | 100 % |
| Malla / Reglamento correctas | {por_cat['malla']} / {por_cat['reglamento']} | |
{extra}| Indicador del OE3 | {'Cumplido' if res['cumple_indicador'] else 'No cumplido aún'} | |

## Respuestas incorrectas
{chr(10).join(malas) or 'Ninguna.'}

## Respuestas sin la fuente esperada
{chr(10).join(sin_traza) or 'Ninguna.'}
"""
    MD.write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="https://planeai.onrender.com")
    ap.add_argument("--pausa", type=float, default=8.0, help="segundos entre preguntas (cuota gratuita de Gemini)")
    ap.add_argument("--desde", type=int, default=1)
    ap.add_argument("--resumen", action="store_true")
    a = ap.parse_args()
    resumir() if a.resumen else correr(a.api, a.pausa, a.desde)
