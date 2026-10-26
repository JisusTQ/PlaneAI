import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Search, MousePointerClick, Eye, Flame, CircleDot, Upload, List, Network, Check, RefreshCw } from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { etiquetaNivel, NIVEL_ELECTIVAS } from "../lib/malla.js";
import MallaGrafo from "../components/MallaGrafo.jsx";
import PanelMateria from "../components/PanelMateria.jsx";
import ImportarHistoria from "../components/ImportarHistoria.jsx";
import Segmentado from "../components/Segmentado.jsx";

function useAncho() {
  const [w, setW] = useState(() => window.innerWidth);
  useEffect(() => {
    const f = () => setW(window.innerWidth);
    window.addEventListener("resize", f);
    return () => window.removeEventListener("resize", f);
  }, []);
  return w;
}

function MallaLista({ incluirElectivas, busqueda, onSeleccion, modo }) {
  const { malla, estados, aprobadas, alternarAprobada } = useApp();
  const t = busqueda.trim().toLowerCase();
  const niveles = [...new Set(malla.materias.map((m) => m.nivel))].filter((n) => incluirElectivas || n !== NIVEL_ELECTIVAS).sort((a, b) => a - b);
  return (
    <div className="malla-lista">
      {niveles.map((n) => {
        const mats = malla.materias.filter((m) => m.nivel === n && (!t || m.nombre.toLowerCase().includes(t) || String(m.codigo).includes(t)));
        if (!mats.length) return null;
        const listas = mats.filter((m) => aprobadas.has(m.codigo)).length;
        return (
          <section key={n} className="ml-nivel">
            <header>
              <b>{etiquetaNivel(n)}</b>
              <span className="ayuda num">{listas}/{mats.length} aprobadas</span>
            </header>
            <div className="ml-items">
              {mats.map((m) => {
                const est = estados.get(m.codigo);
                return (
                  <button
                    key={m.codigo}
                    className={`ml-item ${est}`}
                    onClick={() => (modo === "marcar" ? alternarAprobada(m.codigo) : onSeleccion(m.codigo))}
                    aria-pressed={modo === "marcar" ? aprobadas.has(m.codigo) : undefined}
                  >
                    <i className="ml-marca">{est === "aprobada" && <Check size={13} strokeWidth={3} />}</i>
                    <span>{m.nombre}</span>
                    <small className="num">{m.creditos} cr</small>
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default function Malla() {
  const { malla, cargarMalla, aprobadas, creditosAprobados, creditosTotales, habilitadas, servidor } = useApp();
  const ancho = useAncho();
  const [modo, setModo] = useState("explorar");
  const [color, setColor] = useState("estado");
  const [vistaTipo, setVistaTipo] = useState(() => (window.innerWidth < 720 ? "lista" : "grafo"));
  const [busqueda, setBusqueda] = useState("");
  const [electivas, setElectivas] = useState(false);
  const [sel, setSel] = useState(null);
  const [importar, setImportar] = useState(false);

  const resumen = useMemo(() => {
    const ob = malla.materias.filter((m) => m.nivel !== NIVEL_ELECTIVAS);
    return { total: ob.length, niveles: new Set(ob.map((m) => m.nivel)).size, aristas: malla.materias.reduce((a, m) => a + m.requisitos.length, 0) };
  }, [malla.materias]);

  return (
    <div className="vista vista-malla">
      <div className="vista-cab">
        <div>
          <h1 className="titulo-vista">Mi malla</h1>
          <p className="bajada">
            {malla.estado === "ok"
              ? `${resumen.total} materias obligatorias en ${resumen.niveles} semestres${malla.version ? `, versión ${malla.version} del pensum` : ""}. Marca lo que ya aprobaste y la malla te muestra qué puedes ver ahora.`
              : "El plan de estudios de Ingeniería de Sistemas como red de prerrequisitos."}
          </p>
        </div>
        <button className="btn primario" onClick={() => setImportar(true)} disabled={malla.estado !== "ok"}>
          <Upload size={17} /> Cargar mi historia
        </button>
      </div>

      {malla.estado === "ok" && (
        <div className="malla-resumen">
          <div><b className="num">{aprobadas.size}</b> aprobadas</div>
          <div><b className="num">{habilitadas.length}</b> disponibles para matricular</div>
          <div><b className="num">{creditosAprobados}/{creditosTotales}</b> créditos</div>
          <div className="malla-leyenda" aria-label="Leyenda">
            {color === "estado" ? (
              <>
                <span><i className="ley aprobada" /> Aprobada</span>
                <span><i className="ley habilitada" /> Disponible</span>
                <span><i className="ley bloqueada" /> Bloqueada</span>
                <span><i className="ley linea co" /> Correquisito</span>
              </>
            ) : (
              <span><i className="ley calor" /> Más oscuro = más materias dependen de ella</span>
            )}
          </div>
        </div>
      )}

      <div className="malla-barra">
        <Segmentado
          etiqueta="Modo"
          valor={modo}
          onChange={setModo}
          opciones={[
            { v: "explorar", t: "Explorar", Icon: Eye },
            { v: "marcar", t: "Marcar aprobadas", Icon: MousePointerClick },
          ]}
        />
        <Segmentado
          etiqueta="Vista"
          valor={vistaTipo}
          onChange={setVistaTipo}
          opciones={[
            { v: "grafo", t: "Red", Icon: Network },
            { v: "lista", t: "Lista", Icon: List },
          ]}
        />
        {vistaTipo === "grafo" && (
          <Segmentado
            etiqueta="Color"
            valor={color}
            onChange={setColor}
            opciones={[
              { v: "estado", t: "Mi avance", Icon: CircleDot },
              { v: "criticidad", t: "Criticidad", Icon: Flame },
            ]}
          />
        )}
        <label className="campo malla-buscar">
          <Search size={17} />
          <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar materia o código" aria-label="Buscar materia" />
        </label>
        <label className="interruptor">
          <input type="checkbox" checked={electivas} onChange={(e) => setElectivas(e.target.checked)} />
          Electivas
        </label>
      </div>

      <AnimatePresence>
        {modo === "marcar" && (
          <motion.p className="aviso-caja ok malla-tip" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            <MousePointerClick size={16} /> Toca cada materia que ya aprobaste. Se guarda automáticamente en este navegador.
          </motion.p>
        )}
      </AnimatePresence>

      {malla.estado === "cargando" && (
        <div className="malla-cargando">
          <div className="esqueleto" style={{ height: 420 }} />
          <p className="ayuda">{servidor === "despertando" ? "Activando el servidor; la primera consulta puede tardar hasta un minuto…" : "Consultando el pensum oficial…"}</p>
        </div>
      )}
      {malla.estado === "error" && (
        <div className="aviso-caja error">
          <span>No se pudo cargar la malla: {malla.error}</span>
          <button className="btn secundario chico" onClick={cargarMalla}><RefreshCw size={14} /> Reintentar</button>
        </div>
      )}

      {malla.estado === "ok" && (
        <div className={`malla-cuerpo ${sel ? "con-panel" : ""}`}>
          {vistaTipo === "grafo" ? (
            <MallaGrafo modo={modo} color={color} seleccion={sel} onSeleccion={setSel} busqueda={busqueda} incluirElectivas={electivas} />
          ) : (
            <MallaLista incluirElectivas={electivas} busqueda={busqueda} onSeleccion={setSel} modo={modo} />
          )}
          <AnimatePresence>
            {sel != null && (
              <motion.div
                key="panel"
                className="malla-panel"
                initial={ancho < 900 ? { y: "100%" } : { x: 30, opacity: 0 }}
                animate={ancho < 900 ? { y: 0 } : { x: 0, opacity: 1 }}
                exit={ancho < 900 ? { y: "100%" } : { x: 30, opacity: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 38 }}
              >
                <PanelMateria codigo={sel} onCerrar={() => setSel(null)} onIr={setSel} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      <AnimatePresence>{importar && <ImportarHistoria onCerrar={() => setImportar(false)} />}</AnimatePresence>
    </div>
  );
}
