"""
Agente Gemini con tool-calling sobre datos en vivo de la UdeA.

Herramientas:
  - RAG (rag_service): `consultar_reglamento` (Reglamento Estudiantil) y
    `buscar_en_malla` (materias del plan por nombre/tema).
  - Datos en vivo: `consultar_pensum` (materias por nivel) y
    `consultar_horarios_udea` (grupos, cupos y horarios).
  - Motor DETERMINISTA (validador_service): `proponer_cargas` y `validar_carga`;
    la IA no decide si una carga es válida, solo la explica.
Cada herramienta registra la fuente que consultó; /chat devuelve esa traza.
El SDK ejecuta el bucle agéntico (enable_automatic_function_calling).
"""
import re

import google.generativeai as genai
from google.api_core import exceptions as gexc
from google.api_core import retry as gretry

from app.config import get_settings
from app.services import rag_service as rag
from app.services import udea_horarios_service as udea
from app.services import udea_pensum_service as pensum
from app.services import validador_service as motor

settings = get_settings()

# Límites por llamada al modelo. Sin esto el SDK reintenta en silencio hasta
# 600 s cuando Gemini responde 503 ("modelo saturado"), y una pregunta (2-3
# llamadas) puede tardar varios minutos: la interfaz se rinde a los 120 s.
TIMEOUT_LLAMADA = 45
_REINTENTO = gretry.Retry(
    predicate=gretry.if_exception_type(gexc.ServiceUnavailable),
    initial=1.0,
    maximum=4.0,
    multiplier=2.0,
    timeout=15.0,
)
OPCIONES_CHAT = {"timeout": TIMEOUT_LLAMADA, "retry": _REINTENTO}
OPCIONES_SUGERENCIAS = {"timeout": 15, "retry": None}


def mensaje_seguro(exc: Exception) -> str:
    """Texto del error sin URLs ni claves (los errores de Google pueden traer ?key=...)."""
    texto = re.sub(r"https?://\S+", "[url]", str(exc))
    texto = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[clave]", texto)
    return texto[:300]


class IASaturada(Exception):
    """Gemini no respondió a tiempo o está saturado (503 / timeout)."""


class CuotaAgotada(Exception):
    """Se agotó la cuota de la API de Gemini (429)."""

# Instrucción de sistema: define el rol y las reglas del asistente.
SYSTEM_PROMPT = """Eres "PlaneAI", un asistente de planeación académica para estudiantes \
del programa de Ingeniería de Sistemas de la Universidad de Antioquia (UdeA).

Tu objetivo es ayudar a armar horarios, recomendar materias y resolver dudas sobre
el plan de estudios y el Reglamento Estudiantil. Reglas estrictas:
1. NUNCA respondas de memoria sobre la malla, la oferta o el reglamento: consulta
   siempre una herramienta y basa la respuesta solo en lo que devuelva.
   - Normas (créditos mínimos/máximos, cancelaciones, notas, habilitación,
     validación, período de prueba, faltas, ajustes...): `consultar_reglamento`.
   - Una materia concreta (nivel, créditos, requisitos, qué desbloquea):
     `buscar_en_malla`. Todas las materias de un semestre: `consultar_pensum`.
   - Grupos, cupos, horarios, profesores o aulas: `consultar_horarios_udea`
     (varias materias en UNA llamada, separadas por ";").
2. Para RECOMENDAR una carga usa SIEMPRE `proponer_cargas`. Necesitas saber qué
   materias tiene aprobadas el estudiante: pregúntalo si no lo dijo. Si solo dice
   su semestre (p. ej. "voy para cuarto"), asume aprobados los niveles anteriores
   ("nivel:1-3") y dile explícitamente que hiciste esa suposición.
3. Si el estudiante trae su PROPIA propuesta de materias/grupos, verifícala con
   `validar_carga`. Nunca afirmes que una carga es válida si el validador no lo
   confirma; si hay errores, explícalos y sugiere cómo corregirlos.
4. Las cargas que devuelven las herramientas YA cumplen prerrequisitos,
   correquisitos, créditos, cupos, choques de horario y tope de créditos: tu
   trabajo es EXPLICARLAS (por qué esas materias, en qué horario), no cambiarlas.
5. Franjas: "mañana" = antes de las 12:00, "tarde" = 12:00-18:00, "noche" = 18:00+.
6. TRAZABILIDAD: termina toda respuesta con una línea "**Fuentes:**" que liste lo
   consultado, citando los artículos exactos del reglamento (p. ej. "Reglamento
   Estudiantil, art. 66") y el plan o la oferta cuando los uses. No cites nada que
   las herramientas no hayan devuelto.
7. Si las herramientas no traen la respuesta, dilo con honestidad y sugiere
   consultar al asesor académico o a Admisiones y Registro; no inventes.
8. Responde en español, claro, breve y organizado (listas o tablas cuando ayude)."""


