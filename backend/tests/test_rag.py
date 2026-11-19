"""Recuperación (RAG) sobre reglamento y malla, y trazabilidad de fuentes (OE3)."""
import pytest

from app.services import rag_service as rag
from app.services import udea_pensum_service as pensum

SNAPSHOT, _ = pensum.cargar_snapshot()


@pytest.fixture
def pensum_real(monkeypatch):
    monkeypatch.setattr(pensum, "obtener_pensum", lambda forzar=False: SNAPSHOT)


@pytest.mark.parametrize(
    "pregunta, articulo",
    [
        ("¿Cuántos créditos mínimo debo matricular?", "67"),
        ("¿Cuántas veces puedo cancelar una materia?", "75"),
        ("¿Qué pasa si pierdo una materia tres veces?", "136"),
        ("¿Hasta cuándo puedo cancelar un curso?", "74"),
        ("¿Con qué nota se aprueba una asignatura?", "113"),
        ("¿Puedo habilitar si saqué 1.8?", "103"),
        ("¿Qué es un correquisito?", "43"),
        ("¿Cuántas faltas puedo tener?", "78"),
        ("¿Puedo matricular dos materias que se cruzan de horario?", "68"),
        ("¿Cuándo son los ajustes de matrícula?", "73"),
        ("¿Qué promedio necesito para matrícula de honor?", "214-216"),
        ("¿Cuándo pierdo el derecho a seguir por bajo rendimiento?", "135"),
    ],
)
def test_reglamento_recupera_el_articulo_correcto(pregunta, articulo):
    top = [d.extra["articulo"] for d, _ in rag.buscar_reglamento(pregunta, k=3)]
    assert articulo in top, (pregunta, top)


def test_maximo_de_creditos_recupera_art_66():
    top = [d.extra["articulo"] for d, _ in rag.buscar_reglamento("¿Cuál es el máximo de créditos por semestre?", k=3)]
    assert "66" in top


@pytest.mark.parametrize(
    "consulta, materia",
    [
        ("¿En qué semestre se ve Bases de Datos?", "BASES DE DATOS Y LABORATORIO"),
        ("prerrequisitos de Cálculo Integral", "CÁLCULO INTEGRAL"),
        ("trabajo de grado", "TRABAJO DE GRADO"),
        ("ingeniería web", "INGENIERÍA WEB"),
    ],
)
def test_malla_recupera_la_materia(pensum_real, consulta, materia):
    assert rag.buscar_malla(consulta, k=1)[0][0].titulo == materia


def test_documento_de_malla_incluye_requisitos_y_desbloqueos(pensum_real):
    doc = rag.buscar_malla("Cálculo Diferencial", k=1)[0][0]
    assert "nivel 1" in doc.texto
    assert "Correquisitos: ÁLGEBRA Y TRIGONOMETRÍA" in doc.texto
    assert "CÁLCULO INTEGRAL" in doc.texto  # lo desbloquea


def test_herramientas_registran_fuentes(pensum_real):
    from app.services import gemini_service as g

    rag.iniciar_traza()
    texto = g.consultar_reglamento("créditos mínimos por semestre")
    g.buscar_en_malla("Bases de Datos")
    fuentes = rag.fuentes_traza()
    assert "art. 67" in texto
    tipos = {f["tipo"] for f in fuentes}
    assert tipos == {"reglamento", "pensum"}
    regl = next(f for f in fuentes if f["tipo"] == "reglamento")
    assert "art. 67" in regl["detalle"] and regl["url"].startswith("https://")


def test_sin_traza_activa_no_falla():
    rag._traza.set(None)
    rag.registrar_fuente("x", "y")
    assert rag.fuentes_traza() == []


def test_api_chat_devuelve_fuentes(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services import gemini_service as g

    def falso(mensaje, historial):
        return "Respuesta\n\n**Fuentes:** Reglamento Estudiantil, art. 66", [{"herramienta": "consultar_reglamento", "args": {}}], [
            {"tipo": "reglamento", "titulo": "Reglamento Estudiantil", "detalle": "art. 66", "url": "https://x"}
        ]

    monkeypatch.setattr(g, "responder", falso)
    d = TestClient(app).post("/chat", json={"mensaje": "¿máximo de créditos?"}).json()
    assert d["fuentes"][0]["detalle"] == "art. 66"


def test_malla_responde_preguntas_generales_del_plan(pensum_real):
    for q in ("¿Cuántos créditos necesito para graduarme?", "¿Cuántos semestres tiene el plan de estudios?"):
        doc = rag.buscar_malla(q, k=1)[0][0]
        assert doc.id == "PE-RESUMEN" and "168 créditos" in doc.texto and "10 niveles" in doc.texto


def test_malla_explica_espacios_electivos(pensum_real):
    doc = rag.buscar_malla("línea de énfasis principal", k=1)[0][0]
    assert doc.id.startswith("EE-") and "INGENIERÍA WEB" in doc.texto


@pytest.mark.parametrize(
    "consulta, doc_id, dato",
    [
        ("¿Cuál es la materia de la que más materias dependen?", "PE-CRITICAS", "ÁLGEBRA Y TRIGONOMETRÍA (30)"),
        ("¿Cuántos cursos de inglés tiene el plan?", "PE-INGLES", "5 cursos de inglés"),
    ],
)
def test_malla_responde_preguntas_de_agregacion(pensum_real, consulta, doc_id, dato):
    # Fallas P10 y P16 del banco del OE3: ninguna materia individual responde estas preguntas.
    rag._malla.update(clave=None, indice=None)
    doc = rag.buscar_malla(consulta, k=3)[0][0]
    assert doc.id == doc_id and dato in doc.texto
