"""Banco de 25 escenarios del motor (OE2) y pruebas del auditor independiente."""
from app.services import udea_pensum_service as pensum
from app.services.udea_horarios_service import GrupoVivo, MateriaViva, Sesion
from scripts.auditor import auditar
from scripts.banco_motor import ESCENARIOS, ejecutar, oferta_simulada

MATERIAS = pensum.cargar_snapshot()[0]


def test_banco_cumple_indicador_oe2():
    r = ejecutar(MATERIAS, oferta_simulada(MATERIAS), 8, 24)
    assert len(ESCENARIOS) >= 25
    assert r["propuestas_totales"] >= 25
    assert r["porcentaje"] >= 90, [f["violaciones"] for f in r["escenarios"] if f["violaciones"]]


def test_banco_es_reproducible():
    a = ejecutar(MATERIAS, oferta_simulada(MATERIAS), 8, 24)
    b = ejecutar(MATERIAS, oferta_simulada(MATERIAS), 8, 24)
    assert a == b


# --- El auditor no es vacuo: detecta cada tipo de violación ------------------ #
OFERTA = [
    MateriaViva("CÁLCULO DIFERENCIAL", "2555131", [GrupoVivo("1", 30, 5, "A", "P", [Sesion("lunes", "06:00", "08:00")])]),
    MateriaViva("ÁLGEBRA Y TRIGONOMETRÍA", "2555101", [GrupoVivo("1", 30, 0, "A", "P", [Sesion("lunes", "07:00", "09:00")])]),
    MateriaViva("CÁLCULO INTEGRAL", "2555231", [GrupoVivo("1", 30, 5, "A", "P", [Sesion("martes", "14:00", "16:00")])]),
    MateriaViva("TRABAJO DE GRADO", "2508002", [GrupoVivo("1", 30, 5, "A", "P", [Sesion("sábado", "08:00", "12:00")])]),
]


def _v(carga, aprobadas=frozenset(), cmax=24, franja=None):
    return " | ".join(auditar(carga, MATERIAS, OFERTA, set(aprobadas), cmax, franja))


def test_auditor_detecta_violaciones():
    assert "falta correquisito" in _v([{"codigo": 2555131, "grupo": "1"}])
    assert "sin cupo" in _v([{"codigo": 2555101, "grupo": "1"}])
    assert "cruce de horario" in _v([{"codigo": 2555131, "grupo": "1"}, {"codigo": 2555101, "grupo": "1"}])
    assert "falta prerrequisito" in _v([{"codigo": 2555231, "grupo": "1"}])
    assert "132 créditos" in _v([{"codigo": 2508002, "grupo": "1"}], aprobadas={2508701})
    assert "tope de créditos" in _v([{"codigo": 2555231, "grupo": "1"}], aprobadas={2555101, 2555131}, cmax=2)
    assert "franja" in _v([{"codigo": 2555231, "grupo": "1"}], aprobadas={2555101, 2555131}, franja="manana")
    assert "no ofertada" in _v([{"codigo": 2508207, "grupo": "1"}], aprobadas={2508120})
    assert "ya aprobada" in _v([{"codigo": 2555231, "grupo": "1"}], aprobadas={2555101, 2555131, 2555231})


def test_auditor_acepta_carga_correcta():
    assert _v([{"codigo": 2555231, "grupo": "1"}], aprobadas={2555101, 2555131}) == ""
