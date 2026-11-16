"""Plan oficial V.5 (AF 868): estructura, cotejo y ajustes que Cursum no refleja (OE1)."""
from fastapi.testclient import TestClient

from app.services import grafo_service as grafo
from app.services import plan_service as ps
from app.services import udea_pensum_service as pensum
from app.services import validador_service as motor
from app.services.udea_horarios_service import GrupoVivo, MateriaViva, Sesion
from app.services.validador_service import Eleccion

MATERIAS, _ = pensum.cargar_snapshot()
IDX = {m.codigo: m for m in MATERIAS}


def test_plan_publicado_transcrito():
    plan = ps.plan_publicado()
    assert len(plan["espacios"]) == 55
    assert sum(e["creditos"] for e in plan["espacios"]) == plan["total_creditos"] == 168


def test_estructura_coincide_con_el_plan_oficial():
    e = ps.estructura(MATERIAS)
    assert (e["total_espacios"], e["total_creditos"], e["total_niveles"]) == (55, 168, 10)
    por_nivel = [e["niveles"][str(n)]["creditos"] for n in range(1, 11)]
    assert por_nivel == [16, 17, 17, 17, 16, 18, 18, 18, 16, 15]  # gráfico oficial AF 868
    assert all(x["opciones"] for x in e["espacios_electivos"])


def test_cotejo_supera_el_indicador_oe1():
    c = ps.cotejo(MATERIAS)
    assert c["porcentaje_espacios"] >= 95
    assert {f["espacio"] for f in c["detalle"] if not f["coincide"]} == {
        "LÓGICA Y REPRESENTACIÓN III",
        "FORMACIÓN CIUDADANA Y CONSTITUCIONAL",
    }


def test_proyecto_integrador_i_exige_80_creditos():
    assert any(pensum.es_req_creditos(r) and r.codigo == 80 for r in IDX[2508700].requisitos)
    oferta = {"2508700": MateriaViva("PI I", "2508700", [GrupoVivo("1", 30, 5, "A", "P", [Sesion("lunes", "08:00", "10:00")])])}
    pocos = {m.codigo for m in MATERIAS if m.nivel <= 2}  # 33 créditos
    r = motor.validar_carga(IDX, oferta, pocos, [Eleccion(2508700, "1")], 1, 24)
    assert not r.valida and r.errores[0]["tipo"] == "creditos_requisito"
    muchos = {m.codigo for m in MATERIAS if m.nivel <= 5}  # 83 créditos
    assert motor.validar_carga(IDX, oferta, muchos, [Eleccion(2508700, "1")], 1, 24).valida


def test_equivalencia_lectoescritura_espanol_academico():
    r = IDX[2508037].requisitos  # Motivación humana y tecnología
    assert [(x.codigo, x.tipo) for x in r] == [(2539130, "PRERREQ")]


def test_motor_no_propone_dos_practicas_academicas():
    oferta = {
        str(c): MateriaViva(str(c), str(c), [GrupoVivo("1", 30, 5, "A", "P", [Sesion(d, "08:00", "10:00")])])
        for c, d in [(2508001, "lunes"), (2508002, "martes"), (2508003, "miércoles")]
    }
    aprobadas = {m.codigo for m in MATERIAS if m.nivel != 99}  # 128 créditos
    aprobadas |= {2508020, 2508021}  # + 6 de electivas -> 134 >= 132
    crit = grafo.criticidad(grafo.construir_grafo(MATERIAS))
    cargas = motor.proponer_cargas(IDX, oferta, crit, aprobadas, 1, 24, incluir_electivas=True)
    assert cargas
    for c in cargas:
        practicas = [m for m in c["materias"] if IDX[m["codigo"]].banco == "PRÁCTICA ACADÉMICA"]
        assert len(practicas) == 1


def test_api_plan(monkeypatch):
    from app.main import app

    monkeypatch.setattr(pensum, "obtener_pensum", lambda forzar=False: MATERIAS)
    d = TestClient(app).get("/pensum/plan").json()
    assert d["estructura"]["total_creditos"] == 168 and d["cotejo"]["porcentaje_espacios"] >= 95
    m = TestClient(app).get("/pensum/malla").json()
    assert m["creditos_grado"] == 168 and len(m["espacios_electivos"]) == 11
