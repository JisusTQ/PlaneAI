"""
Recuperación aumentada por generación (RAG) sobre las fuentes oficiales.  [OE3]

Indexa dos colecciones:
  - Reglamento Estudiantil de Pregrado (app/data/reglamento_udea.json): un
    fragmento por artículo, con su cita.
  - Malla curricular: un documento por materia del pensum en vivo (nivel,
    créditos, requisitos y lo que desbloquea), reconstruido cuando cambia el pensum.

La recuperación usa BM25 (Robertson y Zaragoza, 2009) sobre texto normalizado
en español. Se eligió por ser determinista, no consumir cuota de la API del LLM
y funcionar sin servicios externos en el plan gratuito de Render; la interfaz
`buscar()` permite cambiarlo por embeddings sin tocar al agente.

También lleva la TRAZA DE FUENTES de cada respuesta: cada herramienta del agente
registra lo que consultó y /chat lo devuelve como lista `fuentes`.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from app.services import udea_pensum_service as pensum
from app.services.udea_horarios_service import normalizar

DATA = Path(__file__).resolve().parent.parent / "data"

_STOP = set(
    """a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales cuando de del desde
    donde dos el ella ellas ellos en entre era es esa esas ese eso esos esta estas este esto estos fue ha hay
    la las le les lo los mas me mi mis mucho muy ni no nos o otra otro para pero poco por porque que quien se
    ser si sin sobre son su sus tambien te tiene tienen todo todos tu tus un una uno unos y ya yo puedo puede
    debo cuanto cuantos cuantas cuanta hacer pasa sucede quiero""".split()
)


def tokens(texto: str) -> list[str]:
    """Normaliza (minúsculas, sin acentos), quita palabras vacías y aplica un
    recorte de plurales sencillo para el español."""
    salida = []
    for t in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", normalizar(texto)):
        if t in _STOP:
            continue
        if len(t) > 3 and t.endswith("s"):
            t = t[:-1]  # créditos -> credito, cruces -> cruce
            if t.endswith(("ione", "ore")):
                t = t[:-1]  # cancelaciones -> cancelacion, profesores -> profesor
        salida.append(t)
    return salida


@dataclass
class Documento:
    id: str
    titulo: str
    texto: str
    fuente: str
    url: str = ""
    extra: dict = field(default_factory=dict)


class BM25:
    def __init__(self, docs: list[Documento], campos, k1: float = 1.4, b: float = 0.7):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tf = [Counter(tokens(campos(d))) for d in docs]
        self.largo = [sum(c.values()) for c in self.tf]
        self.prom = (sum(self.largo) / len(self.largo)) if docs else 0
        df = Counter(t for c in self.tf for t in c)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def buscar(self, consulta: str, k: int = 4) -> list[tuple[Documento, float]]:
        q = tokens(consulta)
        puntajes = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                f = tf[t]
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.largo[i] / self.prom))
            if s > 0:
                puntajes.append((self.docs[i], s))
        puntajes.sort(key=lambda x: -x[1])
        return puntajes[:k]


# --------------------------------------------------------------------------- #
#  Colección 1: Reglamento Estudiantil
# --------------------------------------------------------------------------- #
_reglamento: BM25 | None = None


def _indice_reglamento() -> BM25:
    global _reglamento
    if _reglamento is None:
        datos = json.loads((DATA / "reglamento_udea.json").read_text(encoding="utf-8"))
        docs = [
            Documento(
                id=f["id"],
                titulo=f"Art. {f['articulo']} — {f['titulo']}",
                texto=f["texto"] + (f" (Modificado por {f['modificado_por']}.)" if f["modificado_por"] else ""),
                fuente=f["fuente"],
                url=f["url"],
                extra={"articulo": f["articulo"]},
            )
            for f in datos["fragmentos"]
        ]
        # El título y las palabras clave pesan doble frente al cuerpo del artículo.
        clave = {f["id"]: f["palabras_clave"] for f in datos["fragmentos"]}
        _reglamento = BM25(docs, lambda d: f"{d.titulo} {d.titulo} {clave[d.id]} {clave[d.id]} {d.texto}")
    return _reglamento


def buscar_reglamento(consulta: str, k: int = 4) -> list[tuple[Documento, float]]:
    return _indice_reglamento().buscar(consulta, k)


# --------------------------------------------------------------------------- #
#  Colección 2: malla curricular (desde el pensum)
# --------------------------------------------------------------------------- #
_malla: dict = {"clave": None, "indice": None}


def documentos_malla(materias: list[pensum.MateriaPensum]) -> list[Documento]:
    from app.services import plan_service

    est = plan_service.estructura(materias)
    espacios_por_banco: dict[str, list[str]] = {}
    for e in est["espacios_electivos"]:
        grupo = re.sub(r"\s+(I{1,3})$", "", e["nombre"]).lower()  # "línea de énfasis principal I" -> "... principal"
        grupo = "línea de énfasis" if "énfasis" in grupo else grupo
        for b in e["bancos"]:
            if grupo not in espacios_por_banco.setdefault(b, []):
                espacios_por_banco[b].append(grupo)
    idx = {m.codigo: m for m in materias}
    desbloquea: dict[int, list[str]] = {m.codigo: [] for m in materias}
    for m in materias:
        for r in m.requisitos:
            if pensum.es_prerrequisito(r) and r.codigo in desbloquea:
                desbloquea[r.codigo].append(m.nombre)

    def req(m, pred):
        return ", ".join(idx[r.codigo].nombre if r.codigo in idx else str(r.codigo) for r in m.requisitos if pred(r)) or "ninguno"

    docs = []
    for m in materias:
        if m.nivel == pensum.NIVEL_ELECTIVAS:
            usos = ", ".join(espacios_por_banco.get(m.banco, [])) or "electiva"
            nivel = f"electiva del banco {m.banco.lower()}; se cursa en: {usos}"
        else:
            nivel = f"nivel {m.nivel} (semestre {m.nivel})"
        creditos_req = [f"{r.codigo} créditos aprobados" for r in m.requisitos if pensum.es_req_creditos(r)]
        texto = (
            f"{m.nombre} (código {m.codigo}): {nivel}, {m.creditos} créditos, {m.tipo.lower()}. "
            f"Prerrequisitos: {req(m, pensum.es_prerrequisito)}. Correquisitos: {req(m, pensum.es_correquisito)}."
            + (f" Requiere {', '.join(creditos_req)}." if creditos_req else "")
            + f" Desbloquea directamente: {', '.join(desbloquea[m.codigo]) or 'ninguna'}."
        )
        docs.append(Documento(id=f"PE-{m.codigo}", titulo=m.nombre, texto=texto, fuente=f"Plan de estudios v{pensum.version_actual() or 5} (Cursum), {m.nombre}", extra={"codigo": m.codigo}))

    # Espacios electivos del plan oficial y resumen general del plan.
    for e in est["espacios_electivos"]:
        opciones = [idx[c].nombre for c in e["opciones"] if c in idx]
        texto = (
            f"{e['nombre']}: espacio electivo del nivel {e['nivel']} (semestre {e['nivel']}) de {e['creditos']} créditos en el plan V.5 "
            f"(Acuerdo de Facultad 868). Se cursa con una materia de: {', '.join(b.lower() for b in e['bancos'])}. "
            f"Opciones en Cursum: {', '.join(opciones)}."
        )
        docs.append(Documento(id=f"EE-{e['id']}", titulo=e["nombre"], texto=texto, fuente=f"Plan de estudios V.5 (AF 868), {e['nombre'].title()}"))
    por_nivel = "; ".join(f"nivel {k}: {v['creditos']} créditos" for k, v in est["niveles"].items())
    docs.append(
        Documento(
            id="PE-RESUMEN",
            titulo="RESUMEN DEL PLAN DE ESTUDIOS niveles semestres créditos totales grado duración",
            texto=(
                f"El plan de estudios V.5 de Ingeniería de Sistemas tiene {est['total_creditos']} créditos para grado, "
                f"{est['total_niveles']} niveles (semestres) y {est['total_espacios']} espacios: "
                f"{est['total_espacios'] - len(est['espacios_electivos'])} asignaturas obligatorias y {len(est['espacios_electivos'])} espacios electivos "
                f"(curso alternativo de física y su laboratorio, línea de énfasis principal I-III, línea de énfasis complementaria I-II, "
                f"electivas socio-humanísticas I-III y práctica académica de 12 créditos). Créditos por nivel: {por_nivel}."
            ),
            fuente="Plan de estudios V.5 (Acuerdo de Facultad 868) y Cursum",
        )
    )

    # Agregados que ninguna materia responde por sí sola (hallazgo de la evaluación
    # del OE3: "¿de qué materia dependen más materias?", "¿cuántos cursos de inglés?").
    from app.services import grafo_service as grafo

    crit = grafo.criticidad(grafo.construir_grafo(materias))
    obligatorias = [m for m in materias if m.nivel != pensum.NIVEL_ELECTIVAS]
    ranking = sorted(obligatorias, key=lambda m: (-crit.get(m.codigo, 0), m.nivel, m.codigo))[:8]
    docs.append(
        Documento(
            id="PE-CRITICAS",
            titulo="MATERIAS MÁS CRÍTICAS de las que más materias dependen ranking criticidad cuello de botella",
            texto=(
                "Materias de las que más materias dependen (número de materias que las exigen directa o indirectamente "
                "en el grafo de prerrequisitos): "
                + ", ".join(f"{m.nombre} ({crit.get(m.codigo, 0)})" for m in ranking)
                + ". Perder o aplazar una de ellas retrasa la mayor cantidad de materias del plan."
            ),
            fuente="Plan de estudios (grafo de prerrequisitos de PlaneAI sobre Cursum)",
        )
    )
    ingles = sorted((m for m in obligatorias if m.nombre.upper().startswith("ENGLISH")), key=lambda m: m.codigo)
    if ingles:
        docs.append(
            Documento(
                id="PE-INGLES",
                titulo="CURSOS DE INGLÉS english lengua extranjera idiomas",
                texto=(
                    f"El plan de estudios incluye {len(ingles)} cursos de inglés obligatorios: "
                    + ", ".join(f"{m.nombre} (nivel {m.nivel}, {m.creditos} créditos)" for m in ingles)
                    + "."
                ),
                fuente="Plan de estudios (Cursum), cursos de inglés",
            )
        )
    return docs


def _indice_malla() -> BM25:
    materias = pensum.obtener_pensum()
    if _malla["clave"] is not materias:
        # El nombre pesa triple: las preguntas suelen nombrar la materia.
        _malla.update(clave=materias, indice=BM25(documentos_malla(materias), lambda d: f"{d.titulo} {d.titulo} {d.titulo} {d.texto}"))
    return _malla["indice"]


def buscar_malla(consulta: str, k: int = 3) -> list[tuple[Documento, float]]:
    return _indice_malla().buscar(consulta, k)


# --------------------------------------------------------------------------- #
#  Traza de fuentes por respuesta
# --------------------------------------------------------------------------- #
_traza: ContextVar[list[dict] | None] = ContextVar("traza_fuentes", default=None)

URL_CURSUM = "https://ingenieria2.udea.edu.co/cursum"
URL_OFERTA = "https://ayudame2.udea.edu.co/php_mares/do.php?app=pub_cuposprog"


def iniciar_traza() -> None:
    _traza.set([])


def registrar_fuente(tipo: str, titulo: str, detalle: str = "", url: str = "") -> None:
    traza = _traza.get()
    if traza is None:
        return
    for f in traza:
        if f["tipo"] == tipo and f["titulo"] == titulo:
            if detalle and detalle not in f["detalle"]:
                f["detalle"] = f"{f['detalle']}; {detalle}" if f["detalle"] else detalle
            return
    traza.append({"tipo": tipo, "titulo": titulo, "detalle": detalle, "url": url})


def fuentes_traza() -> list[dict]:
    return list(_traza.get() or [])