def _formatear_materia(m) -> list[str]:
    lineas = [f"{m.nombre} (código {m.codigo}):"]
    for g in m.grupos:
        sesiones = (
            "; ".join(f"{s.dia} {s.hora_inicio}-{s.hora_fin}" for s in g.horario)
            or "sin horario"
        )
        lineas.append(
            f"  - Grupo {g.numero}: cupos {g.cupos_disponibles}/"
            f"{g.cupos_totales}, profesor {g.profesor}, "
            f"horario [{sesiones}], aula {g.aula}."
        )
    return lineas


def consultar_horarios_udea(materia: str = "") -> str:
    """Consulta EN VIVO los grupos, cupos, horarios y profesores de la oferta
    académica vigente del programa de Ingeniería de Sistemas de la UdeA.

    Úsala siempre que necesites información de grupos, cupos disponibles,
    horarios o profesores de una o varias materias.

    Args:
        materia: Nombre (o parte) de la materia. Para consultar VARIAS materias
            de una sola vez (recomendado, p. ej. todas las de un semestre),
            sepáralas con punto y coma ";", por ejemplo
            "cálculo diferencial; álgebra y trigonometría; geometría vectorial".
            Si se deja vacío, devuelve la lista de materias disponibles.

    Returns:
        Texto con los grupos encontrados de cada materia (cupos, horario,
        profesor y aula) o la lista de materias disponibles.
    """
    try:
        if not materia.strip():
            nombres = "; ".join(m.nombre for m in udea.obtener_oferta())
            return f"Materias disponibles en la oferta vigente:\n{nombres}"

        terminos = [t.strip() for t in materia.split(";") if t.strip()]
        rag.registrar_fuente("oferta", "Oferta de cupos y horarios del semestre (MARES)", ", ".join(terminos), rag.URL_OFERTA)
        bloques: list[str] = []
        for termino in terminos:
            materias = udea.buscar_materias(termino)
            if not materias:
                bloques.append(
                    f"'{termino}': no se encontró en la oferta vigente "
                    "(puede no estar ofertada este semestre)."
                )
                continue
            for m in materias:
                bloques.append("\n".join(_formatear_materia(m)))
        return "\n\n".join(bloques)
    except Exception as exc:  # noqa: BLE001 — degradar con elegancia para el modelo
        return f"Error al consultar el portal de la UdeA: {exc}"


def _describir_requisito(r) -> str:
    if pensum.es_req_creditos(r):
        return f"{r.codigo} créditos aprobados"
    if pensum.es_externo(r):
        return f"materia {r.codigo} (de otra versión del plan)"
    return f"{pensum.nombre_de(r.codigo)} ({'correquisito' if pensum.es_correquisito(r) else 'prerrequisito'})"


def consultar_pensum(nivel: int = 0) -> str:
    """Consulta el PENSUM oficial (plan de estudios) de Ingeniería de Sistemas:
    qué materias corresponden a cada nivel y sus prerrequisitos, donde NIVEL =
    SEMESTRE (nivel 1 = primer semestre, nivel 2 = segundo, etc.).

    Úsala SIEMPRE que necesites saber qué materias le tocan a un estudiante según
    su semestre, antes de revisar cupos y horarios.

    Args:
        nivel: número de semestre (1, 2, 3, ...). Usa 99 para las electivas.
            Si se deja en 0, devuelve un resumen con cuántas materias hay por nivel.

    Returns:
        Texto con las materias del nivel solicitado (nombre, código, créditos,
        tipo y prerrequisitos) o un resumen de los niveles disponibles.
    """
    try:
        rag.registrar_fuente(
            "pensum", f"Plan de estudios v{pensum.version_actual() or ''} (Cursum)", f"nivel {nivel}" if nivel else "resumen", rag.URL_CURSUM
        )
        if not nivel:
            niveles = pensum.niveles_disponibles()
            partes = []
            for n in niveles:
                etiqueta = "electivas" if n == pensum.NIVEL_ELECTIVAS else f"semestre {n}"
                partes.append(f"nivel {n} ({etiqueta}): {len(pensum.materias_por_nivel(n))} materias")
            return "Niveles disponibles en el pensum:\n" + "\n".join(partes)

        materias = pensum.materias_por_nivel(nivel)
        if not materias:
            return f"No hay materias registradas para el nivel {nivel} en el pensum."

        etiqueta = "electivas" if nivel == pensum.NIVEL_ELECTIVAS else f"semestre {nivel}"
        lineas = [f"Materias del nivel {nivel} ({etiqueta}):"]
        for m in materias:
            req = ""
            if m.requisitos:
                detalle = ", ".join(_describir_requisito(r) for r in m.requisitos)
                req = f" Requisitos: {detalle}."
            lineas.append(
                f"  - {m.nombre} (código {m.codigo}, {m.creditos} créditos, {m.tipo}).{req}"
            )
        return "\n".join(lineas)
    except Exception as exc:  # noqa: BLE001 — degradar con elegancia para el modelo
        return f"Error al consultar el pensum de la UdeA: {exc}"


