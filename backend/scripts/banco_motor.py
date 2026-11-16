"""
Banco de casos del motor de recomendación (OE2).

Ejecuta 25 escenarios de estudiantes sobre el plan de estudios real (versión 5)
y una oferta de grupos, y audita cada carga propuesta con un verificador
independiente (scripts/auditor.py).

Indicador OE2: en al menos 25 casos de prueba, ≥ 90 % de las propuestas
generadas cumple todas las restricciones duras.

Uso (desde backend/):
    python scripts/banco_motor.py            # oferta simulada reproducible (semilla fija)
    python scripts/banco_motor.py --vivo     # pensum y oferta en vivo de los portales UdeA
Salida: docs/resultados/oe2_motor.md y oe2_motor.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from app.services import grafo_service as grafo  # noqa: E402
from app.services import udea_horarios_service as udea  # noqa: E402
from app.services import udea_pensum_service as pensum  # noqa: E402
from app.services import validador_service as motor  # noqa: E402
from app.services.udea_horarios_service import GrupoVivo, MateriaViva, Sesion  # noqa: E402
from scripts.auditor import auditar  # noqa: E402

SALIDA = RAIZ / "docs" / "resultados"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]


def oferta_simulada(materias, semilla: int = 2026) -> list[MateriaViva]:
    """Oferta reproducible sobre el plan real: 1 a 3 grupos por materia, con
    bloques de 2 h (dos días) o un bloque de 4 h para laboratorios, entre las
    6:00 y las 20:00, y algunos grupos llenos (cupo 0)."""
    rnd = random.Random(semilla)
    oferta = []
    for m in materias:
        if m.nivel == pensum.NIVEL_ELECTIVAS and rnd.random() < 0.5:
            continue  # no todas las electivas se ofertan cada semestre
        grupos = []
        for n in range(1, rnd.randint(1, 3) + 1):
            inicio = rnd.choice(range(6, 19, 2))
            if "LABORATORIO" in m.nombre and inicio <= 16:
                horario = [Sesion(rnd.choice(DIAS), f"{inicio:02d}:00", f"{inicio + 4:02d}:00")]
            else:
                d1 = rnd.randrange(0, 3)
                horario = [Sesion(DIAS[d1], f"{inicio:02d}:00", f"{inicio + 2:02d}:00"), Sesion(DIAS[d1 + 2], f"{inicio:02d}:00", f"{inicio + 2:02d}:00")]
            cupos = 0 if rnd.random() < 0.15 else rnd.randint(1, 35)
            grupos.append(GrupoVivo(str(n), 35, cupos, f"{rnd.randint(18, 21)}-{rnd.randint(101, 420)}", f"PROFESOR {m.codigo % 97}-{n}", horario))
        oferta.append(MateriaViva(m.nombre, str(m.codigo), grupos))
    return oferta


@dataclass
class Escenario:
    id: str
    descripcion: str
    aprobadas: str = ""  # mismo formato que acepta el agente: "nivel:1-3, 2508207"
    quitar: list[int] = field(default_factory=list)  # materias NO aprobadas dentro del rango
    creditos_max: int | None = None
    franja: str | None = None
    electivas: bool = False


ESCENARIOS = [
    Escenario("E01", "Primíparo sin materias aprobadas"),
    Escenario("E02", "Aprobó todo el nivel 1", "nivel:1"),
    Escenario("E03", "Aprobó niveles 1 y 2", "nivel:1-2"),
    Escenario("E04", "Aprobó niveles 1 a 3", "nivel:1-3"),
    Escenario("E05", "Aprobó niveles 1 a 4", "nivel:1-4"),
    Escenario("E06", "Aprobó niveles 1 a 5", "nivel:1-5"),
    Escenario("E07", "Aprobó niveles 1 a 6", "nivel:1-6"),
    Escenario("E08", "Aprobó niveles 1 a 7", "nivel:1-7"),
    Escenario("E09", "Aprobó niveles 1 a 8 (solo le queda Ética y la modalidad de grado)", "nivel:1-8", electivas=True),
    Escenario("E10", "Primíparo que solo estudia en la mañana", franja="manana"),
    Escenario("E11", "Niveles 1-2 aprobados, solo en la tarde", "nivel:1-2", franja="tarde"),
    Escenario("E12", "Niveles 1-4 aprobados, solo en la noche", "nivel:1-4", franja="noche"),
    Escenario("E13", "Niveles 1-3 aprobados con tope de 12 créditos (trabaja)", "nivel:1-3", creditos_max=12),
    Escenario("E14", "Niveles 1-3 aprobados con tope de 16 créditos", "nivel:1-3", creditos_max=16),
    Escenario("E15", "Niveles 1-5 aprobados, quiere el máximo (24)", "nivel:1-5", creditos_max=24),
    Escenario("E16", "Perdió Cálculo Diferencial en nivel 1", "nivel:1", quitar=[2555131]),
    Escenario("E17", "Niveles 1-2 sin Matemáticas Discretas I (rezago en la cadena crítica)", "nivel:1-2", quitar=[2508207]),
    Escenario("E18", "Niveles 1-3 sin Técnicas de Programación", "nivel:1-3", quitar=[2508307]),
    Escenario("E19", "Niveles 1-4 sin Inglés 3 ni Métodos Estadísticos", "nivel:1-4", quitar=[9025103, 2508408]),
    Escenario("E20", "Niveles 1-5 incluyendo electivas habilitadas", "nivel:1-5", electivas=True),
    Escenario("E21", "Niveles 1-6 con electivas y tope de 15 créditos", "nivel:1-6", creditos_max=15, electivas=True),
    Escenario("E22", "Estudiante irregular: niveles 1-3 más Bases de Datos adelantada", "nivel:1-3, 2508507, 2508402, 2508609"),
    Escenario("E23", "Niveles 1-2 sin Lógica I (correquisitos en juego)", "nivel:1-2", quitar=[2508208]),
    Escenario("E24", "Niveles 1-6 solo en la mañana con electivas", "nivel:1-6", franja="manana", electivas=True),
    Escenario("E25", "Niveles 1-7 con tope de 10 créditos", "nivel:1-7", creditos_max=10),
]


def ejecutar(materias, oferta, cmin: int, cmax_defecto: int) -> dict:
    p_idx = {m.codigo: m for m in materias}
    o_idx = {m.codigo: m for m in oferta}
    crit = grafo.criticidad(grafo.construir_grafo(materias))
    filas, total, validas = [], 0, 0
    for e in ESCENARIOS:
        aprobadas, _ = motor.resolver_aprobadas(e.aprobadas, p_idx)
        aprobadas -= set(e.quitar)
        cmax = e.creditos_max or cmax_defecto
        cargas = motor.proponer_cargas(p_idx, o_idx, crit, aprobadas, cmin, cmax, k=3, franja=e.franja, incluir_electivas=e.electivas)
        auditorias = [
            auditar([{"codigo": m["codigo"], "grupo": m["grupo"]} for m in c["materias"]], materias, oferta, aprobadas, cmax, e.franja) for c in cargas
        ]
        ok = sum(1 for a in auditorias if not a)
        total += len(cargas)
        validas += ok
        filas.append(
            {
                "id": e.id,
                "descripcion": e.descripcion,
                "aprobadas": len(aprobadas),
                "tope": cmax,
                "franja": e.franja or "cualquiera",
                "propuestas": len(cargas),
                "cumplen": ok,
                "creditos": [c["creditos"] for c in cargas],
                "ejemplo": [m["nombre"] for m in cargas[0]["materias"]] if cargas else [],
                "violaciones": [v for a in auditorias for v in a],
            }
        )
    pct = round(100 * validas / total, 1) if total else 0.0
    return {"escenarios": filas, "propuestas_totales": total, "propuestas_validas": validas, "porcentaje": pct, "cumple_indicador": len(ESCENARIOS) >= 25 and pct >= 90}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vivo", action="store_true")
    args = ap.parse_args()
    from app.config import get_settings

    s = get_settings()
    if args.vivo:
        materias, oferta, origen = pensum.obtener_pensum(forzar=True), udea.obtener_oferta(forzar=True), f"en vivo ({pensum.origen_actual()} + MARES)"
    else:
        materias = pensum.cargar_snapshot()[0]
        oferta, origen = oferta_simulada(materias), "plan real v5 (snapshot) + oferta simulada con semilla 2026"
    r = ejecutar(materias, oferta, s.CREDITOS_MIN, s.CREDITOS_MAX)
    r.update(fecha=date.today().isoformat(), origen=origen)

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "oe2_motor.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    tabla = "\n".join(
        f"| {f['id']} | {f['descripcion']} | {f['franja']} | {f['tope']} | {f['propuestas']} | {f['cumplen']} | {', '.join(map(str, f['creditos'])) or '—'} |"
        for f in r["escenarios"]
    )
    viol = [f"- {f['id']}: {v}" for f in r["escenarios"] for v in f["violaciones"]]
    sin = [f["id"] for f in r["escenarios"] if not f["propuestas"]]
    md = f"""# OE2 — Banco de casos del motor de validación y recomendación

