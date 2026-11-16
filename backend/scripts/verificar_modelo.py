"""
Verificación del modelo computable del plan de estudios (OE1).

Genera la evidencia del indicador OE1:
  - materias y créditos modelados por nivel, aciclicidad (Kahn) y orden topológico;
  - consistencia de niveles (todo prerrequisito está en un nivel anterior);
  - requisitos por créditos y requisitos con código de otra versión del plan;
  - % de coincidencia con el plan publicado, a partir de la hoja de cotejo
    docs/datos/cotejo_plan_publicado.csv (el equipo marca "sí"/"no" por materia
    comparando contra el documento oficial del plan).

Uso (desde backend/):
    python scripts/verificar_modelo.py              # pensum en vivo (o snapshot si el portal no responde)
    python scripts/verificar_modelo.py --snapshot   # usa la copia local app/data/pensum_504_v5.json
Salida: docs/resultados/oe1_modelo.md y oe1_modelo.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from app.services import grafo_service as grafo  # noqa: E402
from app.services import udea_pensum_service as pensum  # noqa: E402

COTEJO = RAIZ / "docs" / "datos" / "cotejo_plan_publicado.csv"
SALIDA = RAIZ / "docs" / "resultados"
CAMPOS = ["codigo", "nombre", "nivel", "creditos", "prerrequisitos", "correquisitos", "otros_requisitos", "coincide", "observacion"]


def _cargar(usar_snapshot: bool):
    if usar_snapshot:
        materias, version = pensum.cargar_snapshot()
        return materias, version, "snapshot"
    materias = pensum.obtener_pensum(forzar=True)
    return materias, pensum.version_actual(), pensum.origen_actual()


def consistencia_niveles(materias) -> list[str]:
    """Un prerrequisito de una obligatoria debe estar en un nivel estrictamente menor."""
    idx = {m.codigo: m for m in materias}
    hallazgos = []
    for m in materias:
        if m.nivel == pensum.NIVEL_ELECTIVAS:
            continue
        for r in m.requisitos:
            req = idx.get(r.codigo)
            if req is None or req.nivel == pensum.NIVEL_ELECTIVAS:
                continue
            if pensum.es_prerrequisito(r) and req.nivel >= m.nivel:
                hallazgos.append(f"{m.nombre} (nivel {m.nivel}) tiene como prerrequisito a {req.nombre} (nivel {req.nivel}).")
            if pensum.es_correquisito(r) and req.nivel > m.nivel:
                hallazgos.append(f"{m.nombre} (nivel {m.nivel}) tiene como correquisito a {req.nombre} (nivel {req.nivel}).")
    return hallazgos


def _fila(m, idx) -> dict:
    nombre = lambda c: idx[c].nombre if c in idx else str(c)  # noqa: E731
    return {
        "codigo": m.codigo,
        "nombre": m.nombre,
        "nivel": m.nivel,
        "creditos": m.creditos,
        "prerrequisitos": "; ".join(nombre(r.codigo) for r in m.requisitos if pensum.es_prerrequisito(r)),
        "correquisitos": "; ".join(nombre(r.codigo) for r in m.requisitos if pensum.es_correquisito(r)),
        "otros_requisitos": "; ".join(
            f"{r.codigo} créditos aprobados" if pensum.es_req_creditos(r) else f"código {r.codigo} (otra versión)"
            for r in m.requisitos
            if pensum.es_req_creditos(r) or pensum.es_externo(r)
        ),
        "coincide": "",
        "observacion": "",
    }


def cotejo(materias) -> dict:
    """Crea la hoja de cotejo si no existe; si existe, calcula el % de coincidencia."""
    idx = {m.codigo: m for m in materias}
    obligatorias = [m for m in materias if m.nivel != pensum.NIVEL_ELECTIVAS]
    if not COTEJO.exists():
        COTEJO.parent.mkdir(parents=True, exist_ok=True)
        with COTEJO.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            w.writeheader()
            for m in sorted(obligatorias, key=lambda x: (x.nivel, x.codigo)):
                w.writerow(_fila(m, idx))
        return {"estado": "hoja creada, pendiente de cotejo", "archivo": str(COTEJO.relative_to(RAIZ))}

    with COTEJO.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    marcadas = [x for x in filas if x["coincide"].strip()]
    si = [x for x in marcadas if x["coincide"].strip().lower() in {"si", "sí", "s", "1", "x"}]
    return {
        "estado": "cotejo completo" if len(marcadas) == len(filas) else f"cotejo parcial ({len(marcadas)}/{len(filas)})",
        "archivo": str(COTEJO.relative_to(RAIZ)),
        "materias_cotejadas": len(marcadas),
        "coinciden": len(si),
        "porcentaje": round(100 * len(si) / len(marcadas), 1) if marcadas else None,
        "no_coinciden": [f"{x['nombre']}: {x['observacion']}" for x in marcadas if x not in si],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    args = ap.parse_args()

    materias, version, origen = _cargar(args.snapshot)
    r = grafo.resumen_grafo(materias, top=10)
    niveles = consistencia_niveles(materias)
    cot = cotejo(materias)
    datos = {"fecha": date.today().isoformat(), "version_pensum": version, "origen": origen, "resumen": r, "consistencia_niveles": niveles, "cotejo": cot}

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "oe1_modelo.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    filas_nivel = "\n".join(f"| {n} | {v['materias']} | {v['creditos']} |" for n, v in r["por_nivel"].items())
    criticas = "\n".join(f"| {c['nombre']} | {c['nivel']} | {c['dependientes']} |" for c in r["materias_mas_criticas"])
    creditos = "\n".join(
        f"- {x['creditos_minimos']} créditos aprobados: {len(x['materias'])} materias" for x in r["requisitos_por_creditos"]
    )
    pct = cot.get("porcentaje")
    md = f"""# OE1 — Verificación del modelo computable del plan de estudios