def consultar_reglamento(pregunta: str) -> str:
    """Busca en el REGLAMENTO ESTUDIANTIL de pregrado de la UdeA (Acuerdo
    Superior 1 de 1981) los artículos pertinentes a una pregunta.

    Úsala para cualquier duda normativa: créditos mínimos y máximos por semestre,
    tiempo completo o parcial, prerrequisitos y correquisitos, ajustes,
    cancelación de materias, faltas de asistencia, notas, habilitación,
    validación, período de prueba, insuficiencia académica, perder una materia
    varias veces, reingreso, cambio de programa o matrícula de honor.

    Args:
        pregunta: la duda del estudiante en lenguaje natural.

    Returns:
        Los artículos más pertinentes, cada uno con su cita exacta para usar en
        la línea de Fuentes.
    """
    try:
        hallados = rag.buscar_reglamento(pregunta, k=4)
        if not hallados:
            return "No se encontraron artículos del Reglamento Estudiantil relacionados con la pregunta."
        bloques = []
        for doc, _ in hallados:
            rag.registrar_fuente("reglamento", "Reglamento Estudiantil de Pregrado (Acuerdo Superior 1 de 1981)", f"art. {doc.extra['articulo']}", doc.url)
            bloques.append(f"[{doc.fuente}] {doc.titulo}: {doc.texto}")
        return "Artículos recuperados (cita cada uno por su número):\n\n" + "\n\n".join(bloques)
    except Exception as exc:  # noqa: BLE001
        return f"Error al consultar el reglamento: {exc}"


def buscar_en_malla(consulta: str) -> str:
    """Busca materias del PLAN DE ESTUDIOS por nombre o tema y devuelve su
    nivel (semestre), créditos, prerrequisitos, correquisitos, requisitos de
    créditos aprobados y las materias que desbloquea.

    Úsala para preguntas sobre una materia concreta: "¿en qué semestre se ve
    Bases de Datos?", "¿qué necesito para ver Ingeniería Web?", "¿qué me
    desbloquea Cálculo Diferencial?", "¿qué es el trabajo de grado?".

    Args:
        consulta: nombre (o parte) de la materia o el tema buscado.

    Returns:
        Las materias más pertinentes con su información curricular.
    """
    try:
        hallados = rag.buscar_malla(consulta, k=3)
        if not hallados:
            return f"No se encontró ninguna materia del plan relacionada con '{consulta}'."
        mejor = hallados[0][1]
        bloques = []
        for doc, puntaje in hallados:
            if puntaje < mejor * 0.6:  # descarta coincidencias débiles
                continue
            rag.registrar_fuente("pensum", f"Plan de estudios v{pensum.version_actual() or ''} (Cursum)", doc.titulo.title(), rag.URL_CURSUM)
            bloques.append(doc.texto)
        return "\n".join(bloques)
    except Exception as exc:  # noqa: BLE001
        return f"Error al consultar la malla: {exc}"


def _formatear_resultado(r) -> str:
    estado = "VÁLIDA" if r.valida else "NO VÁLIDA"
    lineas = [f"Carga {estado} — {r.creditos} créditos."]
    lineas += [f"  · {m['nombre']} (código {m['codigo']}, gr {m['grupo'] or '-'}, {m['creditos']} cr)" for m in r.materias]
    lineas += [f"  ERROR: {e['mensaje']}" for e in r.errores]
    lineas += [f"  Aviso: {a['mensaje']}" for a in r.advertencias]
    return "\n".join(lineas)


