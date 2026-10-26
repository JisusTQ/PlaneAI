"""Banco de casos del modelo del pensum (OE1) y del motor de validación (OE2).

Ejecutar desde backend/:  pytest -q
"""
import pytest

from app.services import grafo_service as grafo
from app.services import validador_service as motor
from app.services.udea_pensum_service import MateriaPensum, Requisito
from app.services.validador_service import Eleccion
from tests.conftest import PENSUM

CMIN, CMAX = 8, 24


def validar(pensum_idx, oferta_idx, aprobadas, propuesta, cmax=CMAX):
    return motor.validar_carga(pensum_idx, oferta_idx, set(aprobadas), propuesta, CMIN, cmax)


def tipos(r):
    return {e["tipo"] for e in r.errores}


# --------------------------------------------------------------------------- #
#  OE1 — grafo del plan de estudios
# --------------------------------------------------------------------------- #
def test_pensum_es_aciclico():
    _, en_ciclo = grafo.orden_topologico(grafo.construir_grafo(PENSUM))
    assert en_ciclo == []


def test_orden_topologico_respeta_prerrequisitos():
    orden, _ = grafo.orden_topologico(grafo.construir_grafo(PENSUM))
    pos = {c: i for i, c in enumerate(orden)}
    for m in PENSUM:
        for r in m.requisitos:
            if r.tipo == "PRERREQ":
                assert pos[r.codigo] < pos[m.codigo]


def test_detecta_ciclo():
    ciclico = [
        MateriaPensum(1, "A", 1, 3, "OB", [Requisito(2, "PRERREQ")]),
        MateriaPensum(2, "B", 1, 3, "OB", [Requisito(1, "PRERREQ")]),
        MateriaPensum(3, "C", 1, 3, "OB"),
    ]
    _, en_ciclo = grafo.orden_topologico(grafo.construir_grafo(ciclico))
    assert en_ciclo == [1, 2]


def test_correquisito_no_crea_arista():
    suc = grafo.construir_grafo(PENSUM)
    assert 203 not in suc[204]


def test_criticidad_transitiva():
    crit = grafo.criticidad(grafo.construir_grafo(PENSUM))
    assert crit[101] == 3      # 201, 203, 301
    assert crit[103] == 3      # 202, 302, 401
    assert crit[401] == 0


def test_resumen_excluye_electivas():
    r = grafo.resumen_grafo(PENSUM)
    assert r["materias_obligatorias"] == 10
    assert r["creditos_obligatorios"] == 35
    assert r["es_aciclico"] is True
    assert r["materias_mas_criticas"][0]["codigo"] in (101, 103)


# --------------------------------------------------------------------------- #
#  OE2 — validación de cargas (restricciones duras)
# --------------------------------------------------------------------------- #
def test_carga_valida(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101, 103], [Eleccion(201, "2"), Eleccion(202, "1")])
    assert r.valida, r.errores


def test_prerrequisito_faltante(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(201, "2")])
    assert "prerrequisito" in tipos(r)


def test_prerrequisito_transitivo_no_basta_nivel(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101], [Eleccion(301, "1")])
    assert "prerrequisito" in tipos(r)


def test_correquisito_en_la_misma_carga(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101], [Eleccion(203, "1"), Eleccion(204, "1")])
    assert r.valida, r.errores


def test_correquisito_faltante(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101], [Eleccion(203, "1")])
    assert "correquisito" in tipos(r)


def test_correquisito_ya_aprobado(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101, 204], [Eleccion(203, "1")])
    assert r.valida, r.errores


def test_materia_ya_aprobada(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101], [Eleccion(101, "1")])
    assert "ya_aprobada" in tipos(r)


def test_materia_inexistente(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(999, "1")])
    assert "no_existe" in tipos(r)


def test_materia_duplicada(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(101, "1"), Eleccion(101, "1")])
    assert "duplicada" in tipos(r)


def test_materia_no_ofertada(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(103, "1")])
    assert "no_ofertada" in tipos(r)


def test_grupo_inexistente(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(101, "7")])
    assert "grupo_inexistente" in tipos(r)


def test_grupo_sin_cupo(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(102, "1")])
    assert "sin_cupo" in tipos(r)


def test_grupo_con_ceros_a_la_izquierda(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [], [Eleccion(102, "02")])
    assert r.valida, r.errores


def test_choque_mismo_horario(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101, 103], [Eleccion(201, "1"), Eleccion(102, "2"), Eleccion(202, "1")])
    assert "choque_horario" in tipos(r)  # 201-1 lunes 6-8 vs 202-1 lunes 7-9


def test_horas_contiguas_no_chocan(pensum_idx, oferta_idx):
    # 101-1 lunes 6-8 y una sesión que empieza justo a las 8 no se solapan
    g1, g2 = oferta_idx["101"].grupos[0], oferta_idx["202"].grupos[0]
    assert motor._se_cruzan(g1, g2)  # 7-9 sí se cruza con 6-8
    from tests.conftest import _g
    assert not motor._se_cruzan(g1, _g("9", 5, ("lunes", 8, 10)))


