import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { X, ClipboardPaste, ShieldCheck } from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { detectarCodigos, NIVEL_ELECTIVAS } from "../lib/malla.js";

/** Carga de datos: el estudiante elige su semestre o pega su historia académica (se procesa solo en el navegador). */
export default function ImportarHistoria({ onCerrar }) {
  const { malla, porCodigo, guardarAprobadas, marcarHastaNivel, aprobadas } = useApp();
  const [texto, setTexto] = useState("");
  const niveles = useMemo(() => [...new Set(malla.materias.map((m) => m.nivel))].filter((n) => n !== NIVEL_ELECTIVAS).sort((a, b) => a - b), [malla.materias]);
  const detectados = useMemo(() => detectarCodigos(texto, porCodigo), [texto, porCodigo]);

  return (
    <>
      <motion.div className="velo" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onCerrar} />
      <motion.div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-importar"
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 24, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 380, damping: 34 }}
      >
        <div className="modal-cab">
          <h2 id="titulo-importar" className="subtitulo">Tu historia académica</h2>
          <button className="icono" onClick={onCerrar} aria-label="Cerrar"><X size={20} /></button>
        </div>

        <section className="modal-seccion">
          <h3>La forma rápida: ¿para qué semestre vas?</h3>
          <p className="ayuda">Marca como aprobadas todas las materias de los semestres anteriores. Después puedes ajustar una por una en la malla.</p>
          <div className="niveles-rapidos">
            {niveles.map((n) => (
              <button key={n} className="btn secundario chico" onClick={() => { marcarHastaNivel(n); onCerrar(); }}>
                {`${n}.º`}
              </button>
            ))}
          </div>
        </section>

        <section className="modal-seccion">
          <h3>La forma exacta: pega tu historia de MARES</h3>
          <p className="ayuda">
            Copia la tabla de materias aprobadas desde el portal y pégala aquí. PlaneAI reconoce los códigos de 7 dígitos del pensum.
          </p>
          <textarea className="area" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Pega aquí el texto de tu historia académica…" />
          <div className="importar-pie">
            <span className="ayuda"><ShieldCheck size={14} /> El texto no sale de tu navegador.</span>
            <button
              className="btn primario chico"
              disabled={!detectados.size}
              onClick={() => { guardarAprobadas(new Set([...aprobadas, ...detectados])); onCerrar(); }}
            >
              <ClipboardPaste size={15} /> {detectados.size ? `Agregar ${detectados.size} materias` : "Sin códigos reconocidos"}
            </button>
          </div>
        </section>

        {aprobadas.size > 0 && (
          <button className="btn peligro chico" onClick={() => { guardarAprobadas(new Set()); onCerrar(); }}>
            Borrar mi historia ({aprobadas.size} materias)
          </button>
        )}
      </motion.div>
    </>
  );
}
