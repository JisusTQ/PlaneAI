"""
Verificación del modelo computable del plan de estudios (OE1).

Genera la evidencia del indicador OE1:
  - materias y créditos modelados por nivel, aciclicidad (Kahn) y orden topológico;
  - consistencia de niveles (todo prerrequisito está en un nivel anterior);
  - requisitos por créditos y requisitos con código de otra versión del plan;
  - estructura del plan oficial (55 espacios, 168 créditos, 10 niveles);
  - % de coincidencia con el plan publicado (Acuerdo de Facultad 868, gráfico
    oficial V.5 transcrito en app/data/plan_publicado_af868.json), espacio por
    espacio y atributo por atributo; el detalle queda en
    docs/datos/cotejo_plan_publicado.csv.

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
from app.services import plan_service  # noqa: E402
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


def cotejo(materias) -> dict:
    """Cotejo automático contra el plan publicado; escribe el detalle en CSV."""
    c = plan_service.cotejo(materias)
    COTEJO.parent.mkdir(parents=True, exist_ok=True)
    with COTEJO.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nivel", "espacio_plan", "codigo_plan", "codigo_modelo", "coincide", "diferencias", "nota"])
        for x in c["detalle"]:
            w.writerow([x["nivel"], x["espacio"], x["codigo_plan"] or "", x["codigo_modelo"] or "", "sí" if x["coincide"] else "no", "; ".join(x["diferencias"]), x["nota"]])
    c["archivo"] = str(COTEJO.relative_to(RAIZ))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    args = ap.parse_args()

    materias, version, origen = _cargar(args.snapshot)
    r = grafo.resumen_grafo(materias, top=10)
    niveles = consistencia_niveles(materias)
    cot = cotejo(materias)
    est = plan_service.estructura(materias)
    datos = {"fecha": date.today().isoformat(), "version_pensum": version, "origen": origen, "resumen": r, "estructura_plan": est, "consistencia_niveles": niveles, "cotejo": {k: v for k, v in cot.items() if k != "detalle"}, "cotejo_detalle": cot["detalle"]}

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "oe1_modelo.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    filas_nivel = "\n".join(f"| {n} | {v['materias']} | {v['creditos']} |" for n, v in r["por_nivel"].items())
    criticas = "\n".join(f"| {c['nombre']} | {c['nivel']} | {c['dependientes']} |" for c in r["materias_mas_criticas"])
    creditos = "\n".join(
        f"- {x['creditos_minimos']} créditos aprobados: {len(x['materias'])} materias" for x in r["requisitos_por_creditos"]
    )
    plan_niveles = "\n".join(
        f"| {n} | {len(v['obligatorias'])} | {', '.join(v['electivos']) or '—'} | {v['creditos']} |" for n, v in est["niveles"].items()
    )
    difs = "\n".join(
        f"| {x['espacio'].title()} | {'; '.join(x['diferencias']) or 'Coincide'} | {x['nota']} |"
        for x in cot["detalle"]
        if x["diferencias"] or (x["nota"] and x["codigo_plan"])
    )
    md = f"""# OE1 — Verificación del modelo computable del plan de estudios

Generado el {datos['fecha']} con `backend/scripts/verificar_modelo.py`.
Fuente: pensum versión {version} del programa 504 (origen de los datos: **{origen}**).

## Indicadores

| Indicador | Resultado |
|---|---|
| Espacios del plan modelados | {est['total_espacios']} ({r['materias_obligatorias']} obligatorias + {len(est['espacios_electivos'])} espacios electivos) |
| Créditos para grado | {est['total_creditos']} ({r['creditos_obligatorios']} obligatorios + {est['total_creditos'] - r['creditos_obligatorios']} electivos); Cursum: {est['creditos_grado_cursum']} |
| Niveles | {est['total_niveles']} |
| Materias de Cursum modeladas | {r['materias_totales']} ({r['materias_obligatorias']} obligatorias y {r['materias_totales'] - r['materias_obligatorias']} del banco de electivas) |
| Aristas de prerrequisito | {r['aristas_prerrequisito']} |
| Correquisitos | {r['correquisitos']} |
| Grafo acíclico (Kahn) | {'Sí' if r['es_aciclico'] else 'No: ' + str(r['materias_en_ciclo'])} |
| Orden topológico cubre todas las materias | {'Sí' if r['orden_topologico_valido'] else 'No'} |
| Prerrequisitos en niveles anteriores | {'Sí, sin hallazgos' if not niveles else f'{len(niveles)} hallazgos (ver abajo)'} |
| **Coincidencia con el plan publicado (por espacio)** | **{cot['porcentaje_espacios']} %** ({cot['espacios_coinciden']}/{cot['espacios']}) — meta ≥ 95 % |
| Coincidencia por atributo (nivel, créditos, requisitos) | {cot['porcentaje_atributos']} % ({cot['atributos_coinciden']}/{cot['atributos']}) |

## Plan por niveles (AF 868)

| Nivel | Obligatorias | Espacios electivos | Créditos |
|---|---|---|---|
{plan_niveles}

## Requisitos por créditos aprobados (tipo PRERREQCRED en Cursum)

{creditos or '- Ninguno'}

Requisitos con código que no existe en la versión vigente: {', '.join(map(str, r['requisitos_fuera_del_pensum'])) or 'ninguno'}.

## Materias más críticas (dependientes transitivos)

| Materia | Nivel | Dependientes |
|---|---|---|
{criticas}

## Consistencia de niveles

{chr(10).join('- ' + h for h in niveles) if niveles else 'Todos los prerrequisitos de las materias obligatorias están en un nivel anterior y los correquisitos en el mismo nivel o uno anterior.'}

## Cotejo con el plan publicado ({cot['plan']})

Detalle completo: `{cot['archivo']}`. Espacios con diferencias o con reemplazo de código:

| Espacio | Diferencia | Nota |
|---|---|---|
{difs}

Ajustes aplicados al modelo porque Cursum no los refleja: Proyecto Integrador I exige 80 créditos aprobados
(Lineamientos PI 2026-2 y AF 868) y el requisito antiguo 2539101 (Lectoescritura) se cumple con Español
Académico (2539130), que la reemplazó en el mismo espacio.
"""
    (SALIDA / "oe1_modelo.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
