"""Datos simulados (pensum y oferta) para probar el motor sin consultar los portales."""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Si el SDK de Gemini no está instalado en el entorno de pruebas, se simula:
# las pruebas del motor no lo usan.
try:  # pragma: no cover
    import google.generativeai  # noqa: F401
except ImportError:  # pragma: no cover
    google = sys.modules.setdefault("google", types.ModuleType("google"))
    genai = types.ModuleType("google.generativeai")
    sys.modules["google.generativeai"] = genai
    google.generativeai = genai

from app.services.udea_horarios_service import GrupoVivo, MateriaViva, Sesion  # noqa: E402
from app.services.udea_pensum_service import MateriaPensum, Requisito  # noqa: E402

PRE, CO = "PRERREQ", "CORREQ"


def _m(codigo, nombre, nivel, creditos, reqs=()):
    return MateriaPensum(codigo, nombre, nivel, creditos, "OBLIGATORIA" if nivel != 99 else "ELECTIVA",
                         [Requisito(c, t) for c, t in reqs])


def _g(numero, cupos, *bloques, total=30):
    """bloques: ("lunes", 6, 8)"""
    return GrupoVivo(numero, total, cupos, "AULA", "PROFESOR",
                     [Sesion(d, f"{i:02d}:00", f"{f:02d}:00") for d, i, f in bloques])


PENSUM = [
    _m(101, "Cálculo Diferencial", 1, 4),
    _m(102, "Álgebra Lineal", 1, 4),
    _m(103, "Introducción a la Programación", 1, 3),
    _m(201, "Cálculo Integral", 2, 4, [(101, PRE)]),
    _m(202, "Lógica y Representación", 2, 3, [(103, PRE)]),
    _m(203, "Física Mecánica", 2, 4, [(101, PRE), (204, CO)]),
    _m(204, "Laboratorio de Física Mecánica", 2, 1),
    _m(301, "Ecuaciones Diferenciales", 3, 4, [(201, PRE)]),
    _m(302, "Estructuras de Datos", 3, 4, [(202, PRE)]),
    _m(401, "Bases de Datos", 4, 4, [(302, PRE)]),
    _m(901, "Electiva de Profundización", 99, 3),
]

OFERTA = [
    MateriaViva("Cálculo Diferencial", "101", [_g("1", 5, ("lunes", 6, 8), ("miércoles", 6, 8))]),
    MateriaViva("Álgebra Lineal", "102", [_g("1", 0, ("martes", 8, 10)), _g("2", 3, ("viernes", 14, 16))]),
    MateriaViva("Cálculo Integral", "201", [
        _g("1", 4, ("lunes", 6, 8), ("miércoles", 6, 8)),
        _g("2", 2, ("martes", 10, 12), ("jueves", 10, 12)),
    ]),
    MateriaViva("Lógica y Representación", "202", [_g("1", 6, ("lunes", 7, 9))]),
    MateriaViva("Física Mecánica", "203", [_g("1", 8, ("martes", 14, 16), ("jueves", 14, 16))]),
    MateriaViva("Laboratorio de Física Mecánica", "204", [_g("1", 8, ("viernes", 8, 10))]),
    MateriaViva("Ecuaciones Diferenciales", "301", [_g("1", 3, ("lunes", 18, 20))]),
    MateriaViva("Estructuras de Datos", "302", [_g("1", 0, ("miércoles", 10, 12))]),
]


@pytest.fixture
def pensum_idx():
    return {m.codigo: m for m in PENSUM}


@pytest.fixture
def oferta_idx():
    return {m.codigo: m for m in OFERTA}


@pytest.fixture
def datos_en_vivo_simulados(monkeypatch):
    """Reemplaza las consultas a los portales por los datos simulados."""
    from app.services import udea_horarios_service as udea
    from app.services import udea_pensum_service as pensum

    monkeypatch.setattr(pensum, "obtener_pensum", lambda forzar=False: PENSUM)
    monkeypatch.setattr(udea, "obtener_oferta", lambda forzar=False: OFERTA)