Generado el {r['fecha']} con `backend/scripts/banco_motor.py`. Datos: {origen}.
Cada carga propuesta por el motor se verificó con un auditor independiente
(`backend/scripts/auditor.py`) que reimplementa las restricciones duras:
existencia en el plan, no aprobada, prerrequisitos, correquisitos, créditos
aprobados mínimos, oferta, grupo y cupo, cruces de horario al minuto, franja
pedida y tope de créditos.

## Resultado del indicador

| Casos | Propuestas generadas | Cumplen todas las restricciones | Porcentaje | Meta |
|---|---|---|---|---|
| {len(r['escenarios'])} | {r['propuestas_totales']} | {r['propuestas_validas']} | **{r['porcentaje']} %** | ≥ 90 % → {'cumplida' if r['cumple_indicador'] else 'no cumplida'} |

## Escenarios

| Caso | Descripción | Franja | Tope | Propuestas | Cumplen | Créditos por propuesta |
|---|---|---|---|---|---|---|
{tabla}

{'Escenarios sin propuestas (no hay carga factible con esas condiciones): ' + ', '.join(sin) if sin else 'Todos los escenarios produjeron al menos una propuesta.'}

## Violaciones encontradas por el auditor

{chr(10).join(viol) if viol else 'Ninguna.'}
"""
    (SALIDA / "oe2_motor.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
