// Utilidades de horario: días, horas, choques y colores por materia.
export const DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
export const DIA_CORTO = { lunes: "Lun", martes: "Mar", miércoles: "Mié", jueves: "Jue", viernes: "Vie", sábado: "Sáb", domingo: "Dom" };

const sinTilde = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
export const indiceDia = (dia) => DIAS.findIndex((d) => sinTilde(d) === sinTilde(dia || ""));

export const aHoras = (h) => {
  const [hh, mm = "0"] = String(h).split(":");
  return Number(hh) + Number(mm) / 60;
};

export const COLORES = ["#1F8A5B", "#B8860B", "#2F6FA3", "#8A4FA0", "#5B6BBF", "#22918E", "#6B7F2A", "#B04A78"];
export const colorDe = (i) => COLORES[i % COLORES.length];

/** Sesiones que se cruzan entre dos horarios. */
export function cruces(h1 = [], h2 = []) {
  const res = [];
  for (const a of h1)
    for (const b of h2)
      if (indiceDia(a.dia) === indiceDia(b.dia) && aHoras(a.hora_inicio) < aHoras(b.hora_fin) && aHoras(b.hora_inicio) < aHoras(a.hora_fin))
        res.push([a, b]);
  return res;
}

/** Códigos de materias que tienen algún choque dentro de la carga. */
export function codigosEnChoque(items) {
  const set = new Set();
  for (let i = 0; i < items.length; i++)
    for (let j = i + 1; j < items.length; j++)
      if (cruces(items[i].horario, items[j].horario).length) {
        set.add(items[i].codigo);
        set.add(items[j].codigo);
      }
  return set;
}

export const textoSesion = (s) => `${DIA_CORTO[s.dia] ?? s.dia} ${s.hora_inicio}–${s.hora_fin}`;

export function estadoCupo(disponibles) {
  if (disponibles == null) return "nd";
  if (disponibles <= 0) return "lleno";
  if (disponibles <= 5) return "bajo";
  return "ok";
}
