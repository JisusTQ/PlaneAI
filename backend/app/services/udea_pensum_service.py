"""
Pensum oficial de Ingeniería de Sistemas desde el portal Cursum.

Las materias se organizan por NIVEL (= semestre). El agente lo usa para saber
qué materias corresponden a un semestre antes de revisar cupos/horarios.

API:  GET {BASE}/programas -> versión vigente; GET {BASE}/pensum/{prog}/{ver}.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.services.udea_horarios_service import crear_sesion

_BASE = "https://wsingenieria.udea.edu.co:8094/cursum/ingenieria"
_ORIGIN = "https://ingenieria2.udea.edu.co"
PROGRAMA_ID = 504  # INGENIERÍA DE SISTEMAS
_TIMEOUT = 45

CACHE_TTL_SEGUNDOS = 3600  # 1 hora (el plan de estudios es muy estable)

# Nivel especial que el portal usa para las electivas / banco de materias.
NIVEL_ELECTIVAS = 99

# Tipos de requisito normalizados.
#  - PRERREQ:  materia que debe estar aprobada antes (Reglamento, art. 42).
#  - CORREQ:   materia que se cursa a la vez o ya aprobada (art. 43).
#  - CREDITOS: el portal la marca "PRERREQCRED"; el "código" es en realidad el
#              número mínimo de créditos aprobados (p. ej. 132 para trabajo de grado).
#  - EXTERNO:  código de materia que no existe en la versión vigente del plan
#              (versión anterior u otro programa); se reporta como aviso.
TIPO_PRE, TIPO_CO, TIPO_CREDITOS, TIPO_EXTERNO = "PRERREQ", "CORREQ", "CREDITOS", "EXTERNO"

# Copia local del pensum (misma estructura que el portal) para operar si Cursum
# no responde y para pruebas reproducibles.
SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "pensum_504_v5.json"


@dataclass
class Requisito:
    codigo: int          # código de la materia requisito
    tipo: str            # "PRERREQ" (prerrequisito) o "CORREQ" (correquisito)


@dataclass
class MateriaPensum:
    codigo: int
    nombre: str
    nivel: int
    creditos: int
    tipo: str
    requisitos: list[Requisito] = field(default_factory=list)


_cache: dict = {"datos": None, "ts": 0.0, "version": None, "origen": None}


def es_prerrequisito(r: Requisito) -> bool:
    return r.tipo == TIPO_PRE


def es_correquisito(r: Requisito) -> bool:
    return r.tipo == TIPO_CO


def es_req_creditos(r: Requisito) -> bool:
    return r.tipo == TIPO_CREDITOS


def es_externo(r: Requisito) -> bool:
    return r.tipo == TIPO_EXTERNO


def _tipo_normalizado(tipo_portal: str, codigo: int, codigos_plan: set[int]) -> str:
    t = (tipo_portal or "").upper()
    if "CRED" in t or codigo < 1000:  # los códigos de materia UdeA tienen 7 dígitos
        return TIPO_CREDITOS
    if t.startswith("CO"):
        return TIPO_CO
    if codigo not in codigos_plan:
        return TIPO_EXTERNO
    return TIPO_PRE


def parsear(filas: list[dict]) -> list[MateriaPensum]:
    """Convierte la respuesta JSON de Cursum en materias con requisitos normalizados."""
    codigos = {int(x["materia"]) for x in filas}
    return [
        MateriaPensum(
            codigo=int(x["materia"]),
            nombre=(x.get("nombreMateria") or "").strip(),
            nivel=int(x.get("nivel") or 0),
            creditos=int(x.get("creditos") or 0),
            tipo=(x.get("tipoMateria") or "").strip(),
            requisitos=[
                Requisito(
                    codigo=int(req["materiaRequisito"]),
                    tipo=_tipo_normalizado(req.get("tipoRequisito"), int(req["materiaRequisito"]), codigos),
                )
                for req in (x.get("requisitos") or [])
                if req.get("materiaRequisito")
            ],
        )
        for x in filas
    ]


def cargar_snapshot() -> tuple[list[MateriaPensum], int]:
    datos = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return parsear(datos["materias"]), int(datos["version"])


def _version_actual(sesion) -> int:
    """Obtiene la versión vigente del pensum del programa desde /programas."""
    r = sesion.get(f"{_BASE}/programas", headers={"Origin": _ORIGIN}, timeout=_TIMEOUT)
    r.raise_for_status()
    for p in r.json():
        if p.get("codigo") == PROGRAMA_ID:
            return int(p["versionActual"])
    raise RuntimeError(f"No se encontró el programa {PROGRAMA_ID} en el portal Cursum.")


def _descargar() -> tuple[list[MateriaPensum], int]:
    sesion = crear_sesion()
    version = _version_actual(sesion)
    r = sesion.get(
        f"{_BASE}/pensum/{PROGRAMA_ID}/{version}",
        headers={"Origin": _ORIGIN},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()

    materias = parsear(r.json())
    return materias, version


def obtener_pensum(forzar: bool = False) -> list[MateriaPensum]:
    """Devuelve el pensum completo (usando la caché si sigue vigente)."""
    ahora = time.monotonic()
    if (
        not forzar
        and _cache["datos"] is not None
        and (ahora - _cache["ts"]) < CACHE_TTL_SEGUNDOS
    ):
        return _cache["datos"]

    try:
        datos, version = _descargar()
        origen = "cursum"
    except Exception:
        if _cache["datos"] is not None:  # mejor datos de hace un rato que ninguno
            _cache["ts"] = ahora - CACHE_TTL_SEGUNDOS + 300  # reintenta en 5 min
            return _cache["datos"]
        datos, version = cargar_snapshot()
        origen = "snapshot"
    _cache.update(datos=datos, ts=ahora, version=version, origen=origen)
    return datos


def origen_actual() -> str | None:
    """"cursum" (en vivo) o "snapshot" (copia local por caída del portal)."""
    return _cache["origen"]


def version_actual() -> int | None:
    """Versión del pensum cargada en caché (None si aún no se consultó)."""
    return _cache["version"]


def materias_por_nivel(nivel: int) -> list[MateriaPensum]:
    """Materias de un nivel (= semestre). Para electivas usar NIVEL_ELECTIVAS (99)."""
    return [m for m in obtener_pensum() if m.nivel == nivel]


def niveles_disponibles() -> list[int]:
    """Niveles (semestres) presentes en el pensum, ordenados."""
    return sorted({m.nivel for m in obtener_pensum()})


def catalogo_por_codigo() -> dict[int, MateriaPensum]:
    """Índice {código -> materia} para resolver requisitos por su código."""
    return {m.codigo: m for m in obtener_pensum()}


def nombre_de(codigo: int) -> str:
    """Nombre de una materia dado su código (o el código como texto si no existe)."""
    materia = catalogo_por_codigo().get(codigo)
    return materia.nombre if materia else str(codigo)
