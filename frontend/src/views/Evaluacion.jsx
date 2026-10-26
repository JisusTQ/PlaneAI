import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Trash2, CheckCircle2, XCircle, Play, Loader2, Plus, RotateCcw, ClipboardList, BarChart3, MessagesSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { enviarMensaje } from "../lib/api.js";
import { BANCO_INICIAL, ESCALA, ITEMS_SUS, lecturaSus, META_PARTICIPANTES, META_SUS, puntajeSus } from "../lib/evaluacion.js";
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

function Resultados({ lista, onBorrar }) {
  if (!lista.length)
    return (
      <div className="vacio">
        <BarChart3 size={24} />
        <p className="subtitulo">Aún no hay respuestas en este equipo</p>
        <p>Las sesiones guiadas de prueba se registran aquí. Al final puedes exportar todo a CSV para el informe.</p>
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
        <span className="ayuda">Las respuestas se guardan en este navegador; expórtalas al terminar las sesiones.</span>
      </div>
    </div>
  );
}

function Banco() {
  const [preguntas, setPreguntasState] = useState(() => leer("banco", BANCO_INICIAL.map((t, i) => ({ id: i + 1, texto: t, respuesta: null, pasos: null, correcta: null }))));
  const setPreguntas = (fn) => setPreguntasState((p) => { const n = fn(p); escribir("banco", n); return n; });
  const [corriendo, setCorriendo] = useState(null);
  const [abierta, setAbierta] = useState(null);
  const [nueva, setNueva] = useState("");

  async function correr(p) {
    setCorriendo(p.id);
    setAbierta(p.id);
    try {
      const d = await enviarMensaje(p.texto, []);
      setPreguntas((l) => l.map((x) => (x.id === p.id ? { ...x, respuesta: d.respuesta, pasos: d.pasos || [], correcta: null } : x)));
    } catch (e) {
      setPreguntas((l) => l.map((x) => (x.id === p.id ? { ...x, respuesta: `Error: ${e.message}`, pasos: [], correcta: null } : x)));
    } finally {
      setCorriendo(null);
    }
  }

  const evaluadas = preguntas.filter((p) => p.correcta != null);
  const correctas = evaluadas.filter((p) => p.correcta).length;
  const conFuente = preguntas.filter((p) => p.pasos?.length).length;
  const respondidas = preguntas.filter((p) => p.respuesta).length;
  const pct = evaluadas.length ? Math.round((correctas / evaluadas.length) * 100) : null;

  return (
    <div className="banco">
      <p className="bajada">
        Banco de preguntas para medir el OE3: el equipo lanza cada pregunta al asistente, revisa la respuesta contra la fuente oficial y la marca como correcta o incorrecta. La trazabilidad se registra sola según las fuentes consultadas.
      </p>
      <div className="banco-resumen">
        <div><b className="num">{evaluadas.length}/{preguntas.length}</b><span>evaluadas</span></div>
        <div><b className="num">{pct == null ? "—" : `${pct}%`}</b><span>correctas (meta 85%)</span></div>
        <div><b className="num">{respondidas ? `${Math.round((conFuente / respondidas) * 100)}%` : "—"}</b><span>con fuente citada</span></div>
        <button
          className="btn secundario chico"
          onClick={() =>
            descargarCsv("planeai-banco-preguntas.csv", [
              ["id", "pregunta", "correcta", "fuentes", "respuesta"],
              ...preguntas.map((p) => [p.id, p.texto, p.correcta == null ? "" : p.correcta ? "sí" : "no", (p.pasos || []).map((x) => x.herramienta).join(" | "), p.respuesta || ""]),
            ])
          }
        >
          <Download size={15} /> Exportar CSV
        </button>
      </div>
      <ol className="banco-lista">
        {preguntas.map((p) => (
          <li key={p.id} className={p.correcta === true ? "ok" : p.correcta === false ? "mal" : ""}>
            <div className="bq-fila">
              <button className="bq-texto" onClick={() => setAbierta(abierta === p.id ? null : p.id)} aria-expanded={abierta === p.id}>{p.texto}</button>
              <div className="bq-acciones">
                {p.pasos && <span className={`etiqueta ${p.pasos.length ? "ok" : "aviso"}`}>{p.pasos.length ? "Con fuente" : "Sin fuente"}</span>}
                <button className="icono mini" onClick={() => correr(p)} disabled={corriendo != null} aria-label="Preguntar al asistente">
                  {corriendo === p.id ? <Loader2 size={15} className="gira" /> : <Play size={15} />}
                </button>
                <button className={`icono mini ${p.correcta === true ? "activo-ok" : ""}`} disabled={!p.respuesta} onClick={() => setPreguntas((l) => l.map((x) => (x.id === p.id ? { ...x, correcta: true } : x)))} aria-label="Marcar correcta"><CheckCircle2 size={16} /></button>
                <button className={`icono mini ${p.correcta === false ? "activo-mal" : ""}`} disabled={!p.respuesta} onClick={() => setPreguntas((l) => l.map((x) => (x.id === p.id ? { ...x, correcta: false } : x)))} aria-label="Marcar incorrecta"><XCircle size={16} /></button>
                <button className="icono mini" onClick={() => setPreguntas((l) => l.filter((x) => x.id !== p.id))} aria-label="Eliminar pregunta"><Trash2 size={14} /></button>
              </div>
            </div>
            <AnimatePresence initial={false}>
              {abierta === p.id && p.respuesta && (
                <motion.div className="bq-respuesta md" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{p.respuesta}</ReactMarkdown>
                </motion.div>
              )}
            </AnimatePresence>
          </li>
        ))}
      </ol>
      <form
        className="banco-nueva"
        onSubmit={(e) => {
          e.preventDefault();
          if (!nueva.trim()) return;
          setPreguntas((l) => [...l, { id: Date.now(), texto: nueva.trim(), respuesta: null, pasos: null, correcta: null }]);
          setNueva("");
        }}
      >
        <label className="campo"><input value={nueva} onChange={(e) => setNueva(e.target.value)} placeholder="Agregar una pregunta al banco" aria-label="Nueva pregunta" /></label>
        <button className="btn secundario" type="submit" disabled={!nueva.trim()}><Plus size={16} /> Agregar</button>
      </form>
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
      {tab === "resultados" && <Resultados lista={lista} onBorrar={(id) => setLista((l) => l.filter((x) => x.id !== id))} />}
      {tab === "banco" && <Banco />}
    </div>
  );
}
