"""Router de evaluación (OE3): banco de preguntas y ejecución calificada contra el asistente."""
from fastapi import APIRouter, HTTPException

from app.services import evaluacion_service as ev
from app.services import gemini_service

router = APIRouter(prefix="/evaluacion", tags=["Evaluación (OE3)"])


@router.get("/banco", summary="Banco de 40 preguntas con respuesta esperada y fuente esperada")
def obtener_banco():
    return ev.banco()


@router.post("/banco/{id_}", summary="Lanza una pregunta del banco al asistente y la precalifica")
def evaluar_pregunta(id_: int):
    p = ev.pregunta(id_)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No existe la pregunta {id_}.")
    try:
        respuesta, pasos, fuentes = gemini_service.responder(p["pregunta"], [])
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Error al consultar la IA: {exc}") from exc
    return {"id": id_, "respuesta": respuesta, "pasos": pasos, "fuentes": fuentes, **ev.calificar(p, respuesta, fuentes)}