def proponer_cargas(aprobadas: str = "", max_creditos: int = 0, franja: str = "") -> str:
    """Genera con el MOTOR DETERMINISTA hasta 3 cargas académicas factibles
    (cumplen prerrequisitos, correquisitos, cupos, sin choques de horario y
    dentro del límite de créditos), priorizando las materias más críticas.

    Args:
        aprobadas: materias aprobadas separadas por coma. Acepta códigos,
            nombres o rangos de nivel, p. ej. "nivel:1-3, cálculo integral".
        max_creditos: tope de créditos deseado (0 = el máximo reglamentario).
        franja: "manana", "tarde", "noche" o vacío para cualquier horario.

    Returns:
        Texto con cada alternativa: materias, grupos, horario y créditos.
    """
    try:
        rag.registrar_fuente("motor", "Motor de validación PlaneAI (reglas R01-R11)", "generó cargas factibles")
        rag.registrar_fuente("oferta", "Oferta de cupos y horarios del semestre (MARES)", "grupos de las cargas", rag.URL_OFERTA)
        p_idx = pensum.catalogo_por_codigo()
        codigos, no_rec = motor.resolver_aprobadas(aprobadas, p_idx)
        cargas = motor.proponer_en_vivo(codigos, max_creditos or None, franja or None)
        if not cargas:
            return "El motor no encontró cargas factibles con esas condiciones."
        oferta = {m.codigo: m for m in udea.obtener_oferta()}
        bloques = [f"Materias aprobadas reconocidas: {len(codigos)}."]
        if no_rec:
            bloques.append(f"No reconocidas: {', '.join(no_rec)}.")
        for i, c in enumerate(cargas, 1):
            lineas = [f"Alternativa {i} — {c['creditos']} créditos (validada por el motor):"]
            for m in c["materias"]:
                g = motor._buscar_grupo(oferta.get(str(m["codigo"])), m["grupo"])
                ses = "; ".join(f"{s.dia} {s.hora_inicio}-{s.hora_fin}" for s in g.horario) if g else ""
                lineas.append(f"  · {m['nombre']} (código {m['codigo']}) gr {m['grupo']} [{ses}] {m['creditos']} cr")
            bloques.append("\n".join(lineas))
        return "\n\n".join(bloques)
    except Exception as exc:  # noqa: BLE001
        return f"Error en el motor de recomendación: {exc}"


def validar_carga(aprobadas: str = "", propuesta: str = "") -> str:
    """Verifica con el MOTOR DETERMINISTA si una carga es válida: prerrequisitos,
    correquisitos, oferta y cupos, choques de horario y límite de créditos.

    Args:
        aprobadas: materias aprobadas separadas por coma (códigos, nombres o
            rangos de nivel como "nivel:1-3").
        propuesta: materias a matricular como "codigo:grupo" separadas por ";",
            p. ej. "2554206:1; 2554207:3". El grupo es opcional.

    Returns:
        Veredicto (VÁLIDA / NO VÁLIDA), créditos y la lista de errores o avisos.
    """
    try:
        rag.registrar_fuente("motor", "Motor de validación PlaneAI (reglas R01-R11)", "validó una carga")
        p_idx = pensum.catalogo_por_codigo()
        codigos, no_rec = motor.resolver_aprobadas(aprobadas, p_idx)
        elecciones = motor.resolver_propuesta(propuesta)
        if not elecciones:
            return "La propuesta está vacía o mal formada: usa 'codigo:grupo; codigo:grupo'."
        texto = _formatear_resultado(motor.validar_en_vivo(codigos, elecciones))
        if no_rec:
            texto += f"\n  Aviso: no se reconocieron como aprobadas: {', '.join(no_rec)}."
        return texto
    except Exception as exc:  # noqa: BLE001
        return f"Error en el validador: {exc}"


def _api_key_valida() -> bool:
    """Comprueba que la GEMINI_API_KEY esté configurada (no es el placeholder)."""
    key = settings.GEMINI_API_KEY or ""
    return bool(key) and not key.startswith("tu_api_key")


def _a_history_gemini(historial: list[dict]) -> list[dict]:
    """Convierte el historial del frontend al formato de Gemini, que exige que
    la conversación empiece con un turno 'user' y alterne los roles."""
    h: list[dict] = []
    for m in historial:
        role = "user" if m.get("rol") == "user" else "model"
        if not h and role != "user":
            continue  # descarta el saludo inicial del asistente
        texto = (m.get("texto") or "").strip()
        if texto:
            h.append({"role": role, "parts": [texto]})
    return h


