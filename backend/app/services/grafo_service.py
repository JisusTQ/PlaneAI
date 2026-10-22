"""
Modelo computable del plan de estudios como GRAFO DIRIGIDO ACÍCLICO (DAG).  [OE1]

- Vértices: materias del pensum oficial (Cursum).
- Aristas:  prerrequisito -> materia (solo PRERREQ). Los correquisitos (CORREQ)
  no imponen orden (se cursan a la vez), así que se guardan aparte.

Sobre el grafo se calcula:
- Orden topológico (algoritmo de Kahn) => si no cubre todos los vértices, hay
  un ciclo y el currículo sería inconsistente.
- Criticidad: cuántas materias dependen (directa o indirectamente) de cada una.
  Se usa para priorizar qué cursar primero.

Las funciones "puras" reciben la lista de materias, para poder probarlas sin
consultar el portal; las de la última sección usan el pensum en vivo.
"""
from __future__ import annotations

from collections import defaultdict, deque

from app.services import udea_pensum_service as pensum
from app.services.udea_pensum_service import MateriaPensum

NIVEL_ELECTIVAS = pensum.NIVEL_ELECTIVAS


# --------------------------------------------------------------------------- #
#  Construcción y algoritmos (funciones puras)
# --------------------------------------------------------------------------- #
def construir_grafo(materias: list[MateriaPensum]) -> dict[int, set[int]]:
    """Lista de adyacencia {prerrequisito: {materias que lo exigen}} (solo PRERREQ
    entre materias que existen en el pensum)."""
    codigos = {m.codigo for m in materias}
    sucesores: dict[int, set[int]] = {c: set() for c in codigos}
    for m in materias:
        for r in m.requisitos:
            if r.tipo.upper().startswith("PRE") and r.codigo in codigos:
                sucesores[r.codigo].add(m.codigo)
    return sucesores


def orden_topologico(sucesores: dict[int, set[int]]) -> tuple[list[int], list[int]]:
    """Kahn. Devuelve (orden, vertices_en_ciclo). Si la segunda lista está vacía,
    el grafo es acíclico."""
    grado = {v: 0 for v in sucesores}
    for v in sucesores:
        for w in sucesores[v]:
            grado[w] += 1

    cola = deque(sorted(v for v, g in grado.items() if g == 0))
    orden: list[int] = []
    while cola:
        v = cola.popleft()
        orden.append(v)
        for w in sorted(sucesores[v]):
            grado[w] -= 1
            if grado[w] == 0:
                cola.append(w)

    en_ciclo = sorted(v for v, g in grado.items() if g > 0)
    return orden, en_ciclo


def criticidad(sucesores: dict[int, set[int]]) -> dict[int, int]:
    """Número de materias que dependen (transitivamente) de cada materia."""
    memo: dict[int, frozenset[int]] = {}

    def descendientes(v: int, pila: frozenset[int] = frozenset()) -> frozenset[int]:
        if v in memo:
            return memo[v]
        acumulado: set[int] = set()
        for w in sucesores[v]:
            if w in pila:  # protección ante ciclos (no debería ocurrir en un DAG)
                continue
            acumulado.add(w)
            acumulado |= descendientes(w, pila | {v})
        memo[v] = frozenset(acumulado)
        return memo[v]

    return {v: len(descendientes(v)) for v in sucesores}


def resumen_grafo(materias: list[MateriaPensum], top: int = 10) -> dict:
    """Indicadores del modelo del plan de estudios (lo que se reporta para OE1)."""
    sucesores = construir_grafo(materias)
    orden, en_ciclo = orden_topologico(sucesores)
    crit = criticidad(sucesores)
    por_codigo = {m.codigo: m for m in materias}

    obligatorias = [m for m in materias if m.nivel != NIVEL_ELECTIVAS]
    por_nivel: dict[int, dict] = defaultdict(lambda: {"materias": 0, "creditos": 0})
    for m in obligatorias:
        por_nivel[m.nivel]["materias"] += 1
        por_nivel[m.nivel]["creditos"] += m.creditos

    por_tipo: dict[str, int] = defaultdict(int)
    for m in materias:
        por_tipo[m.tipo or "N/D"] += 1

    requisitos_externos = sorted(
        {
            r.codigo
            for m in materias
            for r in m.requisitos
            if r.codigo not in por_codigo
        }
    )
    correquisitos = sum(
        1 for m in materias for r in m.requisitos if r.tipo.upper().startswith("CO")
    )

    mas_criticas = sorted(
        (c for c in crit if por_codigo[c].nivel != NIVEL_ELECTIVAS),
        key=lambda c: (-crit[c], por_codigo[c].nivel, c),
    )[:top]

    return {
        "materias_totales": len(materias),
        "materias_obligatorias": len(obligatorias),
        "creditos_obligatorios": sum(m.creditos for m in obligatorias),
        "niveles": len(por_nivel),
        "por_nivel": {str(k): v for k, v in sorted(por_nivel.items())},
        "por_tipo": dict(por_tipo),
        "aristas_prerrequisito": sum(len(s) for s in sucesores.values()),
        "correquisitos": correquisitos,
        "es_aciclico": not en_ciclo,
        "materias_en_ciclo": en_ciclo,
        "requisitos_fuera_del_pensum": requisitos_externos,
        "orden_topologico_valido": len(orden) == len(sucesores),
        "materias_mas_criticas": [
            {
                "codigo": c,
                "nombre": por_codigo[c].nombre,
                "nivel": por_codigo[c].nivel,
                "dependientes": crit[c],
            }
            for c in mas_criticas
        ],
    }


# --------------------------------------------------------------------------- #
#  Acceso sobre el pensum en vivo (con la caché del servicio de pensum)
# --------------------------------------------------------------------------- #
def resumen_en_vivo(top: int = 10) -> dict:
    datos = resumen_grafo(pensum.obtener_pensum(), top=top)
    datos["version_pensum"] = pensum.version_actual()
    return datos


def criticidad_en_vivo() -> dict[int, int]:
    return criticidad(construir_grafo(pensum.obtener_pensum()))
