"""Límites de tiempo, modelo de respaldo y errores claros ante fallas de Gemini."""
import pytest
from fastapi.testclient import TestClient
from google.api_core import exceptions as gexc

from app.main import app
from app.services import gemini_service as g


@pytest.fixture
def con_clave(monkeypatch):
    monkeypatch.setattr(g.settings, "GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(g.genai, "configure", lambda **k: None)


def test_llamadas_tienen_limite_de_tiempo():
    assert g.OPCIONES_CHAT["timeout"] <= 60
    assert g.OPCIONES_CHAT["retry"]._timeout <= 20  # no los 600 s por defecto del SDK


def test_saturado_sin_respaldo(monkeypatch, con_clave):
    monkeypatch.setattr(g.settings, "GEMINI_MODEL_RESPALDO", "")

    def falla(*a):
        raise gexc.ServiceUnavailable("overloaded")

    monkeypatch.setattr(g, "_conversar", falla)
    with pytest.raises(g.IASaturada):
        g.responder("hola")


def test_usa_modelo_de_respaldo(monkeypatch, con_clave):
    monkeypatch.setattr(g.settings, "GEMINI_MODEL", "principal")
    monkeypatch.setattr(g.settings, "GEMINI_MODEL_RESPALDO", "respaldo")
    usados = []

    def conversar(modelo, mensaje, historial):
        usados.append(modelo)
        if modelo == "principal":
            raise gexc.DeadlineExceeded("timeout")
        return "ok", [], []

    monkeypatch.setattr(g, "_conversar", conversar)
    assert g.responder("hola")[0] == "ok"
    assert usados == ["principal", "respaldo"]


def test_cuota_agotada(monkeypatch, con_clave):
    monkeypatch.setattr(g.settings, "GEMINI_MODEL_RESPALDO", "")
    monkeypatch.setattr(g, "_conversar", lambda *a: (_ for _ in ()).throw(gexc.ResourceExhausted("quota")))
    with pytest.raises(g.CuotaAgotada):
        g.responder("hola")


@pytest.mark.parametrize("error, codigo", [(g.IASaturada("x"), 503), (g.CuotaAgotada("x"), 429)])
def test_api_traduce_errores(monkeypatch, error, codigo):
    def falla(m, h):
        raise error

    monkeypatch.setattr(g, "responder", falla)
    assert TestClient(app).post("/chat", json={"mensaje": "hola"}).status_code == codigo


def test_error_no_expone_clave_ni_urls(monkeypatch):
    def falla(m, h):
        raise RuntimeError("400 POST https://generativelanguage.googleapis.com/v1beta/x?key=AIzaSyABCDEFGHIJKLMNOPQRSTUV123: bad")

    monkeypatch.setattr(g, "responder", falla)
    detalle = TestClient(app).post("/chat", json={"mensaje": "hola"}).json()["detail"]
    assert "AIza" not in detalle and "key=" not in detalle and "https://" not in detalle
