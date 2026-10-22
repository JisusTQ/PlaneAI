"""Router del modelo del pensum (OE1) y del motor de validación/recomendación (OE2)."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import grafo_service as grafo
from app.services import validador_service as motor

router = APIRouter(tags=["Planeación (motor determinista)"])


class EleccionIn(BaseModel):
    codigo: int
    grupo: str | None = Field(None, description="Número de grupo; si se omite solo se valida la parte académica")


class ValidarIn(BaseModel):
    aprobadas: list[int] = Field(default_factory=list, description="Códigos de materias aprobadas")
    propuesta: list[EleccionIn]
    creditos_max: int | None = None


class ProponerIn(BaseModel):
    aprobadas: list[int] = Field(default_factory=list)
    creditos_max: int | None = None
    franja: str | None = Field(None, description="manana | tarde | noche")
    k: int = Field(3, ge=1, le=5)
    incluir_electivas: bool = False


def _fallo_portal(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=f"No se pudo consultar los portales UdeA: {exc}")


@router.get("/pensum/grafo", summary="Modelo del plan de estudios como DAG (OE1)")
def pensum_grafo(top: int = 10):
    """Aciclicidad, orden topológico, conteos por nivel y materias más críticas."""
    try:
        return grafo.resumen_en_vivo(top=top)
    except Exception as exc:  # noqa: BLE001
        raise _fallo_portal(exc) from exc


@router.post("/planeacion/validar", summary="Validar una carga académica (OE2)")
def validar(peticion: ValidarIn):
    try:
        r = motor.validar_en_vivo(
            set(peticion.aprobadas),
            [motor.Eleccion(e.codigo, e.grupo) for e in peticion.propuesta],
            peticion.creditos_max,
        )
    except Exception as exc:  # noqa: BLE001
        raise _fallo_portal(exc) from exc
    return asdict(r)


@router.post("/planeacion/proponer", summary="Generar cargas factibles (OE2)")
def proponer(peticion: ProponerIn):
    try:
        return motor.proponer_en_vivo(
            set(peticion.aprobadas),
            peticion.creditos_max,
            peticion.franja,
            peticion.k,
            peticion.incluir_electivas,
        )
    except Exception as exc:  # noqa: BLE001
        raise _fallo_portal(exc) from exc
