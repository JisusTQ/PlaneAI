// Cliente HTTP del backend (FastAPI). Se quita la "/" final para evitar rutas "//chat".
export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function pedir(ruta, opciones = {}, { timeout = 90000 } = {}) {
  const control = new AbortController();
  const reloj = setTimeout(() => control.abort(), timeout);
  try {
    const res = await fetch(`${API_URL}${ruta}`, { ...opciones, signal: control.signal });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `El servidor respondió con el código ${res.status}.`);
    }
    return await res.json();
  } catch (e) {
    if (e.name === "AbortError") throw new Error("El servidor tardó demasiado en responder. Intenta de nuevo.");
    if (e instanceof TypeError) throw new Error("No hay conexión con el servidor de PlaneAI.");
    throw e;
  } finally {
    clearTimeout(reloj);
  }
}

const post = (cuerpo) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(cuerpo),
});

const soloMensajes = (historial) => historial.map((m) => ({ rol: m.rol, texto: m.texto }));

export const salud = () => pedir("/health", {}, { timeout: 8000 });

// OE1 — modelo del plan de estudios
export const obtenerMalla = () => pedir("/pensum/malla");
export const obtenerResumenGrafo = () => pedir("/pensum/grafo?top=6");

// Oferta
export const listarCursos = (nivel) => pedir(`/cursos${nivel ? `?nivel=${nivel}` : ""}`);
export const obtenerGrupos = (codigo) => pedir(`/cursos/${codigo}/grupos`);

// OE2 — motor determinista
export const proponerCargas = ({ aprobadas, creditosMax, franja, incluirElectivas }) =>
  pedir(
    "/planeacion/proponer",
    post({
      aprobadas,
      creditos_max: creditosMax || null,
      franja: franja || null,
      k: 3,
      incluir_electivas: !!incluirElectivas,
    })
  );

export const validarCarga = ({ aprobadas, propuesta, creditosMax }) =>
  pedir("/planeacion/validar", post({ aprobadas, propuesta, creditos_max: creditosMax || null }));

// OE3 — asistente conversacional
export const enviarMensaje = (mensaje, historial = []) =>
  pedir("/chat", post({ mensaje, historial: soloMensajes(historial) }), { timeout: 120000 });

export const obtenerSugerencias = (historial = []) =>
  pedir("/chat/sugerencias", post({ historial: soloMensajes(historial) }), { timeout: 30000 });
