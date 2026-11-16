"""
Catálogo verificable de las reglas académicas que aplica PlaneAI.  [OE1]

Cada regla indica su fuente (artículo del Reglamento Estudiantil de Pregrado,
Acuerdo Superior 1 de 1981, o el plan de estudios en Cursum), si es dura
(invalida la carga) o una advertencia, y dónde se verifica en el código. Las
pruebas (tests/test_reglas.py) comprueban que cada regla dura tenga un caso que
la dispare, de modo que el catálogo no quede desalineado con el motor.
"""
from __future__ import annotations

from app.config import get_settings

REGLAMENTO = "Reglamento Estudiantil de Pregrado UdeA (Acuerdo Superior 1 de 1981)"
PLAN = "Plan de estudios de Ingeniería de Sistemas (portal Cursum, programa 504)"


def catalogo() -> list[dict]:
    s = get_settings()
    return [
        {
            "id": "R01",
            "nombre": "Solo materias del plan y no aprobadas",
            "tipo": "dura",
            "error": ["no_existe", "ya_aprobada", "duplicada"],
            "descripcion": "El estudiante solo inscribe asignaturas de su plan de estudios que no haya aprobado.",
            "fuente": f"{REGLAMENTO}, art. 64",
        },
        {
            "id": "R02",
            "nombre": "Prerrequisitos aprobados",
            "tipo": "dura",
            "error": ["prerrequisito"],
            "descripcion": "Un prerrequisito debe estar aprobado antes de matricular la asignatura que lo exige.",
            "fuente": f"{REGLAMENTO}, art. 42; {PLAN}",
        },
        {
            "id": "R03",
            "nombre": "Correquisitos simultáneos o aprobados",
            "tipo": "dura",
            "error": ["correquisito"],
            "descripcion": "Un correquisito se cursa a la vez que la asignatura, salvo que ya esté aprobado.",
            "fuente": f"{REGLAMENTO}, art. 43 y parágrafo; {PLAN}",
        },
        {
            "id": "R04",
            "nombre": "Créditos aprobados mínimos",
            "tipo": "dura",
            "error": ["creditos_requisito"],
            "descripcion": "Algunas asignaturas exigen un mínimo de créditos aprobados (p. ej. 132 para las modalidades de grado).",
            "fuente": f"{PLAN} (requisitos tipo PRERREQCRED)",
        },
        {
            "id": "R05",
            "nombre": "Oferta, grupo y cupo",
            "tipo": "dura",
            "error": ["no_ofertada", "grupo_inexistente", "sin_cupo"],
            "descripcion": "La asignatura debe estar ofertada en el semestre y el grupo elegido debe existir y tener cupos.",
            "fuente": "Oferta de cupos del programa (MARES, pub_cuposprog)",
        },
        {
            "id": "R06",
            "nombre": "Sin cruces de horario",
            "tipo": "dura",
            "error": ["choque_horario"],
            "descripcion": "No pueden matricularse asignaturas cuyos horarios se crucen.",
            "fuente": f"{REGLAMENTO}, art. 68",
        },
        {
            "id": "R07",
            "nombre": "Máximo de créditos",
            "tipo": "dura",
            "error": ["creditos_max"],
            "parametro": {"CREDITOS_MAX": s.CREDITOS_MAX},
            "descripcion": "Tiempo completo va de 14 a 24 créditos por semestre; el tope ordinario es 24.",
            "fuente": f"{REGLAMENTO}, art. 66",
        },
        {
            "id": "R08",
            "nombre": "Mínimo de créditos",
            "tipo": "advertencia",
            "error": ["creditos_min"],
            "parametro": {"CREDITOS_MIN": s.CREDITOS_MIN},
            "descripcion": "La carga mínima es de 8 créditos, salvo fuerza mayor aprobada o si faltan menos para terminar.",
            "fuente": f"{REGLAMENTO}, art. 67",
        },
        {
            "id": "R09",
            "nombre": "Tiempo parcial",
            "tipo": "advertencia",
            "error": ["tiempo_parcial"],
            "descripcion": "Con menos de 14 créditos la matrícula es de tiempo parcial.",
            "fuente": f"{REGLAMENTO}, art. 66",
        },
        {
            "id": "R10",
            "nombre": "Requisito con código de otra versión del plan",
            "tipo": "advertencia",
            "error": ["requisito_externo"],
            "descripcion": "Si un requisito apunta a una materia que no está en la versión vigente, se pide confirmar la equivalencia con el asesor.",
            "fuente": PLAN,
        },
        {
            "id": "R11",
            "nombre": "Grupo sin elegir",
            "tipo": "advertencia",
            "error": ["sin_grupo"],
            "descripcion": "Sin grupo solo se valida la parte académica (requisitos y créditos), no cupos ni horario.",
            "fuente": "Regla de uso de PlaneAI",
        },
    ]


def reglas_duras() -> list[dict]:
    return [r for r in catalogo() if r["tipo"] == "dura"]
