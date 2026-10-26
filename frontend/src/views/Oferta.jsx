import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Search, X, Lock } from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { etiquetaNivel, etiquetaNivelCorta, NIVEL_ELECTIVAS } from "../lib/malla.js";
import { ListaGrupos } from "../components/Grupos.jsx";
import { itemDeGrupo } from "../components/PanelMateria.jsx";

const sinTilde = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export default function Oferta() {
  const { malla, estados, carga, setCarga } = useApp();
  const [q, setQ] = useState("");
  const [nivel, setNivel] = useState(null);
  const [soloDisponibles, setSoloDisponibles] = useState(false);
  const [sel, setSel] = useState(null);

  const niveles = useMemo(() => [...new Set(malla.materias.map((m) => m.nivel))].sort((a, b) => a - b), [malla.materias]);
  const filtradas = useMemo(() => {
    const t = sinTilde(q.trim());
    return malla.materias.filter(
      (m) =>
        (nivel == null || m.nivel === nivel) &&
        (!soloDisponibles || estados.get(m.codigo) === "habilitada") &&
        (!t || sinTilde(m.nombre).includes(t) || String(m.codigo).includes(t))
    );
  }, [malla.materias, q, nivel, soloDisponibles, estados]);

  const m = sel != null ? malla.materias.find((x) => x.codigo === sel) : null;
  const enCarga = m ? carga.find((x) => x.codigo === m.codigo) : null;
  const habilitada = m && estados.get(m.codigo) === "habilitada";

  return (
    <div className="vista">
      <div className="vista-cab">
        <div>
          <h1 className="titulo-vista">Oferta y cupos</h1>
          <p className="bajada">Grupos, horarios, profesores y cupos de este semestre, consultados en vivo en el portal de la UdeA.</p>
        </div>
      </div>

      <div className="oferta-filtros">
        <label className="campo">
          <Search size={17} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar materia o código" aria-label="Buscar materia" />
          {q && <button className="icono mini" onClick={() => setQ("")} aria-label="Borrar búsqueda"><X size={14} /></button>}
        </label>
        <label className="interruptor">
          <input type="checkbox" checked={soloDisponibles} onChange={(e) => setSoloDisponibles(e.target.checked)} />
          Solo las que puedo ver
        </label>
      </div>
      <div className="niveles-chips" role="radiogroup" aria-label="Semestre">
        <button role="radio" aria-checked={nivel == null} className={nivel == null ? "on" : ""} onClick={() => setNivel(null)}>Todas</button>
        {niveles.map((n) => (
          <button key={n} role="radio" aria-checked={nivel === n} className={nivel === n ? "on" : ""} onClick={() => setNivel(n)}>
            {n === NIVEL_ELECTIVAS ? "Electivas" : `Semestre ${n}`}
          </button>
        ))}
      </div>

      {malla.estado === "cargando" && <div className="esqueleto" style={{ height: 320 }} />}
      {malla.estado === "error" && <div className="aviso-caja error">No se pudo cargar el catálogo: {malla.error}</div>}

      {malla.estado === "ok" && (
        <div className={`oferta-cuerpo ${m ? "con-detalle" : ""}`}>
          <div className="oferta-lista">
            <p className="ayuda num">{filtradas.length} materias</p>
            {filtradas.map((x) => {
              const est = estados.get(x.codigo);
              return (
                <button key={x.codigo} className={`of-item ${sel === x.codigo ? "on" : ""}`} onClick={() => setSel(x.codigo)}>
                  <span className={`of-nivel ${est}`}>{etiquetaNivelCorta(x.nivel)}</span>
                  <span className="of-nombre">
                    <b>{x.nombre}</b>
                    <small className="num">{x.codigo}, {x.creditos} créditos</small>
                  </span>
                  {est === "aprobada" && <span className="etiqueta ok">Aprobada</span>}
                  {est === "bloqueada" && <Lock size={14} className="of-lock" aria-label="Bloqueada" />}
                </button>
              );
            })}
            {!filtradas.length && <p className="ayuda">Ninguna materia coincide. Prueba con otro nombre o quita los filtros.</p>}
          </div>

          {m ? (
              <motion.section
                key={m.codigo}
                className="oferta-detalle"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="od-cab">
                  <div>
                    <h2 className="subtitulo">{m.nombre}</h2>
                    <p className="ayuda num">{etiquetaNivel(m.nivel)}, {m.creditos} créditos, código {m.codigo}</p>
                  </div>
                  <button className="icono" onClick={() => setSel(null)} aria-label="Cerrar"><X size={19} /></button>
                </div>
                {!habilitada && estados.get(m.codigo) === "bloqueada" && (
                  <div className="aviso-caja aviso"><Lock size={16} /> Según tu historia aún no cumples los prerrequisitos; puedes consultar los grupos, pero no agregarla a tu carga.</div>
                )}
                <ListaGrupos
                  codigo={m.codigo}
                  grupoEnCarga={enCarga?.grupo}
                  onAgregar={
                    habilitada
                      ? (g) =>
                          setCarga((prev) =>
                            enCarga?.grupo === g.numero ? prev.filter((x) => x.codigo !== m.codigo) : [...prev.filter((x) => x.codigo !== m.codigo), itemDeGrupo(m, g)]
                          )
                      : undefined
                  }
                />
              </motion.section>
            ) : (
              <section className="oferta-detalle vacio-detalle" key="vacio">
                <p className="subtitulo">Elige una materia</p>
                <p className="ayuda">Verás sus grupos con los cupos disponibles en este momento. Las que puedes ver se agregan a tu carga del planificador.</p>
              </section>
            )}
        </div>
      )}
    </div>
  );
}
