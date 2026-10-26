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

// OE3 — banco de preguntas para medir la exactitud del asistente (editable por el equipo).
export const BANCO_INICIAL = [
  "¿Qué materias tiene el primer semestre de Ingeniería de Sistemas?",
  "¿Cuántos créditos tiene el plan de estudios en total?",
  "¿Cuántos niveles tiene el pensum?",
  "¿Cuáles son los prerrequisitos de Cálculo Integral?",
  "¿Qué materias se desbloquean al aprobar Cálculo Diferencial?",
  "¿Física Mecánica tiene algún correquisito?",
  "¿Qué materias del segundo semestre exigen haber visto Álgebra y Trigonometría?",
  "¿Cuántos créditos tiene Matemáticas Discretas?",
  "¿En qué semestre se ve Bases de Datos?",
  "¿Cuál es la materia que más materias desbloquea en el pensum?",
  "¿Qué electivas ofrece el programa?",
  "¿Puedo ver Estructuras de Datos si no he aprobado Matemáticas Discretas?",
  "¿Qué grupos de Cálculo Integral tienen cupo?",
  "¿Qué profesores dictan Matemáticas Discretas este semestre?",
  "¿En qué horario se dicta Álgebra Lineal?",
  "¿Qué materias del tercer semestre se pueden ver en la mañana?",
  "¿Hay grupos de Física Mecánica en la noche?",
  "¿Qué grupos están llenos en las materias de segundo semestre?",
  "¿En qué aula se dicta el grupo 1 de Cálculo Diferencial?",
  "¿Qué materias tienen pocos cupos disponibles?",
  "Soy de primer semestre, ¿qué puedo matricular en la mañana?",
  "Voy para tercer semestre, recomiéndame una carga sin choques.",
  "Aprobé todo primer semestre: propónme una carga de máximo 16 créditos.",
  "Voy para cuarto semestre y solo puedo estudiar en la tarde, ¿qué me sirve?",
  "Recomiéndame una carga que priorice las materias más críticas.",
  "¿Por qué me recomiendas esa materia primero?",
  "Valida esta carga: Cálculo Integral grupo 1 y Álgebra Lineal grupo 2.",
  "¿Mi propuesta tiene choques de horario?",
  "¿Puedo matricular Física Mecánica sin su laboratorio?",
  "¿Cuál es el máximo de créditos que el motor permite por semestre?",
  "Si pierdo Cálculo Integral, ¿qué materias se retrasan?",
  "¿Qué me falta para poder ver Ingeniería de Software?",
  "¿Qué materias de quinto semestre son prerrequisito de muchas otras?",
  "Ármame un horario con todas las clases antes de las 12.",
  "¿Qué combinación de grupos me deja los viernes libres?",
  "¿Cuántos créditos sumo si matriculo todo el segundo semestre?",
  "¿Qué pasa si una materia no está ofertada este semestre?",
  "¿Cómo sé que la carga que me recomiendas es válida?",
  "¿De dónde sacas la información de cupos y horarios?",
  "¿Qué diferencia hay entre prerrequisito y correquisito en el pensum?",
];
