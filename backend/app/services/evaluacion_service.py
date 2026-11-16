"""
Banco de 40 preguntas y calificación asistida de las respuestas del asistente.  [OE3]

Indicador OE3: ≥ 85 % de respuestas correctas en un banco de 40 preguntas sobre la
malla y el reglamento, con trazabilidad a la fuente en todas las respuestas.

La calificación automática es una AYUDA para el evaluador humano:
  - `claves`: datos que una respuesta correcta debe mencionar (alternativas con "|").
  - `trazable`: la respuesta trae fuentes y entre ellas está la esperada
    (para el reglamento, el artículo exacto).
El equipo confirma o corrige cada veredicto antes de reportar el indicador.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.services.udea_horarios_service import normalizar

BANCO = Path(__file__).resolve().parent.parent / "data" / "banco_preguntas.json"


@lru_cache
def banco() -> dict:
    return json.loads(BANCO.read_text(encoding="utf-8"))


def pregunta(id_: int) -> dict | None:
    return next((p for p in banco()["preguntas"] if p["id"] == id_), None)


def _contiene(texto: str, alternativa: str) -> bool:
    alt = normalizar(alternativa)
    if len(alt) <= 3:  # "no", "24", "dos": como palabra completa
        return re.search(rf"(?<![\w.,]){re.escape(alt)}(?![\w]|[.,]\d)", texto) is not None
    return alt in texto


def calificar(p: dict, respuesta: str, fuentes: list[dict]) -> dict:
    texto = normalizar(respuesta or "")
    faltantes = [c for c in p["claves"] if not any(_contiene(texto, a) for a in c.split("|"))]

    esperada = p["fuente_esperada"]
    tipos = {f.get("tipo") for f in fuentes}
    detalle_ok = True
    if esperada["tipo"] == "reglamento" and esperada["detalle"]:
        art = normalizar(esperada["detalle"])
        detalle_ok = any(art in normalizar(f.get("detalle", "")) for f in fuentes if f.get("tipo") == "reglamento")
    trazable = bool(fuentes) and esperada["tipo"] in tipos and detalle_ok
    cita_en_texto = "fuente" in texto

    return {
        "auto_correcta": not faltantes,
        "claves_faltantes": faltantes,
        "trazable": trazable,
        "cita_en_texto": cita_en_texto,
    }


def resumen(resultados: list[dict]) -> dict:
    """resultados: [{"correcta": bool|None, "trazable": bool}, ...]"""
    evaluadas = [r for r in resultados if r.get("correcta") is not None]
    correctas = sum(1 for r in evaluadas if r["correcta"])
    trazables = sum(1 for r in resultados if r.get("trazable"))
    pct = round(100 * correctas / len(evaluadas), 1) if evaluadas else None
    pct_traza = round(100 * trazables / len(resultados), 1) if resultados else None
    return {
        "preguntas": len(resultados),
        "evaluadas": len(evaluadas),
        "correctas": correctas,
        "porcentaje_correctas": pct,
        "porcentaje_trazables": pct_traza,
        "cumple_indicador": len(evaluadas) >= 40 and pct is not None and pct >= 85 and pct_traza == 100.0,
    }
