import { useMemo } from "react";
import { motion } from "framer-motion";

import { disponer, NODO } from "../lib/malla.js";
import { useApp } from "../lib/AppContext.jsx";

/** La malla real en miniatura: el momento de entrada de la página de inicio (las aristas se trazan una vez). */
export default function MallaMini() {
  const { malla, estados } = useApp();
  const layout = useMemo(() => disponer(malla.materias), [malla.materias]);
  if (malla.estado !== "ok") return <div className="mini-placeholder" aria-hidden />;

  const top = NODO.padTop - 14;
  return (
    <svg className="malla-mini" viewBox={`0 ${top} ${layout.ancho} ${layout.alto - top}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Vista general de la malla curricular y tu avance">
      {layout.aristas.map((a, i) => (
        <motion.path
          key={a.id}
          d={a.d}
          className={`mini-arista ${a.tipo}`}
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.9, delay: 0.25 + (i % 40) * 0.02, ease: "easeOut" }}
        />
      ))}
      {[...layout.pos.entries()].map(([c, p], i) => (
        <motion.rect
          key={c}
          x={p.x}
          y={p.y}
          width={NODO.w}
          height={NODO.h}
          rx={14}
          className={`mini-nodo ${estados.get(c)}`}
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ transformOrigin: `${p.x + NODO.w / 2}px ${p.y + NODO.h / 2}px` }}
          transition={{ duration: 0.35, delay: Math.floor(p.x / (NODO.w + NODO.gapX)) * 0.06 + (i % 6) * 0.015 }}
        />
      ))}
    </svg>
  );
}
