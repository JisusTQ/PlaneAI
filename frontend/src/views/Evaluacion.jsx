import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Trash2, CheckCircle2, XCircle, Play, Loader2, RotateCcw, ClipboardList, BarChart3, MessagesSquare, Upload } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { evaluarPregunta, obtenerBanco } from "../lib/api.js";
import { ESCALA, ITEMS_SUS, lecturaSus, META_PARTICIPANTES, META_SUS, puntajeSus, leerCsvSus } from "../lib/evaluacion.js";
import { descargarCsv, escribir, leer } from "../lib/storage.js";
import Segmentado from "../components/Segmentado.jsx";

function Medidor({ valor }) {
  const r = 70, c = Math.PI * r;
  const pct = Math.max(0, Math.min(100, valor)) / 100;
  const meta = META_SUS / 100;
  const ang = Math.PI * (1 - meta);
  return (
    <svg className="medidor-sus" viewBox="0 0 180 104" role="img" aria-label={`Puntaje SUS ${valor}`}>
      <path d="M20 94 A70 70 0 0 1 160 94" className="ms-pista" />
      <motion.path d="M20 94 A70 70 0 0 1 160 94" className="ms-arco" strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct) }} transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }} />
      <line x1={90 + Math.cos(ang) * 58} y1={94 - Math.sin(ang) * 58} x2={90 + Math.cos(ang) * 82} y2={94 - Math.sin(ang) * 82} className="ms-meta" />
      <text x="90" y="86" textAnchor="middle" className="ms-valor num">{valor.toFixed(1).replace(".", ",")}</text>
    </svg>
  );
}

function Cuestionario({ onGuardar }) {
  const [resp, setResp] = useState(Array(10).fill(null));
  const [participante, setParticipante] = useState("");
  const [comentario, setComentario] = useState("");
  const [resultado, setResultado] = useState(null);
  const completas = resp.every((r) => r != null);

  if (resultado != null) {
    const l = lecturaSus(resultado);
    return (
      <motion.div className="sus-resultado" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
        <Medidor valor={resultado} />
        <p className="subtitulo">Gracias. Respuesta guardada.</p>
        <p className={`etiqueta ${l.tono}`}>{l.texto}</p>
        <p className="ayuda">La meta del proyecto es un promedio de al menos {META_SUS} con {META_PARTICIPANTES} estudiantes.</p>
        <button className="btn primario" onClick={() => { setResultado(null); setResp(Array(10).fill(null)); setParticipante(""); setComentario(""); }}>
          <RotateCcw size={16} /> Siguiente participante
        </button>
      </motion.div>
    );
  }

  return (
    <div className="sus">
      <p className="bajada">
        Responde según tu experiencia con PlaneAI. No hay respuestas correctas; marca la primera impresión que tengas en cada afirmación.
      </p>
      <label className="campo sus-participante">
        <input value={participante} onChange={(e) => setParticipante(e.target.value)} placeholder="Código del participante (opcional, p. ej. P07)" aria-label="Código del participante" />
      </label>
      <ol className="sus-items">
        {ITEMS_SUS.map((item, i) => (
          <li key={i} className={resp[i] != null ? "respondida" : ""}>
            <p>{item}</p>
            <div className="likert" role="radiogroup" aria-label={item}>
              {ESCALA.map(({ v, t }) => (
                <button key={v} role="radio" aria-checked={resp[i] === v} className={resp[i] === v ? "on" : ""} onClick={() => setResp((r) => r.map((x, j) => (j === i ? v : x)))} title={t}>
                  <b>{v}</b>
                  <small>{t}</small>
                </button>
              ))}
            </div>
          </li>
        ))}
      </ol>
      <label className="sus-coment">
        <span>¿Qué cambiarías o qué te gustó? (opcional)</span>
        <textarea className="area" value={comentario} onChange={(e) => setComentario(e.target.value)} />
      </label>
      <div className="sus-pie">
        <span className="ayuda num">{resp.filter((r) => r != null).length} de 10 respondidas</span>
        <button
          className="btn primario"
          disabled={!completas}
          onClick={() => {
            const p = puntajeSus(resp);
            onGuardar({ id: Date.now(), fecha: new Date().toISOString(), participante: participante.trim(), respuestas: resp, puntaje: p, comentario: comentario.trim() });
            setResultado(p);
          }}
        >
          Enviar respuestas
        </button>
      </div>
    </div>
  );
}