def _extraer_pasos(chat) -> list[dict]:
    """Lista las herramientas que el agente decidió invocar durante el turno."""
    pasos: list[dict] = []
    for content in chat.history:
        for part in getattr(content, "parts", []):
            fc = getattr(part, "function_call", None)
            if fc and getattr(fc, "name", None):
                args = {}
                try:
                    for k, v in fc.args.items():
                        args[k] = str(v)
                except Exception:  # noqa: BLE001
                    pass
                pasos.append({"herramienta": fc.name, "args": args})
    return pasos


HERRAMIENTAS = [consultar_reglamento, buscar_en_malla, consultar_pensum, consultar_horarios_udea, proponer_cargas, validar_carga]


def _conversar(modelo: str, mensaje: str, historial: list[dict]):
    model = genai.GenerativeModel(model_name=modelo, system_instruction=SYSTEM_PROMPT, tools=HERRAMIENTAS)
    chat = model.start_chat(history=_a_history_gemini(historial), enable_automatic_function_calling=True)
    rag.iniciar_traza()
    respuesta = chat.send_message(mensaje, request_options=OPCIONES_CHAT)
    return respuesta.text, _extraer_pasos(chat), rag.fuentes_traza()


def responder(mensaje: str, historial: list[dict] | None = None) -> tuple[str, list[dict], list[dict]]:
    """
    Responde al estudiante con el agente Gemini sobre datos en vivo de la UdeA.

    Recibe el historial previo (memoria multi-turno) y devuelve la respuesta,
    la traza de herramientas que el agente invocó y las fuentes consultadas.
    Si el modelo principal está saturado y hay GEMINI_MODEL_RESPALDO, reintenta
    una vez con ese modelo.
    Lanza ValueError (sin API key), IASaturada o CuotaAgotada.
    """
    if not _api_key_valida():
        raise ValueError(
            "La GEMINI_API_KEY no está configurada en el .env. "
            "Agrega tu clave real para habilitar el chat."
        )
    genai.configure(api_key=settings.GEMINI_API_KEY)
    modelos = [settings.GEMINI_MODEL]
    if settings.GEMINI_MODEL_RESPALDO and settings.GEMINI_MODEL_RESPALDO != settings.GEMINI_MODEL:
        modelos.append(settings.GEMINI_MODEL_RESPALDO)

    error_principal: Exception | None = None
    for modelo in modelos:
        try:
            return _conversar(modelo, mensaje, historial or [])
        except (gexc.ResourceExhausted, gexc.ServiceUnavailable, gexc.DeadlineExceeded, gexc.RetryError, TimeoutError) as exc:
            error_principal = error_principal or exc
        except gexc.GoogleAPICallError:
            # Un respaldo mal configurado (p. ej. modelo retirado, 404) no debe
            # ocultar el error del modelo principal; si es el principal, se propaga.
            if error_principal is None:
                raise
    if isinstance(error_principal, gexc.ResourceExhausted):
        raise CuotaAgotada("Se agotó por ahora la cuota gratuita de la API de Gemini. Intenta de nuevo en unos minutos.") from error_principal
    if error_principal is not None:
        raise IASaturada("El modelo de IA está saturado o no respondió a tiempo. Intenta de nuevo en un momento.") from error_principal
    raise IASaturada("No hay modelo de IA disponible.")  # pragma: no cover


_PROMPT_SUGERENCIAS = (
    "Con base en la conversación anterior, propón TRES preguntas de seguimiento "
    "breves (máximo 9 palabras), en primera persona, que el estudiante podría "
    "hacerle al asistente de planeación académica. Una por línea, sin numeración "
    "ni viñetas. Si no hay conversación previa, propón preguntas generales de "
    "planeación de semestre."
)


def sugerencias(historial: list[dict]) -> list[str]:
    """Genera hasta 3 preguntas de seguimiento contextuales (sin herramientas)."""
    if not settings.SUGERENCIAS_IA or not _api_key_valida():
        return []
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
        chat = model.start_chat(history=_a_history_gemini(historial))
        texto = chat.send_message(_PROMPT_SUGERENCIAS, request_options=OPCIONES_SUGERENCIAS).text
        opciones = [linea.strip(" -•*\t").strip() for linea in texto.splitlines()]
        return [o for o in opciones if len(o) > 4][:3]
    except Exception:  # noqa: BLE001 — las sugerencias son un extra opcional
        return []
