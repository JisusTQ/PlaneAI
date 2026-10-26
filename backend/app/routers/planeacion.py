"""Router del modelo del pensum (OE1) y del motor de validación/recomendación (OE2)."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import grafo_service as grafo
from app.services import udea_horarios_service as udea
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


def _con_detalle_grupo(materias: list[dict]) -> list[dict]:
    """Agrega horario, profesor, aula y cupos del grupo elegido a cada materia,
    para que el frontend pueda dibujar el horario semanal de la carga."""
    oferta = {m.codigo: m for m in udea.obtener_oferta()}
    for m in materias:
        g = motor._buscar_grupo(oferta.get(str(m["codigo"])), m["grupo"]) if m.get("grupo") else None
        m["horario"] = [asdict(s) for s in g.horario] if g else []
        m["profesor"] = g.profesor if g else None
        m["aula"] = g.aula if g else None
        m["cupos_disponibles"] = g.cupos_disponibles if g else None
        m["cupos_totales"] = g.cupos_totales if g else None
    return materias


@router.get("/pensum/grafo", summary="Modelo del plan de estudios como DAG (OE1)")
def pensum_grafo(top: int = 10):
    """Aciclicidad, orden topológico, conteos por nivel y materias más críticas."""
    try:
        return grafo.resumen_en_vivo(top=top)
    except Exception as exc:  # noqa: BLE001
        raise _fallo_portal(exc) from exc


@router.get("/pensum/malla", summary="Malla curricular completa: materias, requisitos y criticidad (OE1)")
def pensum_malla():
    """Vértices y aristas del DAG para dibujar la malla interactiva en el frontend."""
    try:
        return grafo.malla_en_vivo()
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
        datos = asdict(r)
        datos["materias"] = _con_detalle_grupo(datos["materias"])
    except Exception as exc:  # noqa: BLE001
        raise _fallo_portal(exc) from exc
    return datos


@router.post("/planeacion/proponer", summary="Generar cargas factibles (OE2)")
def proponer(peticion: ProponerIn):
    try:
        cargas = motor.proponer_en_vivo(
            set(peticion.aprobadas),
            peticion.creditos_max,
            peticion.franja,
            peticion.k,
            peticion.incluir_electivas,
        )
        for c in cargas:
            c["materias"] = _con_detalle_grupo(c["materias"])
    except Exception as exc:  # noqa: BLE001
        raise _fallo_portal(exc) from exc
    return cargas
