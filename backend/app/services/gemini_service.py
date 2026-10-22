"""
Agente Gemini con tool-calling sobre datos en vivo de la UdeA.

Herramientas: `consultar_pensum`, `consultar_horarios_udea`, `proponer_cargas`
y `validar_carga`. Las dos últimas delegan en el motor DETERMINISTA
(validador_service): la IA no decide si una carga es válida, solo la explica.
El SDK ejecuta el bucle agéntico (enable_automatic_function_calling).
"""
import google.generativeai as genai

from app.config import get_settings
from app.services import udea_horarios_service as udea
from app.services import udea_pensum_service as pensum
from app.services import validador_service as motor

settings = get_settings()

# Instrucción de sistema: define el rol y las reglas del asistente.
SYSTEM_PROMPT = """Eres "PlaneAI", un asistente de planeación académica para estudiantes \
del programa de Ingeniería de Sistemas de la Universidad de Antioquia (UdeA).

Tu objetivo es ayudar a armar horarios y recomendar materias. Reglas estrictas:
1. Para RECOMENDAR una carga usa SIEMPRE `proponer_cargas`. Necesitas saber qué
   materias tiene aprobadas el estudiante: pregúntalo si no lo dijo. Si solo dice
   su semestre (p. ej. "voy para cuarto"), asume aprobados los niveles anteriores
   ("nivel:1-3") y dile explícitamente que hiciste esa suposición.
2. Si el estudiante trae su PROPIA propuesta de materias/grupos, verifícala con
   `validar_carga`. Nunca afirmes que una carga es válida si el validador no lo
   confirma; si hay errores, explícalos y sugiere cómo corregirlos.
3. Las cargas que devuelven las herramientas YA cumplen prerrequisitos,
   correquisitos, cupos, choques de horario y límite de créditos: tu trabajo es
   EXPLICARLAS de forma clara (por qué esas materias, en qué horario), no cambiarlas.
4. Usa `consultar_pensum` para preguntas sobre materias, niveles y requisitos, y
   `consultar_horarios_udea` para grupos, cupos, horarios o profesores (varias
   materias en UNA llamada, separadas por ";"). NUNCA inventes datos.
5. Franjas: "mañana" = antes de las 12:00, "tarde" = 12:00-18:00, "noche" = 18:00+.
6. Responde en español, claro, breve y organizado (usa listas o tablas cuando ayude).
7. Si una herramienta devuelve un error o no encuentra datos, dilo con honestidad."""


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
                detalle = ", ".join(
                    f"{pensum.nombre_de(r.codigo)} ({r.tipo.lower()})" for r in m.requisitos
                )
                req = f" Requisitos: {detalle}."
            lineas.append(
                f"  - {m.nombre} (código {m.codigo}, {m.creditos} créditos, {m.tipo}).{req}"
            )
        return "\n".join(lineas)
    except Exception as exc:  # noqa: BLE001 — degradar con elegancia para el modelo
        return f"Error al consultar el pensum de la UdeA: {exc}"


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


def responder(mensaje: str, historial: list[dict] | None = None) -> tuple[str, list[dict]]:
    """
    Responde al estudiante con el agente Gemini sobre datos en vivo de la UdeA.

    Recibe el historial previo (memoria multi-turno) y devuelve la respuesta y
    la traza de herramientas que el agente invocó. Lanza ValueError si la API
    key no está configurada.
    """
    if not _api_key_valida():
        raise ValueError(
            "La GEMINI_API_KEY no está configurada en el .env. "
            "Agrega tu clave real para habilitar el chat."
        )

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        tools=[consultar_pensum, consultar_horarios_udea, proponer_cargas, validar_carga],
    )
    chat = model.start_chat(
        history=_a_history_gemini(historial or []),
        enable_automatic_function_calling=True,
    )
    respuesta = chat.send_message(mensaje)
    return respuesta.text, _extraer_pasos(chat)


_PROMPT_SUGERENCIAS = (
    "Con base en la conversación anterior, propón TRES preguntas de seguimiento "
    "breves (máximo 9 palabras), en primera persona, que el estudiante podría "
    "hacerle al asistente de planeación académica. Una por línea, sin numeración "
    "ni viñetas. Si no hay conversación previa, propón preguntas generales de "
    "planeación de semestre."
)


def sugerencias(historial: list[dict]) -> list[str]:
    """Genera hasta 3 preguntas de seguimiento contextuales (sin herramientas)."""
    if not _api_key_valida():
        return []
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
        chat = model.start_chat(history=_a_history_gemini(historial))
        texto = chat.send_message(_PROMPT_SUGERENCIAS).text
        opciones = [linea.strip(" -•*\t").strip() for linea in texto.splitlines()]
        return [o for o in opciones if len(o) > 4][:3]
    except Exception:  # noqa: BLE001 — las sugerencias son un extra opcional
        return []
