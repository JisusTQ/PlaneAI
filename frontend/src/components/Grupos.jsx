import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { User, MapPin, Plus, Check } from "lucide-react";

import { obtenerGrupos } from "../lib/api.js";
import { DIAS, DIA_CORTO, estadoCupo, indiceDia, textoSesion } from "../lib/horario.js";

const cache = new Map();

/** Grupos en vivo de una materia, con caché por sesión. */
export function useGrupos(codigo) {
  const [estado, setEstado] = useState(() => (cache.has(codigo) ? { cargando: false, grupos: cache.get(codigo), error: null } : { cargando: true, grupos: [], error: null }));
  useEffect(() => {
    if (codigo == null) return;
    if (cache.has(codigo)) {
      setEstado({ cargando: false, grupos: cache.get(codigo), error: null });
      return;
    }
    let vivo = true;
    setEstado({ cargando: true, grupos: [], error: null });
    obtenerGrupos(codigo)
      .then((g) => {
        cache.set(codigo, g);
        vivo && setEstado({ cargando: false, grupos: g, error: null });
      })
      .catch((e) => vivo && setEstado({ cargando: false, grupos: [], error: e.message }));
    return () => {
      vivo = false;
    };
  }, [codigo]);
  return estado;
}

/** Mini franja semanal: un punto por día con clase. */
function Semana({ horario }) {
  const dias = new Set(horario.map((s) => indiceDia(s.dia)));
  return (
    <span className="semana" aria-hidden>
      {DIAS.slice(0, 6).map((d, i) => (
        <i key={d} className={dias.has(i) ? "on" : ""} title={DIA_CORTO[d]}>{DIA_CORTO[d][0]}</i>
      ))}
    </span>
  );
}

export function TarjetaGrupo({ g, onAgregar, agregado, onHover, compacto }) {
  const est = estadoCupo(g.cupos_disponibles);
  const pct = g.cupos_totales ? Math.max(0, Math.min(100, (g.cupos_disponibles / g.cupos_totales) * 100)) : 0;
  return (
    <motion.div
      layout
      className={`grupo ${compacto ? "compacto" : ""}`}
      onMouseEnter={() => onHover?.(g)}
      onMouseLeave={() => onHover?.(null)}
      onFocus={() => onHover?.(g)}
      onBlur={() => onHover?.(null)}
    >
      <div className="grupo-cab">
        <b>Grupo {g.numero}</b>
        <Semana horario={g.horario} />
      </div>
      <div className="cupos">
        <div className="cupos-barra"><i className={est} style={{ width: `${pct}%` }} /></div>
        <span className={`cupos-txt ${est}`}>
          {est === "lleno" ? "Sin cupos" : `${g.cupos_disponibles} de ${g.cupos_totales} cupos`}
        </span>
      </div>
      <div className="grupo-sesiones">
        {g.horario.length ? g.horario.map((s, i) => <span key={i}>{textoSesion(s)}</span>) : <span>Sin horario publicado</span>}
      </div>
      {!compacto && (
        <div className="grupo-datos">
          <span><User size={14} /> {g.profesor?.nombre || g.profesor || "Sin asignar"}</span>
          <span><MapPin size={14} /> {g.aula || "Aula por definir"}</span>
        </div>
      )}
      {onAgregar && (
        <button className={`btn chico ${agregado ? "secundario" : "primario"}`} onClick={() => onAgregar(g)} disabled={est === "lleno" && !agregado}>
          {agregado ? <><Check size={15} /> En tu carga</> : <><Plus size={15} /> Agregar a mi carga</>}
        </button>
      )}
    </motion.div>
  );
}

export function ListaGrupos({ codigo, onAgregar, grupoEnCarga, onHover, compacto }) {
  const { cargando, grupos, error } = useGrupos(codigo);
  if (cargando)
    return (
      <div className="grupos-lista">
        {[0, 1].map((i) => <div key={i} className="esqueleto" style={{ height: compacto ? 92 : 132 }} />)}
      </div>
    );
  if (error) return <div className="aviso-caja error">{error}</div>;
  if (!grupos.length) return <p className="ayuda">Esta materia no aparece en la oferta de este semestre.</p>;
  return (
    <div className="grupos-lista">
      {grupos.map((g) => (
        <TarjetaGrupo key={g.numero} g={g} compacto={compacto} onHover={onHover} onAgregar={onAgregar} agregado={grupoEnCarga === g.numero} />
      ))}
    </div>
  );
}
