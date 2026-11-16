"""Requisitos por créditos, códigos externos, snapshot del pensum y catálogo de reglas (OE1)."""
from app.services import grafo_service as grafo
from app.services import reglas_service as reglas
from app.services import udea_pensum_service as pensum
from app.services import validador_service as motor
from app.services.udea_horarios_service import GrupoVivo, MateriaViva, Sesion
from app.services.udea_pensum_service import MateriaPensum, Requisito
from app.services.validador_service import Eleccion

CRED, EXT = pensum.TIPO_CREDITOS, pensum.TIPO_EXTERNO


# --------------------------------------------------------------------------- #
#  Normalización de requisitos
# --------------------------------------------------------------------------- #
def test_parsear_normaliza_tipos():
    filas = [
        {"materia": 1000001, "nombreMateria": "A", "nivel": 1, "creditos": 3, "tipoMateria": "OBLIGATORIA"},
        {
            "materia": 1000002,
            "nombreMateria": "B",
            "nivel": 99,
            "creditos": 12,
            "tipoMateria": "ELECTIVA",
            "requisitos": [
                {"materiaRequisito": 132, "tipoRequisito": "PRERREQCRED"},
                {"materiaRequisito": 1000001, "tipoRequisito": "PRERREQ"},
                {"materiaRequisito": 2539101, "tipoRequisito": "PRERREQ"},
                {"materiaRequisito": 1000001, "tipoRequisito": "CORREQ"},
            ],
        },
    ]
    b = pensum.parsear(filas)[1]
    assert [r.tipo for r in b.requisitos] == [CRED, "PRERREQ", EXT, "CORREQ"]


def test_snapshot_es_consistente():
    materias, version = pensum.cargar_snapshot()
    r = grafo.resumen_grafo(materias)
    assert version == 5
    assert r["materias_totales"] == 108
    assert r["es_aciclico"] and r["orden_topologico_valido"]
    # Los requisitos numéricos ya no aparecen como "materias fuera del pensum".
    assert r["requisitos_fuera_del_pensum"] == [2539101]
    assert {x["creditos_minimos"] for x in r["requisitos_por_creditos"]} == {16, 48, 60, 65, 132}


def test_snapshot_trabajo_de_grado_exige_132_creditos():
    materias, _ = pensum.cargar_snapshot()
    tg = next(m for m in materias if m.codigo == 2508002)
    assert any(r.tipo == CRED and r.codigo == 132 for r in tg.requisitos)


# --------------------------------------------------------------------------- #
#  Motor con requisitos de créditos
# --------------------------------------------------------------------------- #
def _m(codigo, nivel, creditos, reqs=()):
    return MateriaPensum(codigo, f"M{codigo}", nivel, creditos, "OBLIGATORIA", [Requisito(c, t) for c, t in reqs])


PENSUM = {
    m.codigo: m
    for m in [
        _m(1111111, 1, 10),
        _m(2222222, 2, 10),
        _m(3333333, 99, 3, [(16, CRED)]),
        _m(4444444, 99, 3, [(9999999, EXT)]),
    ]
}
OFERTA = {
    str(c): MateriaViva(f"M{c}", str(c), [GrupoVivo("1", 30, 10, "A", "P", [Sesion("lunes", f"{h:02d}:00", f"{h + 2:02d}:00")])])
    for c, h in [(2222222, 6), (3333333, 8), (4444444, 10)]
}


def test_requisito_de_creditos_no_cumplido():
    r = motor.validar_carga(PENSUM, OFERTA, {1111111}, [Eleccion(3333333, "1")], 1, 24)
    assert not r.valida
    assert r.errores[0]["tipo"] == "creditos_requisito"
    assert "16 créditos" in r.errores[0]["mensaje"]


def test_requisito_de_creditos_cumplido():
    r = motor.validar_carga(PENSUM, OFERTA, {1111111, 2222222}, [Eleccion(3333333, "1")], 1, 24)
    assert r.valida


def test_requisito_externo_es_advertencia():
    r = motor.validar_carga(PENSUM, OFERTA, set(), [Eleccion(4444444, "1")], 1, 24)
    assert r.valida
    assert any(a["tipo"] == "requisito_externo" for a in r.advertencias)


def test_habilitadas_respeta_creditos():
    antes = {m.codigo for m in motor.materias_habilitadas(PENSUM, {1111111}, incluir_electivas=True)}
    despues = {m.codigo for m in motor.materias_habilitadas(PENSUM, {1111111, 2222222}, incluir_electivas=True)}
    assert 3333333 not in antes and 3333333 in despues


def test_tiempo_parcial_es_advertencia(pensum_idx, oferta_idx):
    r = motor.validar_carga(pensum_idx, oferta_idx, set(), [Eleccion(101, "1")], 1, 24)
    assert r.valida and any(a["tipo"] == "tiempo_parcial" for a in r.advertencias)


# --------------------------------------------------------------------------- #
#  Catálogo de reglas alineado con el motor
# --------------------------------------------------------------------------- #
def test_catalogo_cita_fuente_en_todas_las_reglas():
    for regla in reglas.catalogo():
        assert regla["fuente"], regla["id"]


def test_cada_regla_dura_tiene_un_caso_que_la_dispara(pensum_idx, oferta_idx):
    """Ejecuta una carga inválida por cada código de error y verifica que el motor lo emita."""
    casos = {
        "no_existe": (set(), [Eleccion(999)]),
        "ya_aprobada": ({101}, [Eleccion(101, "1")]),
        "duplicada": (set(), [Eleccion(101, "1"), Eleccion(101, "1")]),
        "prerrequisito": (set(), [Eleccion(201, "1")]),
        "correquisito": ({101}, [Eleccion(203, "1")]),
        "no_ofertada": ({301}, [Eleccion(401)]),
        "grupo_inexistente": (set(), [Eleccion(101, "9")]),
        "sin_cupo": (set(), [Eleccion(102, "1")]),
        "choque_horario": ({101, 103}, [Eleccion(201, "1"), Eleccion(202, "1")]),
    }
    emitidos = set()
    for codigo_error, (aprobadas, propuesta) in casos.items():
        r = motor.validar_carga(pensum_idx, oferta_idx, aprobadas, propuesta, 1, 24)
        emitidos |= {e["tipo"] for e in r.errores}
    r = motor.validar_carga(pensum_idx, oferta_idx, set(), [Eleccion(101, "1"), Eleccion(103)], 1, 5)
    emitidos |= {e["tipo"] for e in r.errores}
    r = motor.validar_carga(PENSUM, OFERTA, set(), [Eleccion(3333333, "1")], 1, 24)
    emitidos |= {e["tipo"] for e in r.errores}

    for regla in reglas.reglas_duras():
        assert set(regla["error"]) <= emitidos, f"{regla['id']} no tiene caso de prueba"


def test_api_reglas():
    from fastapi.testclient import TestClient

    from app.main import app

    datos = TestClient(app).get("/reglas").json()
    assert {r["id"] for r in datos} >= {"R02", "R06", "R07"}