Generado el {datos['fecha']} con `backend/scripts/verificar_modelo.py`.
Fuente: pensum versión {version} del programa 504 (origen de los datos: **{origen}**).

## Indicadores

| Indicador | Resultado |
|---|---|
| Materias del pensum modeladas | {r['materias_totales']} ({r['materias_obligatorias']} obligatorias, {r['materias_totales'] - r['materias_obligatorias']} electivas) |
| Créditos obligatorios | {r['creditos_obligatorios']} |
| Niveles con obligatorias | {r['niveles']} |
| Aristas de prerrequisito | {r['aristas_prerrequisito']} |
| Correquisitos | {r['correquisitos']} |
| Grafo acíclico (Kahn) | {'Sí' if r['es_aciclico'] else 'No: ' + str(r['materias_en_ciclo'])} |
| Orden topológico cubre todas las materias | {'Sí' if r['orden_topologico_valido'] else 'No'} |
| Prerrequisitos en niveles anteriores | {'Sí, sin hallazgos' if not niveles else f'{len(niveles)} hallazgos (ver abajo)'} |
| Coincidencia con el plan publicado | {f'{pct} % ({cot["coinciden"]}/{cot["materias_cotejadas"]})' if pct is not None else cot['estado']} |

## Materias y créditos obligatorios por nivel

| Nivel | Materias | Créditos |
|---|---|---|
{filas_nivel}

## Requisitos por créditos aprobados (tipo PRERREQCRED en Cursum)

{creditos or '- Ninguno'}

Requisitos con código que no existe en la versión vigente: {', '.join(map(str, r['requisitos_fuera_del_pensum'])) or 'ninguno'}.

## Materias más críticas (dependientes transitivos)

| Materia | Nivel | Dependientes |
|---|---|---|
{criticas}

## Consistencia de niveles

{chr(10).join('- ' + h for h in niveles) if niveles else 'Todos los prerrequisitos de las materias obligatorias están en un nivel anterior y los correquisitos en el mismo nivel o uno anterior.'}

## Cotejo con el plan publicado

Estado: {cot['estado']}. Hoja: `{cot['archivo']}`. Para cada materia obligatoria, comparar nombre,
nivel, créditos y requisitos contra el documento oficial del plan y escribir `sí` o `no` en la columna
`coincide` (con la diferencia en `observacion`); luego volver a ejecutar este script.
"""
    (SALIDA / "oe1_modelo.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
