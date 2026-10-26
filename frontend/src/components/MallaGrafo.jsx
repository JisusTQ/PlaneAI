import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

import { ancestros, descendientes, disponer, etiquetaNivel, NODO, partirNombre } from "../lib/malla.js";
import { useApp } from "../lib/AppContext.jsx";

const sinTilde = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

/**
 * Malla curricular dibujada como grafo dirigido acíclico (una columna por semestre).
 * - Pasar el cursor/enfocar una materia resalta su cadena de prerrequisitos (verde) y lo que desbloquea (oro).
 * - En modo "marcar" un clic alterna la materia como aprobada.
 */
export default function MallaGrafo({ modo, color, seleccion, onSeleccion, busqueda, incluirElectivas }) {
  const { malla, estados, porCodigo, sucesores, aprobadas, alternarAprobada } = useApp();
  const layout = useMemo(() => disponer(malla.materias, { incluirElectivas }), [malla.materias, incluirElectivas]);
  const [hover, setHover] = useState(null);
  const [zoom, setZoom] = useState(1);
  const caja = useRef(null);
  const arrastre = useRef(null);

  const maxDep = useMemo(() => Math.max(1, ...malla.materias.map((m) => m.dependientes || 0)), [malla.materias]);

  const foco = hover ?? seleccion;
  const { anc, desc } = useMemo(() => {
    if (foco == null) return { anc: null, desc: null };
    return { anc: ancestros(foco, porCodigo), desc: descendientes(foco, sucesores) };
  }, [foco, porCodigo, sucesores]);

  const coincide = useMemo(() => {
    const t = sinTilde(busqueda || "").trim();
    if (!t) return null;
    return new Set(malla.materias.filter((m) => sinTilde(m.nombre).includes(t) || String(m.codigo).includes(t)).map((m) => m.codigo));
  }, [busqueda, malla.materias]);

  // Ajustar al ancho disponible al cargar
  const ajustar = () => {
    const w = caja.current?.clientWidth || 1000;
    // Ajusta al ancho, pero sin bajar de un tamaño en el que los nombres se lean.
    setZoom(Math.min(1, Math.max(window.innerWidth < 720 ? 0.62 : 0.74, (w - 8) / layout.ancho)));
  };
  useEffect(ajustar, [layout.ancho]); // eslint-disable-line react-hooks/exhaustive-deps

  // Llevar a la vista la primera coincidencia de la búsqueda
  useEffect(() => {
    if (!coincide?.size || !caja.current) return;
    const p = layout.pos.get([...coincide][0]);
    if (p) caja.current.scrollTo({ left: p.x * zoom - 40, top: p.y * zoom - 80, behavior: "smooth" });
  }, [coincide]); // eslint-disable-line react-hooks/exhaustive-deps

  // Ctrl/⌘ + rueda = zoom
  useEffect(() => {
    const el = caja.current;
    if (!el) return;
    const rueda = (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      setZoom((z) => Math.min(1.6, Math.max(0.35, z * (e.deltaY > 0 ? 0.92 : 1.08))));
    };
    el.addEventListener("wheel", rueda, { passive: false });
    return () => el.removeEventListener("wheel", rueda);
  }, []);

  // Arrastrar con el mouse para desplazarse
  const alBajar = (e) => {
    if (e.pointerType !== "mouse" || e.button !== 0) return;
    arrastre.current = { x: e.clientX, y: e.clientY, l: caja.current.scrollLeft, t: caja.current.scrollTop, movio: false };
  };
  const alMover = (e) => {
    const a = arrastre.current;
    if (!a) return;
    const dx = e.clientX - a.x, dy = e.clientY - a.y;
    if (Math.abs(dx) + Math.abs(dy) > 5) a.movio = true;
    if (a.movio) {
      caja.current.scrollLeft = a.l - dx;
      caja.current.scrollTop = a.t - dy;
    }
  };
  const alSoltar = () => setTimeout(() => (arrastre.current = null), 0);

  const activar = (codigo) => {
    if (arrastre.current?.movio) return;
    if (modo === "marcar") alternarAprobada(codigo);
    onSeleccion(codigo === seleccion && modo !== "marcar" ? null : codigo);
  };

  const claseArista = (a) => {
    if (foco == null) return coincide ? "tenue" : "";
    const enAnc = (c) => c === foco || anc.has(c);
    const enDesc = (c) => c === foco || desc.has(c);
    if (anc.has(a.de) && enAnc(a.a)) return "previa";
    if (desc.has(a.a) && enDesc(a.de)) return "siguiente";
    return "tenue";
  };

  const claseNodo = (c) => {
    if (foco != null) return c === foco ? "foco" : anc.has(c) ? "previa" : desc.has(c) ? "siguiente" : "tenue";
    if (coincide) return coincide.has(c) ? "coincide" : "tenue";
    return "";
  };

  const S = zoom;
  return (
    <div className="grafo">
      <div className="grafo-zoom" role="group" aria-label="Zoom de la malla">
        <button className="icono" onClick={() => setZoom((z) => Math.max(0.35, z - 0.12))} aria-label="Alejar"><ZoomOut size={17} /></button>
        <span className="num">{Math.round(zoom * 100)}%</span>
        <button className="icono" onClick={() => setZoom((z) => Math.min(1.6, z + 0.12))} aria-label="Acercar"><ZoomIn size={17} /></button>
        <button className="icono" onClick={ajustar} aria-label="Ajustar a la pantalla"><Maximize2 size={16} /></button>
      </div>
      <div
        ref={caja}
        className={`grafo-lienzo ${modo === "marcar" ? "marcando" : ""}`}
        onPointerDown={alBajar}
        onPointerMove={alMover}
        onPointerUp={alSoltar}
        onPointerLeave={alSoltar}
      >
        <svg width={layout.ancho * S} height={layout.alto * S} viewBox={`0 0 ${layout.ancho} ${layout.alto}`} role="group" aria-label="Malla curricular">
          {layout.niveles.map((n, i) => {
            const mats = malla.materias.filter((m) => m.nivel === n);
            const cred = mats.reduce((a, m) => a + m.creditos, 0);
            const listas = mats.filter((m) => aprobadas.has(m.codigo)).length;
            return (
              <g key={n} className="col-cab" transform={`translate(${layout.xColumna(i)}, 0)`}>
                <text x={2} y={24} className="col-titulo">{etiquetaNivel(n)}</text>
                <text x={2} y={40} className="col-meta">{cred} créditos{listas ? ` · ${listas}/${mats.length} aprobadas` : ""}</text>
              </g>
            );
          })}
          <g>
            {layout.aristas.map((a) => (
              <path key={a.id} d={a.d} className={`arista ${a.tipo} ${claseArista(a)}`} markerEnd={a.tipo === "pre" ? undefined : undefined} />
            ))}
          </g>
          {[...layout.pos.entries()].map(([codigo, p]) => {
            const m = porCodigo.get(codigo);
            const est = estados.get(codigo);
            const lineas = partirNombre(m.nombre, 22);
            const calor = (m.dependientes || 0) / maxDep;
            return (
              <g
                key={codigo}
                transform={`translate(${p.x}, ${p.y})`}
                className={`nodo ${color === "criticidad" ? "calor" : est} ${claseNodo(codigo)} ${seleccion === codigo ? "sel" : ""}`}
                style={color === "criticidad" ? { "--calor": `${Math.round(8 + calor * 82)}%` } : undefined}
                tabIndex={0}
                role="button"
                aria-pressed={modo === "marcar" ? aprobadas.has(codigo) : seleccion === codigo}
                aria-label={`${m.nombre}, ${etiquetaNivel(m.nivel)}, ${m.creditos} créditos, ${est}`}
                onMouseEnter={() => setHover(codigo)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(codigo)}
                onBlur={() => setHover(null)}
                onClick={() => activar(codigo)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    activar(codigo);
                  }
                }}
              >
                <rect width={NODO.w} height={NODO.h} rx={11} className="nodo-caja" />
                {color === "criticidad" && (
                  <rect x={10} y={NODO.h - 7} height={3} rx={1.5} width={Math.max(4, (NODO.w - 50) * calor)} className="nodo-calor" />
                )}
                <text x={12} y={lineas.length > 1 ? 22 : 30} className="nodo-texto">
                  {lineas.map((l, i) => (
                    <tspan key={i} x={12} dy={i ? 15 : 0}>{l}</tspan>
                  ))}
                </text>
                <g transform={`translate(${NODO.w - 20}, ${NODO.h / 2})`}>
                  {est === "aprobada" && color !== "criticidad" ? (
                    <motion.path
                      d="M-5 0.5 L-1.5 4 L5 -3.5"
                      className="nodo-check"
                      initial={{ pathLength: 0 }}
                      animate={{ pathLength: 1 }}
                      transition={{ duration: 0.25 }}
                    />
                  ) : (
                    <>
                      <circle r={10} className="nodo-cred-bg" />
                      <text className="nodo-cred" textAnchor="middle" dy={4}>
                        {color === "criticidad" ? m.dependientes : m.creditos}
                      </text>
                    </>
                  )}
                </g>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
