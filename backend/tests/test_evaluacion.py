"""Banco de preguntas del OE3 y calificación asistida."""
from fastapi.testclient import TestClient

from app.main import app
from app.services import evaluacion_service as ev
from app.services import gemini_service as g
from app.services import rag_service as rag
from app.services import udea_pensum_service as pensum


def test_banco_tiene_40_preguntas_de_malla_y_reglamento():
    ps = ev.banco()["preguntas"]
    assert len(ps) == 40
    assert {p["categoria"] for p in ps} == {"malla", "reglamento"}
    assert len({p["id"] for p in ps}) == 40


def test_respuestas_esperadas_de_malla_coinciden_con_el_pensum():
    """Las claves de las preguntas de malla salen del plan real (snapshot v5)."""
    materias, _ = pensum.cargar_snapshot()
    oblig = [m for m in materias if m.nivel != 99]
    assert sum(m.creditos for m in oblig) == 128  # pregunta 2
    assert len({m.nivel for m in oblig}) == 9  # pregunta 3


def test_articulos_esperados_existen_en_el_corpus():
    arts = {d.extra["articulo"] for d in rag._indice_reglamento().docs}
    for p in ev.banco()["preguntas"]:
        if p["categoria"] == "reglamento":
            assert p["fuente_esperada"]["detalle"].removeprefix("art. ") in arts, p["id"]


def test_rag_recupera_el_articulo_esperado_para_cada_pregunta_del_reglamento():
    fallos = []
    for p in ev.banco()["preguntas"]:
        if p["categoria"] != "reglamento":
            continue
        top = [d.extra["articulo"] for d, _ in rag.buscar_reglamento(p["pregunta"], k=4)]
        if p["fuente_esperada"]["detalle"].removeprefix("art. ") not in top:
            fallos.append((p["id"], top))
    assert not fallos, fallos


def test_calificar_correcta_y_trazable():
    p = ev.pregunta(21)
    c = ev.calificar(p, "El máximo es 24 créditos.\n\n**Fuentes:** Reglamento, art. 66", [{"tipo": "reglamento", "detalle": "art. 66; art. 67"}])
    assert c == {"auto_correcta": True, "claves_faltantes": [], "trazable": True, "cita_en_texto": True}


def test_calificar_detecta_dato_faltante_y_sin_fuente():
    c = ev.calificar(ev.pregunta(21), "Puedes ver 20 créditos.", [])
    assert not c["auto_correcta"] and not c["trazable"]
    # "24" no debe confundirse con "2.4" ni con "124"
    assert not ev.calificar(ev.pregunta(21), "Son 124 o 2.4", [])["auto_correcta"]


def test_trazabilidad_exige_el_articulo_correcto():
    c = ev.calificar(ev.pregunta(27), "Máximo dos veces.", [{"tipo": "reglamento", "detalle": "art. 74"}])
    assert c["auto_correcta"] and not c["trazable"]


def test_resumen_indicador():
    r = ev.resumen([{"correcta": True, "trazable": True}] * 35 + [{"correcta": False, "trazable": True}] * 5)
    assert r["porcentaje_correctas"] == 87.5 and r["cumple_indicador"]


def test_api_banco_y_evaluar(monkeypatch):
    c = TestClient(app)
    assert len(c.get("/evaluacion/banco").json()["preguntas"]) == 40
    monkeypatch.setattr(g, "responder", lambda m, h: ("Son 8 créditos. **Fuentes:** art. 67", [], [{"tipo": "reglamento", "titulo": "R", "detalle": "art. 67", "url": ""}]))
    d = c.post("/evaluacion/banco/22").json()
    assert d["auto_correcta"] and d["trazable"]
    assert c.post("/evaluacion/banco/99").status_code == 404
