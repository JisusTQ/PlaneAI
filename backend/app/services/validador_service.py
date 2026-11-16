"""
Motor DETERMINISTA de validación y recomendación de cargas académicas.  [OE2]

La IA no decide si una matrícula es válida: este módulo lo verifica con reglas
explícitas y el agente solo explica el resultado.

Restricciones duras verificadas (catálogo completo en reglas_service):
  1. La materia existe en el pensum y no está aprobada (Reglamento, art. 64).
  2. Prerrequisitos (PRERREQ) cumplidos en la historia académica (art. 42).
  3. Requisitos de créditos aprobados mínimos (PRERREQCRED del plan).
  4. Correquisitos (CORREQ) aprobados o incluidos en la misma carga (art. 43).
  5. La materia está ofertada, el grupo existe y tiene cupos.
  6. Los grupos elegidos no tienen choques de horario (art. 68).
  7. El total de créditos no supera el máximo (art. 66: 24 créditos).
(Mínimo de 8 créditos —art. 67—, tiempo parcial —art. 66— y requisitos con
código de otra versión del plan se reportan como advertencias.)

Las funciones validar_carga y proponer_cargas son puras (reciben el pensum y la
oferta) para poder probarlas con datos simulados; las versiones *_en_vivo usan
los portales de la UdeA.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import get_settings
from app.services import grafo_service as grafo
from app.services import udea_horarios_service as udea
from app.services import udea_pensum_service as pensum
from app.services.udea_horarios_service import GrupoVivo, MateriaViva
from app.services.udea_pensum_service import MateriaPensum

NIVEL_ELECTIVAS = pensum.NIVEL_ELECTIVAS
MAX_NODOS_BUSQUEDA = 20_000  # tope de exploración del generador (poda dura)
TIEMPO_COMPLETO_MIN = 14  # Reglamento Estudiantil, art. 66
# Bancos cuyo espacio en el plan se llena con UNA sola materia (no tiene sentido
# proponer dos modalidades de práctica o dos cursos alternativos de física).
BANCOS_EXCLUSIVOS = {
    "PRÁCTICA ACADÉMICA",
    "CURSO ALTERNATIVO DE FÍSICA",
    "CURSO ALTERNATIVO DE LABORATORIO INTEGRADO FÍSICA",
}


@dataclass
class Eleccion:
    codigo: int
    grupo: str | None = None  # None = solo se valida la parte académica


@dataclass
class Resultado:
    valida: bool
    creditos: int
    errores: list[dict] = field(default_factory=list)
    advertencias: list[dict] = field(default_factory=list)
    materias: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #
def _hora(h: str) -> int:
    return int(h.split(":")[0])


def _se_cruzan(g1: GrupoVivo, g2: GrupoVivo) -> list[str]:
    """Sesiones en las que dos grupos se solapan (mismo día y horas que se cruzan)."""
    cruces = []
    for s1 in g1.horario:
        for s2 in g2.horario:
            if s1.dia == s2.dia and _hora(s1.hora_inicio) < _hora(s2.hora_fin) and _hora(
                s2.hora_inicio
            ) < _hora(s1.hora_fin):
                cruces.append(f"{s1.dia} {s1.hora_inicio}-{s1.hora_fin} / {s2.hora_inicio}-{s2.hora_fin}")
    return cruces


def _en_franja(g: GrupoVivo, franja: str | None) -> bool:
    if not franja:
        return True
    f = udea.normalizar(franja)
    if f.startswith("man"):
        return all(_hora(s.hora_fin) <= 12 for s in g.horario)
    if f.startswith("tar"):
        return all(_hora(s.hora_inicio) >= 12 and _hora(s.hora_fin) <= 18 for s in g.horario)
    if f.startswith("noc"):
        return all(_hora(s.hora_inicio) >= 18 for s in g.horario)
    return True


def creditos_aprobados(pensum_idx: dict[int, MateriaPensum], aprobadas: set[int]) -> int:
    """Créditos acumulados por las materias aprobadas que existen en el pensum."""
    return sum(pensum_idx[c].creditos for c in aprobadas if c in pensum_idx)


def requisitos_academicos_cumplidos(m: MateriaPensum, aprobadas: set[int], creditos_ok: int) -> bool:
    """Prerrequisitos y requisitos de créditos (los que bloquean la matrícula)."""
    for r in m.requisitos:
        if pensum.es_prerrequisito(r) and r.codigo not in aprobadas:
            return False
        if pensum.es_req_creditos(r) and creditos_ok < r.codigo:
            return False
    return True


def _buscar_grupo(materia: MateriaViva | None, numero: str) -> GrupoVivo | None:
    if materia is None:
        return None
    objetivo = numero.strip().lstrip("0") or "0"
    for g in materia.grupos:
        if (g.numero.strip().lstrip("0") or "0") == objetivo:
            return g
    return None


# --------------------------------------------------------------------------- #
#  Validación (función pura)
# --------------------------------------------------------------------------- #
def validar_carga(
    pensum_idx: dict[int, MateriaPensum],
    oferta_idx: dict[str, MateriaViva],
    aprobadas: set[int],
    propuesta: list[Eleccion],
    creditos_min: int,
    creditos_max: int,
) -> Resultado:
    errores: list[dict] = []
    advertencias: list[dict] = []
    detalle: list[dict] = []
    elegidos: list[tuple[int, GrupoVivo]] = []
    codigos_propuesta = [e.codigo for e in propuesta]
    creditos = 0
    creditos_ok = creditos_aprobados(pensum_idx, aprobadas)

    def err(tipo: str, codigo: int | None, msg: str):
        errores.append({"tipo": tipo, "codigo": codigo, "mensaje": msg})

    vistos: set[int] = set()
    for e in propuesta:
        m = pensum_idx.get(e.codigo)
        if m is None:
            err("no_existe", e.codigo, f"La materia {e.codigo} no está en el pensum.")
            continue
        if m.codigo in vistos:
            err("duplicada", m.codigo, f"{m.nombre} aparece más de una vez en la carga.")
            continue
        vistos.add(m.codigo)
        creditos += m.creditos
        detalle.append({"codigo": m.codigo, "nombre": m.nombre, "creditos": m.creditos, "grupo": e.grupo})

        if m.codigo in aprobadas:
            err("ya_aprobada", m.codigo, f"{m.nombre} ya está aprobada.")

        for r in m.requisitos:
            nombre_req = pensum_idx[r.codigo].nombre if r.codigo in pensum_idx else str(r.codigo)
            if pensum.es_prerrequisito(r) and r.codigo not in aprobadas:
                err("prerrequisito", m.codigo, f"{m.nombre} exige haber aprobado {nombre_req} (art. 42).")
            elif pensum.es_correquisito(r) and r.codigo not in aprobadas and r.codigo not in codigos_propuesta:
                err("correquisito", m.codigo, f"{m.nombre} exige cursar a la vez (o tener aprobada) {nombre_req} (art. 43).")
            elif pensum.es_req_creditos(r) and creditos_ok < r.codigo:
                err(
                    "creditos_requisito",
                    m.codigo,
                    f"{m.nombre} exige {r.codigo} créditos aprobados y llevas {creditos_ok}.",
                )
            elif pensum.es_externo(r) and r.codigo not in aprobadas:
                advertencias.append(
                    {
                        "tipo": "requisito_externo",
                        "codigo": m.codigo,
                        "mensaje": f"{m.nombre} pide la materia {r.codigo}, que no está en la versión vigente del plan; confirma la equivalencia con tu asesor.",
                    }
                )

        ofertada = oferta_idx.get(str(m.codigo))
        if ofertada is None:
            err("no_ofertada", m.codigo, f"{m.nombre} no está ofertada este semestre.")
            continue
        if e.grupo is None:
            advertencias.append(
                {"tipo": "sin_grupo", "codigo": m.codigo, "mensaje": f"No se eligió grupo para {m.nombre}; no se verificaron cupos ni horario."}
            )
            continue
        g = _buscar_grupo(ofertada, e.grupo)
        if g is None:
            err("grupo_inexistente", m.codigo, f"{m.nombre} no tiene grupo {e.grupo} en la oferta.")
            continue
        if g.cupos_disponibles <= 0:
            err("sin_cupo", m.codigo, f"{m.nombre} grupo {g.numero} no tiene cupos disponibles.")
        elegidos.append((m.codigo, g))

    for i in range(len(elegidos)):
        for j in range(i + 1, len(elegidos)):
            (c1, g1), (c2, g2) = elegidos[i], elegidos[j]
            cruces = _se_cruzan(g1, g2)
            if cruces:
                err(
                    "choque_horario",
                    c1,
                    f"{pensum_idx[c1].nombre} (gr {g1.numero}) choca con {pensum_idx[c2].nombre} (gr {g2.numero}): {', '.join(cruces)} (art. 68).",
                )

    if creditos > creditos_max:
        err("creditos_max", None, f"La carga suma {creditos} créditos y el máximo es {creditos_max} (art. 66).")
    if propuesta and creditos < creditos_min:
        advertencias.append(
            {"tipo": "creditos_min", "codigo": None, "mensaje": f"La carga suma {creditos} créditos, por debajo del mínimo de {creditos_min} (art. 67); solo se admite por fuerza mayor o si te faltan menos créditos para terminar."}
        )
    elif propuesta and creditos < TIEMPO_COMPLETO_MIN:
        advertencias.append(
            {"tipo": "tiempo_parcial", "codigo": None, "mensaje": f"Con {creditos} créditos la matrícula es de tiempo parcial; tiempo completo es de {TIEMPO_COMPLETO_MIN} a 24 (art. 66)."}
        )

    return Resultado(valida=not errores, creditos=creditos, errores=errores, advertencias=advertencias, materias=detalle)


# --------------------------------------------------------------------------- #
#  Generación de alternativas (búsqueda con poda + ordenamiento por criticidad)
# --------------------------------------------------------------------------- #
def materias_habilitadas(
    pensum_idx: dict[int, MateriaPensum],
    aprobadas: set[int],
    incluir_electivas: bool = False,
) -> list[MateriaPensum]:
    """Materias no aprobadas cuyos prerrequisitos y requisitos de créditos ya se cumplen."""
    creditos_ok = creditos_aprobados(pensum_idx, aprobadas)
    return [
        m
        for m in pensum_idx.values()
        if m.codigo not in aprobadas
        and (incluir_electivas or m.nivel != NIVEL_ELECTIVAS)
        and requisitos_academicos_cumplidos(m, aprobadas, creditos_ok)
    ]


def proponer_cargas(
    pensum_idx: dict[int, MateriaPensum],
    oferta_idx: dict[str, MateriaViva],
    criticidad: dict[int, int],
    aprobadas: set[int],
    creditos_min: int,
    creditos_max: int,
    k: int = 3,
    franja: str | None = None,
    incluir_electivas: bool = False,
    excluir: frozenset[int] | set[int] = frozenset(),
) -> list[dict]:
    """Genera hasta k cargas distintas que cumplen TODAS las restricciones duras,
    priorizando materias críticas y de niveles bajos. `excluir`: materias que no
    deben proponerse (p. ej. las que el estudiante está cursando ahora)."""
    candidatas = []
    for m in materias_habilitadas(pensum_idx, aprobadas, incluir_electivas):
        if m.codigo in excluir:
            continue
        ofertada = oferta_idx.get(str(m.codigo))
        if not ofertada:
            continue
        grupos = [g for g in ofertada.grupos if g.cupos_disponibles > 0 and g.horario and _en_franja(g, franja)]
        if grupos:
            candidatas.append((m, grupos))
    candidatas.sort(key=lambda x: (-criticidad.get(x[0].codigo, 0), x[0].nivel, x[0].codigo))

    soluciones: dict[frozenset[int], tuple[float, list[Eleccion]]] = {}
    nodos = 0

    def puntaje(sel: list[tuple[MateriaPensum, GrupoVivo]]) -> float:
        return sum(1 + criticidad.get(m.codigo, 0) + 1 / max(m.nivel, 1) for m, _ in sel)

    def registrar(sel: list[tuple[MateriaPensum, GrupoVivo]]):
        if not sel:
            return
        clave = frozenset(m.codigo for m, _ in sel)
        p = puntaje(sel)
        if clave not in soluciones or soluciones[clave][0] < p:
            soluciones[clave] = (p, [Eleccion(m.codigo, g.numero) for m, g in sel])

    def dfs(i: int, sel: list[tuple[MateriaPensum, GrupoVivo]], creditos: int):
        nonlocal nodos
        nodos += 1
        if nodos > MAX_NODOS_BUSQUEDA:
            return
        if i == len(candidatas):
            registrar(sel)
            return
        m, grupos = candidatas[i]
        banco_ocupado = m.banco in BANCOS_EXCLUSIVOS and any(x.banco == m.banco for x, _ in sel)
        if creditos + m.creditos <= creditos_max and not banco_ocupado:
            for g in grupos:
                if all(not _se_cruzan(g, g2) for _, g2 in sel):
                    dfs(i + 1, sel + [(m, g)], creditos + m.creditos)
                    break  # un grupo compatible por materia basta para esta rama
        dfs(i + 1, sel, creditos)

    dfs(0, [], 0)

    validas: list[tuple[float, frozenset[int], Resultado]] = []
    for clave, (p, elecciones) in soluciones.items():
        r = validar_carga(pensum_idx, oferta_idx, aprobadas, elecciones, creditos_min, creditos_max)
        if r.valida:  # garantía: solo se devuelven cargas que pasan el validador
            validas.append((p, clave, r))

    # Se descartan cargas que son subconjunto estricto de otra carga válida:
    # las alternativas deben diferir en qué materias se toman, no solo en cuántas.
    claves = [c for _, c, _ in validas]
    resultado = []
    for p, clave, r in sorted(validas, key=lambda x: -x[0]):
        if any(clave < otra for otra in claves):
            continue
        resultado.append({"puntaje": round(p, 2), "creditos": r.creditos, "materias": r.materias, "advertencias": r.advertencias})
        if len(resultado) >= k:
            break
    return resultado


# --------------------------------------------------------------------------- #
#  Interpretación de entradas en texto (para la API y las herramientas del agente)
# --------------------------------------------------------------------------- #
_NIVEL_RE = re.compile(r"^nivel\s*:?\s*(\d+)\s*(?:-\s*(\d+))?$")


def resolver_aprobadas(texto: str, pensum_idx: dict[int, MateriaPensum]) -> tuple[set[int], list[str]]:
    """Acepta códigos, nombres o rangos de nivel separados por ',' o ';'.
    Ej.: "2554103, nivel:1-3, cálculo integral". Devuelve (códigos, no_reconocidos)."""
    codigos: set[int] = set()
    no_reconocidos: list[str] = []
    for token in re.split(r"[;,]", texto or ""):
        t = udea.normalizar(token)
        if not t:
            continue
        mn = _NIVEL_RE.match(t)
        if mn:
            ini = int(mn.group(1))
            fin = int(mn.group(2) or ini)
            codigos |= {m.codigo for m in pensum_idx.values() if ini <= m.nivel <= fin}
        elif t.isdigit() and int(t) in pensum_idx:
            codigos.add(int(t))
        else:
            coinc = [m for m in pensum_idx.values() if udea.normalizar(m.nombre) == t] or [
                m for m in pensum_idx.values() if t in udea.normalizar(m.nombre)
            ]
            if len(coinc) == 1:
                codigos.add(coinc[0].codigo)
            else:
                no_reconocidos.append(token.strip())
    return codigos, no_reconocidos


def resolver_propuesta(texto: str) -> list[Eleccion]:
    """"2554103:1; 2554207:3" -> [Eleccion(2554103,'1'), Eleccion(2554207,'3')]."""
    elecciones = []
    for token in re.split(r"[;,]", texto or ""):
        token = token.strip()
        if not token:
            continue
        codigo, _, grupo = token.partition(":")
        if codigo.strip().isdigit():
            elecciones.append(Eleccion(int(codigo.strip()), grupo.strip() or None))
    return elecciones


# --------------------------------------------------------------------------- #
#  Versiones en vivo
# --------------------------------------------------------------------------- #
def _indices() -> tuple[dict[int, MateriaPensum], dict[str, MateriaViva]]:
    return pensum.catalogo_por_codigo(), {m.codigo: m for m in udea.obtener_oferta()}


def _limites(creditos_max: int | None) -> tuple[int, int]:
    s = get_settings()
    return s.CREDITOS_MIN, creditos_max or s.CREDITOS_MAX


def validar_en_vivo(
    aprobadas: set[int], propuesta: list[Eleccion], creditos_max: int | None = None, cursando: set[int] | None = None
) -> Resultado:
    p_idx, o_idx = _indices()
    cmin, cmax = _limites(creditos_max)
    r = validar_carga(p_idx, o_idx, aprobadas, propuesta, cmin, cmax)
    for e in propuesta:
        if cursando and e.codigo in cursando and e.codigo not in aprobadas and e.codigo in p_idx:
            r.advertencias.append(
                {"tipo": "cursando", "codigo": e.codigo, "mensaje": f"{p_idx[e.codigo].nombre} la estás cursando este semestre; inclúyela solo si crees que no la aprobarás."}
            )
    return r


def proponer_en_vivo(
    aprobadas: set[int],
    creditos_max: int | None = None,
    franja: str | None = None,
    k: int = 3,
    incluir_electivas: bool = False,
    excluir: set[int] | None = None,
) -> list[dict]:
    p_idx, o_idx = _indices()
    cmin, cmax = _limites(creditos_max)
    return proponer_cargas(
        p_idx, o_idx, grafo.criticidad_en_vivo(), aprobadas, cmin, cmax, k=k, franja=franja,
        incluir_electivas=incluir_electivas, excluir=frozenset(excluir or ()),
    )