def test_supera_creditos_maximos(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101, 103], [Eleccion(201, "2"), Eleccion(202, "1")], cmax=6)
    assert "creditos_max" in tipos(r)


def test_por_debajo_del_minimo_es_advertencia(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101], [Eleccion(201, "2")])
    assert r.valida
    assert any(a["tipo"] == "creditos_min" for a in r.advertencias)


def test_sin_grupo_solo_valida_lo_academico(pensum_idx, oferta_idx):
    r = validar(pensum_idx, oferta_idx, [101], [Eleccion(201)])
    assert r.valida
    assert any(a["tipo"] == "sin_grupo" for a in r.advertencias)


# --------------------------------------------------------------------------- #
#  OE2 — generación de alternativas
# --------------------------------------------------------------------------- #
def _proponer(pensum_idx, oferta_idx, aprobadas, **kw):
    crit = grafo.criticidad(grafo.construir_grafo(PENSUM))
    return motor.proponer_cargas(pensum_idx, oferta_idx, crit, set(aprobadas), CMIN, kw.pop("cmax", CMAX), **kw)


def test_propuestas_siempre_validas(pensum_idx, oferta_idx):
    cargas = _proponer(pensum_idx, oferta_idx, [101, 103])
    assert cargas
    for c in cargas:
        elecciones = [Eleccion(m["codigo"], m["grupo"]) for m in c["materias"]]
        assert validar(pensum_idx, oferta_idx, [101, 103], elecciones).valida


def test_propuesta_respeta_tope_de_creditos(pensum_idx, oferta_idx):
    for c in _proponer(pensum_idx, oferta_idx, [101, 103], cmax=7):
        assert c["creditos"] <= 7


def test_propuesta_filtra_franja_manana(pensum_idx, oferta_idx):
    for c in _proponer(pensum_idx, oferta_idx, [101, 103], franja="mañana"):
        for m in c["materias"]:
            g = motor._buscar_grupo(oferta_idx[str(m["codigo"])], m["grupo"])
            assert all(int(s.hora_fin[:2]) <= 12 for s in g.horario)


def test_propuesta_nunca_incluye_grupos_sin_cupo(pensum_idx, oferta_idx):
    for c in _proponer(pensum_idx, oferta_idx, [101, 103, 201, 202]):
        assert 302 not in {m["codigo"] for m in c["materias"]}  # único grupo sin cupo


def test_habilitadas_excluye_electivas_por_defecto(pensum_idx):
    codigos = {m.codigo for m in motor.materias_habilitadas(pensum_idx, set())}
    assert 901 not in codigos and {101, 102, 103}.issubset(codigos)


# --------------------------------------------------------------------------- #
#  Interpretación de entradas y API
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("101, 103", {101, 103}),
        ("nivel:1", {101, 102, 103}),
        ("nivel:1-2", {101, 102, 103, 201, 202, 203, 204}),
        ("calculo diferencial; Lógica y Representación", {101, 202}),
    ],
)
def test_resolver_aprobadas(pensum_idx, texto, esperado):
    codigos, no_rec = motor.resolver_aprobadas(texto, pensum_idx)
    assert codigos == esperado and not no_rec


def test_resolver_propuesta():
    assert motor.resolver_propuesta("201:2; 202") == [Eleccion(201, "2"), Eleccion(202, None)]


def test_api_grafo_y_validar(datos_en_vivo_simulados):
    from fastapi.testclient import TestClient

    from app.main import app

    cliente = TestClient(app)
    g = cliente.get("/pensum/grafo").json()
    assert g["es_aciclico"] and g["materias_obligatorias"] == 10

    r = cliente.post(
        "/planeacion/validar",
        json={"aprobadas": [101], "propuesta": [{"codigo": 203, "grupo": "1"}]},
    ).json()
    assert r["valida"] is False and r["errores"][0]["tipo"] == "correquisito"

    p = cliente.post("/planeacion/proponer", json={"aprobadas": [101, 103]}).json()
    assert len(p) >= 1


def test_malla_incluye_requisitos_y_criticidad():
    vertices = {m["codigo"]: m for m in grafo.malla(PENSUM)}
    assert len(vertices) == len(PENSUM)
    assert {"codigo": 101, "tipo": "PRERREQ"} in vertices[201]["requisitos"]
    assert vertices[101]["dependientes"] == 3  # 201, 203 y 301 dependen de Cálculo Diferencial


def test_api_malla_y_propuesta_con_horario(datos_en_vivo_simulados):
    from fastapi.testclient import TestClient

    from app.main import app

    cliente = TestClient(app)
    m = cliente.get("/pensum/malla").json()
    assert len(m["materias"]) == len(PENSUM)

    p = cliente.post("/planeacion/proponer", json={"aprobadas": [101, 103]}).json()
    materia = p[0]["materias"][0]
    assert materia["horario"] and materia["cupos_disponibles"] > 0