function Importar({ onImportar }) {
  const ref = useRef(null);
  const [msg, setMsg] = useState(null);
  return (
    <>
      <input
        ref={ref}
        type="file"
        accept=".csv,text/csv"
        hidden
        onChange={async (e) => {
          const archivo = e.target.files?.[0];
          e.target.value = "";
          if (!archivo) return;
          try {
            const nuevas = leerCsvSus(await archivo.text());
            setMsg(`${onImportar(nuevas)} respuestas nuevas importadas.`);
          } catch (err) {
            setMsg(err.message);
          }
        }}
      />
      <button className="btn secundario" onClick={() => ref.current?.click()}><Upload size={16} /> Importar CSV</button>
      {msg && <span className="ayuda">{msg}</span>}
    </>
  );
}

function Resultados({ lista, onBorrar, onImportar }) {
  if (!lista.length)
    return (
      <div className="vacio">
        <BarChart3 size={24} />
        <p className="subtitulo">Aún no hay respuestas en este equipo</p>
        <p>Las sesiones guiadas de prueba se registran aquí. Si las sesiones se hicieron en varios computadores, importa aquí el CSV exportado en cada uno.</p>
        <div className="res-acciones"><Importar onImportar={onImportar} /></div>
      </div>
    );
  const prom = lista.reduce((a, x) => a + x.puntaje, 0) / lista.length;
  const sobre = lista.filter((x) => x.puntaje >= META_SUS).length;
  const cumple = prom >= META_SUS && lista.length >= META_PARTICIPANTES;
  return (
    <div className="resultados">
      <div className="res-resumen">
        <Medidor valor={prom} />
        <div className="res-datos">
          <p><b className="num">{lista.length}</b> de {META_PARTICIPANTES} participantes</p>
          <div className="res-barra"><i style={{ width: `${Math.min(100, (lista.length / META_PARTICIPANTES) * 100)}%` }} /></div>
          <p><b className="num">{sobre}</b> respuestas iguales o superiores a {META_SUS}</p>
          <p className={`etiqueta ${cumple ? "ok" : "aviso"}`}>{cumple ? "Indicador del OE4 cumplido" : "Indicador del OE4 aún en curso"}</p>
        </div>
      </div>
      <div className="tabla-scroll">
        <table className="tabla">
          <thead>
            <tr><th>Participante</th><th>Fecha</th><th>Puntaje</th><th>Comentario</th><th /></tr>
          </thead>
          <tbody>
            {lista.map((x, i) => (
              <tr key={x.id}>
                <td>{x.participante || `P${String(lista.length - i).padStart(2, "0")}`}</td>
                <td className="num">{new Date(x.fecha).toLocaleDateString("es-CO")}</td>
                <td className="num"><span className={`etiqueta ${x.puntaje >= META_SUS ? "ok" : "aviso"}`}>{x.puntaje.toFixed(1).replace(".", ",")}</span></td>
                <td className="td-coment">{x.comentario || "—"}</td>
                <td><button className="icono mini" onClick={() => onBorrar(x.id)} aria-label="Borrar respuesta"><Trash2 size={14} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="res-acciones">
        <button
          className="btn secundario"
          onClick={() =>
            descargarCsv("planeai-sus.csv", [
              ["participante", "fecha", ...ITEMS_SUS.map((_, i) => `p${i + 1}`), "puntaje_sus", "comentario"],
              ...lista.map((x) => [x.participante, x.fecha, ...x.respuestas, x.puntaje, x.comentario]),
            ])
          }
        >
          <Download size={16} /> Exportar CSV
        </button>
        <Importar onImportar={onImportar} />
        <span className="ayuda">Las respuestas se guardan en este navegador; expórtalas al terminar las sesiones y únelas importando los CSV de los demás equipos.</span>
      </div>
    </div>
  );
}

function Banco() {
  // Estado por pregunta: respuesta del asistente, fuentes, precalificación y veredicto del equipo.
  const [banco, setBanco] = useState(null);
  const [errorBanco, setErrorBanco] = useState(null);
  const [estado, setEstadoState] = useState(() => leer("banco-v2", {}));
  const setEstado = (fn) => setEstadoState((p) => { const n = fn(p); escribir("banco-v2", n); return n; });
  const [corriendo, setCorriendo] = useState(null);
  const [todas, setTodas] = useState(false);
  const [abierta, setAbierta] = useState(null);
  const [filtro, setFiltro] = useState("todas");

  useEffect(() => {
    obtenerBanco().then((d) => setBanco(d.preguntas)).catch((e) => setErrorBanco(e.message));
  }, []);

  async function correr(p) {
    setCorriendo(p.id);
    try {
      const d = await evaluarPregunta(p.id);
      setEstado((s) => ({ ...s, [p.id]: { respuesta: d.respuesta, fuentes: d.fuentes || [], trazable: d.trazable, auto: d.auto_correcta, faltan: d.claves_faltantes, correcta: d.auto_correcta } }));
    } catch (e) {
      setEstado((s) => ({ ...s, [p.id]: { respuesta: `Error: ${e.message}`, fuentes: [], trazable: false, auto: false, faltan: [], correcta: null } }));
    } finally {
      setCorriendo(null);
    }
  }

  async function correrTodas() {
    setTodas(true);
    for (const p of banco) {
      if (estado[p.id]?.respuesta && !estado[p.id].respuesta.startsWith("Error")) continue;
      await correr(p);
      await new Promise((r) => setTimeout(r, 6000)); // respeta la cuota gratuita de la API
    }
    setTodas(false);
  }

  if (errorBanco) return <div className="vacio"><p className="subtitulo">No se pudo cargar el banco</p><p>{errorBanco}</p></div>;
  if (!banco) return <div className="vacio"><Loader2 size={22} className="gira" /><p>Cargando banco de preguntas…</p></div>;

  const filas = banco.map((p) => ({ ...p, ...(estado[p.id] || {}) }));
  const respondidas = filas.filter((p) => p.respuesta);
  const evaluadas = filas.filter((p) => p.correcta != null);
  const correctas = evaluadas.filter((p) => p.correcta).length;
  const trazables = respondidas.filter((p) => p.trazable).length;
  const pct = evaluadas.length ? Math.round((correctas / evaluadas.length) * 1000) / 10 : null;
  const visibles = filas.filter((p) => filtro === "todas" || p.categoria === filtro);
  const marcar = (id, v) => setEstado((s) => ({ ...s, [id]: { ...s[id], correcta: v } }));

  return (
    <div className="banco">
      <p className="bajada">
        Banco de 40 preguntas sobre la malla y el Reglamento Estudiantil (OE3). Cada pregunta se lanza al asistente; el sistema precalifica si la respuesta trae los datos esperados y la fuente correcta, y el equipo confirma el veredicto comparando con la respuesta esperada.
      </p>
      <div className="banco-resumen">
        <div><b className="num">{evaluadas.length}/{banco.length}</b><span>evaluadas</span></div>
        <div><b className="num">{pct == null ? "—" : `${String(pct).replace(".", ",")}%`}</b><span>correctas (meta 85%)</span></div>
        <div><b className="num">{respondidas.length ? `${Math.round((trazables / respondidas.length) * 100)}%` : "—"}</b><span>con la fuente esperada (meta 100%)</span></div>
        <button className="btn primario chico" onClick={correrTodas} disabled={todas || corriendo != null}>
          {todas ? <Loader2 size={15} className="gira" /> : <Play size={15} />} {todas ? "Corriendo…" : "Correr pendientes"}
        </button>
        <button
          className="btn secundario chico"
          onClick={() =>
            descargarCsv("planeai-banco-preguntas.csv", [
              ["id", "categoria", "pregunta", "respuesta_esperada", "respuesta", "fuentes", "trazable", "claves_faltantes", "correcta"],
              ...filas.map((p) => [p.id, p.categoria, p.pregunta, p.respuesta_esperada, p.respuesta || "", (p.fuentes || []).map((f) => `${f.titulo}${f.detalle ? ` (${f.detalle})` : ""}`).join(" | "), p.respuesta ? (p.trazable ? "sí" : "no") : "", (p.faltan || []).join("; "), p.correcta == null ? "" : p.correcta ? "sí" : "no"]),
            ])
          }
        >
          <Download size={15} /> Exportar CSV
        </button>
      </div>
      <Segmentado etiqueta="Categoría" valor={filtro} onChange={setFiltro} opciones={[{ v: "todas", t: "Todas" }, { v: "malla", t: "Malla" }, { v: "reglamento", t: "Reglamento" }]} />
      <ol className="banco-lista">
        {visibles.map((p) => (
          <li key={p.id} className={p.correcta === true ? "ok" : p.correcta === false ? "mal" : ""}>
            <div className="bq-fila">
              <button className="bq-texto" onClick={() => setAbierta(abierta === p.id ? null : p.id)} aria-expanded={abierta === p.id}>
                <small className="num">P{p.id} · {p.categoria}</small> {p.pregunta}
              </button>
              <div className="bq-acciones">
                {p.respuesta && <span className={`etiqueta ${p.trazable ? "ok" : "aviso"}`}>{p.trazable ? "Fuente correcta" : "Sin la fuente esperada"}</span>}
                <button className="icono mini" onClick={() => { setAbierta(p.id); correr(p); }} disabled={corriendo != null || todas} aria-label="Preguntar al asistente">
                  {corriendo === p.id ? <Loader2 size={15} className="gira" /> : <Play size={15} />}
                </button>
                <button className={`icono mini ${p.correcta === true ? "activo-ok" : ""}`} disabled={!p.respuesta} onClick={() => marcar(p.id, true)} aria-label="Marcar correcta"><CheckCircle2 size={16} /></button>
                <button className={`icono mini ${p.correcta === false ? "activo-mal" : ""}`} disabled={!p.respuesta} onClick={() => marcar(p.id, false)} aria-label="Marcar incorrecta"><XCircle size={16} /></button>
              </div>
            </div>
            <AnimatePresence initial={false}>
              {abierta === p.id && (
                <motion.div className="bq-respuesta" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
                  <p className="ayuda"><b>Respuesta esperada:</b> {p.respuesta_esperada} <i>(fuente: {p.fuente_esperada.tipo}{p.fuente_esperada.detalle ? `, ${p.fuente_esperada.detalle}` : ""})</i></p>
                  {p.respuesta ? (
                    <>
                      {p.faltan?.length > 0 && <p className="etiqueta aviso">Revisar: no menciona {p.faltan.join(", ")}</p>}
                      <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{p.respuesta}</ReactMarkdown></div>
                      {p.fuentes?.length > 0 && <p className="ayuda">Fuentes consultadas: {p.fuentes.map((f) => `${f.titulo}${f.detalle ? ` (${f.detalle})` : ""}`).join(" · ")}</p>}
                    </>
                  ) : (
                    <p className="ayuda">Aún no se ha lanzado al asistente.</p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function Evaluacion() {
  const [tab, setTab] = useState("sus");
  const [lista, setListaState] = useState(() => leer("sus", []));
  const setLista = (fn) => setListaState((p) => { const n = fn(p); escribir("sus", n); return n; });

  return (
    <div className="vista vista-eval">
      <div className="vista-cab">
        <div>
          <h1 className="titulo-vista">Evaluación</h1>
          <p className="bajada">Cuestionario de usabilidad SUS para las sesiones de prueba con estudiantes, y el banco de preguntas para medir la exactitud del asistente.</p>
        </div>
        <Segmentado
          etiqueta="Sección"
          valor={tab}
          onChange={setTab}
          opciones={[
            { v: "sus", t: "Cuestionario", Icon: ClipboardList },
            { v: "resultados", t: `Resultados${lista.length ? ` (${lista.length})` : ""}`, Icon: BarChart3 },
            { v: "banco", t: "Banco de preguntas", Icon: MessagesSquare },
          ]}
        />
      </div>
      {tab === "sus" && <Cuestionario onGuardar={(r) => setLista((l) => [r, ...l])} />}
      {tab === "resultados" && (
        <Resultados
          lista={lista}
          onBorrar={(id) => setLista((l) => l.filter((x) => x.id !== id))}
          onImportar={(nuevas) => {
            const clave = (x) => `${x.participante}|${x.fecha}|${x.respuestas.join("")}`;
            const existentes = new Set(lista.map(clave));
            const agregar = nuevas.filter((x) => !existentes.has(clave(x)));
            setLista((l) => [...agregar, ...l]);
            return agregar.length;
          }}
        />
      )}
      {tab === "banco" && <Banco />}
    </div>
  );
}
