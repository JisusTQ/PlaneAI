"""Herramientas del agente (sin llamar al LLM) y parseo del portal de cupos."""
from app.services import gemini_service as g
from app.services import rag_service as rag
from app.services import udea_horarios_service as udea


def test_parsear_horario_portal():
    aula, ses = udea._parsear_horario("21-232 MJ6-8")
    assert aula == "21-232"
    assert [(s.dia, s.hora_inicio, s.hora_fin) for s in ses] == [("martes", "06:00", "08:00"), ("jueves", "06:00", "08:00")]


def test_parsear_html_portal():
    html = (
        "<b>Semestre:</b> 20262"
        "<tr align='center'><td align='left'>CÁLCULO INTEGRAL (2555231)</td><td>3</td><td>35</td><td>4</td>"
        "<td align='left'>18-101 LW10-12</td><td align='left'>PROFE X</td>"
    )
    [m] = udea._parsear(html)
    assert (m.codigo, m.nombre, m.grupos[0].cupos_disponibles) == ("2555231", "CÁLCULO INTEGRAL", 4)
    assert len(m.grupos[0].horario) == 2


def test_consultar_pensum_describe_requisitos(datos_en_vivo_simulados):
    rag.iniciar_traza()
    texto = g.consultar_pensum(2)
    assert "Cálculo Integral" in texto and "Cálculo Diferencial (prerrequisito)" in texto
    assert "Laboratorio de Física Mecánica (correquisito)" in texto
    assert rag.fuentes_traza()[0]["tipo"] == "pensum"
    assert "nivel 1" in g.consultar_pensum(0)


def test_consultar_horarios(datos_en_vivo_simulados):
    rag.iniciar_traza()
    texto = g.consultar_horarios_udea("cálculo integral; materia inexistente")
    assert "Grupo 2: cupos 2/30" in texto
    assert "no se encontró" in texto
    assert rag.fuentes_traza()[0]["tipo"] == "oferta"


def test_proponer_y_validar_por_herramienta(datos_en_vivo_simulados):
    rag.iniciar_traza()
    texto = g.proponer_cargas("101, 103", 0, "")
    assert "Alternativa 1" in texto and "validada por el motor" in texto
    veredicto = g.validar_carga("101", "201:1; 102:2")
    assert "VÁLIDA" in veredicto
    assert "NO VÁLIDA" in g.validar_carga("", "201:1")
    assert "mal formada" in g.validar_carga("", "")
    assert {f["tipo"] for f in rag.fuentes_traza()} >= {"motor", "oferta"}


def test_historial_para_gemini_empieza_en_usuario():
    h = g._a_history_gemini([{"rol": "bot", "texto": "Hola"}, {"rol": "user", "texto": "x"}, {"rol": "bot", "texto": "y"}])
    assert [x["role"] for x in h] == ["user", "model"]


def test_sin_api_key_se_reporta(monkeypatch):
    monkeypatch.setattr(g.settings, "GEMINI_API_KEY", "")
    try:
        g.responder("hola")
        raise AssertionError("debía fallar")
    except ValueError as e:
        assert "GEMINI_API_KEY" in str(e)
    assert g.sugerencias([]) == []
