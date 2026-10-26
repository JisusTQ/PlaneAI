import { X, Check, Lock, Unlock, MessageSquareText } from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { esCo, esPre, etiquetaNivel } from "../lib/malla.js";
import { ListaGrupos } from "./Grupos.jsx";

export function itemDeGrupo(m, g) {
  return {
    codigo: m.codigo,
    nombre: m.nombre,
    creditos: m.creditos,
    grupo: g.numero,
    horario: g.horario,
    profesor: g.profesor?.nombre ?? g.profesor ?? null,
    aula: g.aula ?? null,
    cupos_disponibles: g.cupos_disponibles,
  };
}

const ESTADO_TXT = {
  aprobada: { t: "Aprobada", c: "ok", Icon: Check },
  habilitada: { t: "Puedes matricularla", c: "oro", Icon: Unlock },
  bloqueada: { t: "Te faltan prerrequisitos", c: "", Icon: Lock },
};

export default function PanelMateria({ codigo, onCerrar, onIr }) {
  const { porCodigo, sucesores, estados, aprobadas, alternarAprobada, carga, setCarga, preguntarAlAsistente } = useApp();
  const m = porCodigo.get(codigo);
  if (!m) return null;
  const est = estados.get(codigo);
  const E = ESTADO_TXT[est];
  const pre = m.requisitos.filter(esPre);
  const co = m.requisitos.filter(esCo);
  const desbloquea = sucesores.get(codigo) || [];
  const enCarga = carga.find((x) => x.codigo === codigo);

  const Chip = ({ c }) => {
    const r = porCodigo.get(c);
    return (
      <button className={`chip-materia ${aprobadas.has(c) ? "aprobada" : ""}`} onClick={() => onIr(c)}>
        {aprobadas.has(c) && <Check size={13} />}
        {r ? r.nombre : `Código ${c} (fuera del pensum)`}
      </button>
    );
  };

  return (
    <aside className="panel-materia" aria-label={`Detalle de ${m.nombre}`}>
      <div className="pm-cab">
        <span className={`etiqueta ${E.c}`}><E.Icon size={13} /> {E.t}</span>
        <button className="icono" onClick={onCerrar} aria-label="Cerrar detalle"><X size={19} /></button>
      </div>
      <h2 className="subtitulo pm-nombre">{m.nombre}</h2>
      <p className="pm-meta num">
        {etiquetaNivel(m.nivel)}, {m.creditos} créditos, código {m.codigo}
      </p>

      <div className="pm-acciones">
        <button className={`btn ${aprobadas.has(codigo) ? "secundario" : "primario"} chico`} onClick={() => alternarAprobada(codigo)}>
          <Check size={15} /> {aprobadas.has(codigo) ? "Quitar de aprobadas" : "Marcar como aprobada"}
        </button>
        <button className="btn fantasma chico" onClick={() => preguntarAlAsistente(`¿Qué necesito para ver ${m.nombre} y qué me desbloquea?`)}>
          <MessageSquareText size={15} /> Preguntar
        </button>
      </div>

      <section className="pm-seccion">
        <h3>Prerrequisitos</h3>
        {pre.length ? <div className="chips-materia">{pre.map((r) => <Chip key={r.codigo} c={r.codigo} />)}</div> : <p className="ayuda">No tiene; puedes verla desde el inicio.</p>}
      </section>
      {co.length > 0 && (
        <section className="pm-seccion">
          <h3>Correquisitos (se ven a la vez)</h3>
          <div className="chips-materia">{co.map((r) => <Chip key={r.codigo} c={r.codigo} />)}</div>
        </section>
      )}
      <section className="pm-seccion">
        <h3>Desbloquea directamente</h3>
        {desbloquea.length ? <div className="chips-materia">{desbloquea.map((c) => <Chip key={c} c={c} />)}</div> : <p className="ayuda">Ninguna materia la exige.</p>}
        {m.dependientes > 0 && (
          <p className="pm-critica">
            <b className="num">{m.dependientes}</b> materias dependen de ella en cadena. Perderla retrasa todo ese camino.
          </p>
        )}
      </section>

      {est === "habilitada" && (
        <section className="pm-seccion">
          <h3>Grupos este semestre</h3>
          <ListaGrupos
            codigo={codigo}
            compacto
            grupoEnCarga={enCarga?.grupo}
            onAgregar={(g) =>
              setCarga((prev) =>
                enCarga?.grupo === g.numero ? prev.filter((x) => x.codigo !== codigo) : [...prev.filter((x) => x.codigo !== codigo), itemDeGrupo(m, g)]
              )
            }
          />
        </section>
      )}
    </aside>
  );
}
