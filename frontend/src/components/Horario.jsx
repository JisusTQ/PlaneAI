import { motion, AnimatePresence } from "framer-motion";

import { aHoras, DIAS, DIA_CORTO, indiceDia } from "../lib/horario.js";

/** Asigna carriles a las sesiones de un día para que las que se cruzan queden lado a lado. */
function carriles(lista) {
  const orden = [...lista].sort((a, b) => aHoras(a.hora_inicio) - aHoras(b.hora_inicio));
  const res = [];
  let grupo = [], finGrupo = -1, fines = [];
  const cerrar = () => grupo.forEach((x) => (x.total = fines.length));
  for (const s of orden) {
    const ini = aHoras(s.hora_inicio), fin = aHoras(s.hora_fin);
    if (ini >= finGrupo && grupo.length) { cerrar(); grupo = []; fines = []; }
    let carril = fines.findIndex((f) => f <= ini);
    if (carril === -1) { carril = fines.length; fines.push(fin); } else fines[carril] = fin;
    const item = { ...s, carril };
    grupo.push(item); res.push(item);
    finGrupo = Math.max(finGrupo, fin);
  }
  cerrar();
  return res;
}

/**
 * Horario semanal (lunes a sábado).
 * items: [{ codigo, nombre, grupo, color, horario: [{dia, hora_inicio, hora_fin}], choque?, fantasma? }]
 */
export default function Horario({ items = [], alto = 40, compacto = false }) {
  const sesiones = items.flatMap((it) => (it.horario || []).map((s) => ({ ...s, it })));
  const usaSabado = sesiones.some((s) => indiceDia(s.dia) === 5);
  const dias = DIAS.slice(0, usaSabado ? 6 : 5);
  const desde = Math.min(7, ...sesiones.map((s) => Math.floor(aHoras(s.hora_inicio))));
  const hasta = Math.max(18, ...sesiones.map((s) => Math.ceil(aHoras(s.hora_fin))));
  const horas = Array.from({ length: hasta - desde }, (_, i) => desde + i);

  return (
    <div className={`horario ${compacto ? "compacto" : ""}`}>
      <div className="horario-grid" style={{ "--cols": dias.length, "--alto": `${alto}px`, "--filas": horas.length }}>
        <div className="horario-esquina" />
        {dias.map((d) => (
          <div key={d} className="horario-dia">{compacto ? DIA_CORTO[d] : d}</div>
        ))}
        <div className="horario-horas">
          {horas.map((h) => (
            <span key={h} style={{ height: alto }}>{String(h).padStart(2, "0")}:00</span>
          ))}
        </div>
        {dias.map((d, di) => (
          <div key={d} className="horario-col" style={{ height: horas.length * alto }}>
            <AnimatePresence>
              {carriles(sesiones.filter((s) => indiceDia(s.dia) === di))
                .map((s) => {
                  const top = (aHoras(s.hora_inicio) - desde) * alto;
                  const h = (aHoras(s.hora_fin) - aHoras(s.hora_inicio)) * alto;
                  const clave = `${s.it.codigo}-${s.it.grupo}-${s.dia}-${s.hora_inicio}-${s.it.fantasma ? "f" : ""}`;
                  return (
                    <motion.div
                      key={clave}
                      layout
                      initial={{ opacity: 0, scale: 0.94 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.94 }}
                      transition={{ duration: 0.2 }}
                      className={`bloque ${s.it.choque ? "choque" : ""} ${s.it.fantasma ? "fantasma" : ""}`}
                      style={{
                        top,
                        height: h - 3,
                        "--c": s.it.color,
                        left: `calc(${(s.carril / s.total) * 100}% + 4px)`,
                        width: `calc(${100 / s.total}% - 8px)`,
                      }}
                      title={`${s.it.nombre} · grupo ${s.it.grupo} · ${s.hora_inicio}–${s.hora_fin}`}
                    >
                      <b>{s.it.nombre}</b>
                      {h >= 56 && (
                        <small>
                          Gr {s.it.grupo} · {s.hora_inicio}–{s.hora_fin}
                        </small>
                      )}
                    </motion.div>
                  );
                })}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}
