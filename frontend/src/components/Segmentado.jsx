import { useId } from "react";
import { motion } from "framer-motion";

/** Control segmentado accesible con indicador animado. opciones: [{ v, t, Icon? }] */
export default function Segmentado({ opciones, valor, onChange, etiqueta }) {
  const id = useId();
  return (
    <div className="segmentado" role="radiogroup" aria-label={etiqueta}>
      {opciones.map(({ v, t, Icon }) => (
        <button key={String(v)} role="radio" aria-checked={valor === v} className={valor === v ? "on" : ""} onClick={() => onChange(v)}>
          {valor === v && <motion.i layoutId={id} className="seg-fondo" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
          <span>
            {Icon && <Icon size={14} />}
            {t}
          </span>
        </button>
      ))}
    </div>
  );
}
