// OE4 — System Usability Scale (Brooke, 1996), versión en español.
export const ITEMS_SUS = [
  "Creo que me gustaría usar PlaneAI con frecuencia.",
  "Encontré PlaneAI innecesariamente complejo.",
  "Pensé que PlaneAI era fácil de usar.",
  "Creo que necesitaría el apoyo de alguien con conocimientos técnicos para poder usar PlaneAI.",
  "Encontré que las diferentes funciones de PlaneAI estaban bien integradas.",
  "Pensé que había demasiada inconsistencia en PlaneAI.",
  "Imagino que la mayoría de las personas aprenderían a usar PlaneAI muy rápidamente.",
  "Encontré PlaneAI muy engorroso de usar.",
  "Me sentí muy seguro usando PlaneAI.",
  "Necesité aprender muchas cosas antes de poder empezar a usar PlaneAI.",
];

export const ESCALA = [
  { v: 1, t: "Totalmente en desacuerdo" },
  { v: 2, t: "En desacuerdo" },
  { v: 3, t: "Neutral" },
  { v: 4, t: "De acuerdo" },
  { v: 5, t: "Totalmente de acuerdo" },
];

export const META_SUS = 68;
export const META_PARTICIPANTES = 15;

/** Ítems impares: respuesta − 1. Ítems pares: 5 − respuesta. Suma × 2,5. */
export function puntajeSus(respuestas) {
  const suma = respuestas.reduce((acc, r, i) => acc + (i % 2 === 0 ? r - 1 : 5 - r), 0);
  return suma * 2.5;
}

export function lecturaSus(p) {
  if (p >= 80.3) return { texto: "Excelente", tono: "ok" };
  if (p >= META_SUS) return { texto: "Por encima del promedio", tono: "ok" };
  if (p >= 51) return { texto: "Por debajo del promedio", tono: "aviso" };
  return { texto: "Deficiente", tono: "error" };
}

/** Parser de CSV (comillas dobles, comas y saltos de línea dentro de campos). */
function parsearCsv(texto) {
  const filas = [];
  let fila = [], campo = "", comillas = false;
  const t = texto.replace(/^\uFEFF/, "");
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (comillas) {
      if (c === '"' && t[i + 1] === '"') { campo += '"'; i++; }
      else if (c === '"') comillas = false;
      else campo += c;
    } else if (c === '"') comillas = true;
    else if (c === ",") { fila.push(campo); campo = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && t[i + 1] === "\n") i++;
      fila.push(campo); filas.push(fila); fila = []; campo = "";
    } else campo += c;
  }
  if (campo || fila.length) { fila.push(campo); filas.push(fila); }
  return filas.filter((f) => f.some((x) => x.trim()));
}

/**
 * Lee un CSV exportado por "Exportar CSV" (otro equipo o navegador) y devuelve
 * respuestas SUS válidas. El puntaje se recalcula a partir de los 10 ítems.
 */
export function leerCsvSus(texto) {
  const [cab, ...filas] = parsearCsv(texto);
  if (!cab) return [];
  const col = (n) => cab.findIndex((h) => h.trim().toLowerCase() === n);
  const items = Array.from({ length: 10 }, (_, i) => col(`p${i + 1}`));
  if (items.some((i) => i < 0)) throw new Error("El archivo no tiene las columnas p1 a p10 del cuestionario SUS.");
  return filas
    .map((f, n) => {
      const respuestas = items.map((i) => Number(f[i]));
      if (respuestas.some((r) => !(r >= 1 && r <= 5))) return null;
      const fecha = f[col("fecha")] || new Date().toISOString();
      return { id: Date.parse(fecha) + n || Date.now() + n, fecha, participante: (f[col("participante")] || "").trim(), respuestas, puntaje: puntajeSus(respuestas), comentario: (f[col("comentario")] || "").trim() };
    })
    .filter(Boolean);
}
