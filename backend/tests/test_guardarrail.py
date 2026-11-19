"""Guardarraíl del agente: ninguna respuesta sustantiva sale sin consultar herramientas."""
from types import SimpleNamespace as NS

import pytest
from google.api_core import exceptions as gexc

from app.services import gemini_service as g


class ChatFalso:
    def __init__(self, modelo, history):
        self.modelo = modelo
        self.history = list(history)

    def send_message(self, mensaje, request_options=None, tool_config=None):
        self.modelo.configs.append(tool_config)
        if self.modelo.decidir(tool_config) == "herramienta":
            llamada = NS(name="proponer_cargas", args={"aprobadas": "nivel:1-3"})
            self.history.append(NS(parts=[NS(function_call=llamada)]))
            return NS(text="carga del motor")
        return NS(text="carga inventada")


class ModeloFalso:
    def __init__(self, decidir):
        self.decidir = decidir
        self.configs = []

    def start_chat(self, history, enable_automatic_function_calling):
        assert enable_automatic_function_calling
        return ChatFalso(self, history)


@pytest.fixture
def modelo(monkeypatch):
    def fabricar(decidir):
        falso = ModeloFalso(decidir)
        monkeypatch.setattr(g.genai, "GenerativeModel", lambda **k: falso)
        return falso

    return fabricar


def test_si_usa_herramientas_no_se_repite(modelo):
    falso = modelo(lambda cfg: "herramienta")
    texto, pasos, _ = g._conversar("m", "voy para cuarto semestre, propónme un horario", [])
    assert texto == "carga del motor" and pasos[0]["herramienta"] == "proponer_cargas"
    assert falso.configs == [None]


def test_sin_herramientas_se_repite_con_llamada_obligatoria(modelo):
    falso = modelo(lambda cfg: "herramienta" if cfg else "texto")
    historial = [{"rol": "user", "texto": "¿qué grupos tiene Física Mecánica?"}, {"rol": "bot", "texto": "Grupo 1..."}]
    texto, pasos, _ = g._conversar("m", "¿Podría ver otras opciones de materias?", historial)
    assert texto == "carga del motor"
    assert [p["herramienta"] for p in pasos] == ["proponer_cargas"]
    assert falso.configs == [None, g.FORZAR_HERRAMIENTA]


@pytest.mark.parametrize("mensaje", ["¡Hola!", "muchas gracias", "[Contexto del estudiante, enviado por la app: materias aprobadas (códigos): 2554206]\n\nGracias"])
def test_saludos_y_agradecimientos_no_fuerzan_herramientas(modelo, mensaje):
    falso = modelo(lambda cfg: "texto")
    assert g._conversar("m", mensaje, [])[0] == "carga inventada"
    assert falso.configs == [None]


def test_si_el_modelo_no_admite_el_modo_forzado_conserva_la_respuesta(modelo):
    def decidir(cfg):
        if cfg:
            raise gexc.InvalidArgument("function calling mode not supported")
        return "texto"

    falso = modelo(decidir)
    texto, pasos, _ = g._conversar("m", "¿cuántos créditos puedo matricular?", [])
    assert texto == "carga inventada" and pasos == []
    assert falso.configs == [None, g.FORZAR_HERRAMIENTA]


@pytest.mark.parametrize("mensaje, esperado", [
    ("hola", True),
    ("Buenos días", True),
    ("ok, gracias!", True),
    ("¿y los correquisitos?", False),
    ("hola, ¿cuántos créditos puedo ver?", False),
    ("voy para cuarto semestre, propónme un horario en la mañana", False),
])
def test_deteccion_de_charla(mensaje, esperado):
    assert g._es_charla(mensaje) is esperado
