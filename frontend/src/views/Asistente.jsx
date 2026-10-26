import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUp, Plus, History, Trash2, Copy, Check, BookMarked, Ticket, ShieldCheck, RotateCcw, X, GraduationCap,
} from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { enviarMensaje, obtenerSugerencias } from "../lib/api.js";
import { leer, escribir } from "../lib/storage.js";
import { LogoMarca } from "../components/Logo.jsx";

const INICIALES = [
  { t: "Voy para tercer semestre, recomiéndame una carga sin choques.", g: "Planear" },
  { t: "¿Qué grupos de Cálculo Integral tienen cupo?", g: "Cupos" },
  { t: "¿Qué materias me desbloquea Matemáticas Discretas?", g: "Malla" },
  { t: "Solo puedo estudiar en la mañana, ¿qué me sirve?", g: "Planear" },
];

// Trazabilidad (OE3): cada herramienta que usa el agente se muestra como la fuente que consultó.
const FUENTES = {
  consultar_pensum: { t: "Pensum oficial (Cursum, Facultad de Ingeniería)", Icon: BookMarked },
  consultar_horarios_udea: { t: "Oferta de cupos y horarios (portal MARES)", Icon: Ticket },
  proponer_cargas: { t: "Motor determinista: generó cargas", Icon: ShieldCheck },
  validar_carga: { t: "Motor determinista: validó la carga", Icon: ShieldCheck },
};

function fuentesDe(pasos = []) {
  const vistos = new Map();
  for (const p of pasos) {
    const f = FUENTES[p.herramienta] || { t: p.herramienta, Icon: BookMarked };
    const detalle = p.args?.nivel ? `nivel ${p.args.nivel}` : p.args?.materia ? p.args.materia : p.args?.franja || "";
    const prev = vistos.get(f.t);
    vistos.set(f.t, { ...f, detalles: [...(prev?.detalles || []), detalle].filter(Boolean) });
  }
  return [...vistos.values()];
}

function Respuesta({ m }) {
  const [copiado, setCopiado] = useState(false);
  const fuentes = fuentesDe(m.pasos);
  return (
    <div className="msg bot">
      <LogoMarca size={28} className="msg-avatar" />
      <div className="msg-cuerpo">
        <div className="md">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.texto}</ReactMarkdown>
        </div>
        {m.pasos && (
          <div className="fuentes">
            {fuentes.length ? (
              fuentes.map((f) => (
                <span key={f.t} className="fuente" title={f.detalles.join(", ")}>
                  <f.Icon size={13} /> {f.t}
                </span>
              ))
            ) : (
              <span className="fuente sin">Respuesta sin consulta a fuentes oficiales</span>
            )}
            <button
              className="icono mini"
              onClick={() => navigator.clipboard?.writeText(m.texto).then(() => { setCopiado(true); setTimeout(() => setCopiado(false), 1400); })}
              aria-label="Copiar respuesta"
            >
              {copiado ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Asistente() {
  const { aprobadas, preguntaPendiente, setPreguntaPendiente, malla } = useApp();
  const [mensajes, setMensajes] = useState(() => leer("chat-actual", []));
  const [historial, setHistorial] = useState(() => leer("chat-historial", []));
  const [verHistorial, setVerHistorial] = useState(false);
  const [entrada, setEntrada] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [sugerencias, setSugerencias] = useState([]);
  const [usarHistoria, setUsarHistoria] = useState(() => leer("chat-usar-historia", true));
  const finRef = useRef(null);
  const areaRef = useRef(null);

  useEffect(() => { escribir("chat-actual", mensajes); }, [mensajes]);
  useEffect(() => { escribir("chat-usar-historia", usarHistoria); }, [usarHistoria]);
  useEffect(() => {
    if (mensajes.length || cargando) finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes, cargando]);

  // Pregunta dejada por otra vista (malla, planificador)
  useEffect(() => {
    if (preguntaPendiente && !cargando) {
      enviar(preguntaPendiente);
      setPreguntaPendiente(null);
    }
  }, [preguntaPendiente]); // eslint-disable-line react-hooks/exhaustive-deps

  const contexto = () =>
    usarHistoria && aprobadas.size
      ? `[Contexto del estudiante, enviado por la app: materias aprobadas (códigos): ${[...aprobadas].join(", ")}]\n\n`
      : "";

  async function pedir(conversacion) {
    setCargando(true);
    setError(null);
    setSugerencias([]);
    const previos = conversacion.slice(0, -1);
    const ultimo = conversacion[conversacion.length - 1];
    try {
      const d = await enviarMensaje(ultimo.envio || ultimo.texto, previos);
      const nueva = [...conversacion, { rol: "bot", texto: d.respuesta, pasos: d.pasos || [] }];
      setMensajes(nueva);
      obtenerSugerencias(nueva).then((s) => s.sugerencias?.length && setSugerencias(s.sugerencias)).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  function enviar(texto) {
    const t = (texto ?? entrada).trim();
    if (!t || cargando) return;
    setEntrada("");
    if (areaRef.current) areaRef.current.style.height = "auto";
    const conv = [...mensajes, { rol: "user", texto: t, envio: contexto() + t }];
    setMensajes(conv);
    pedir(conv);
  }

  function archivar() {
    const primera = mensajes.find((m) => m.rol === "user");
    if (!primera) return historial;
    const lista = [{ id: Date.now(), titulo: primera.texto.slice(0, 70), fecha: Date.now(), mensajes }, ...historial].slice(0, 25);
    setHistorial(lista);
    escribir("chat-historial", lista);
    return lista;
  }

  function nueva() {
    if (cargando) return;
    archivar();
    setMensajes([]);
    setError(null);
    setSugerencias([]);
  }

  function abrir(c) {
    const lista = archivar().filter((x) => x.id !== c.id);
    setHistorial(lista);
    escribir("chat-historial", lista);
    setMensajes(c.mensajes);
    setVerHistorial(false);
  }

  function borrar(id) {
    const lista = historial.filter((x) => x.id !== id);
    setHistorial(lista);
    escribir("chat-historial", lista);
  }

  const vacio = mensajes.length === 0;

  return (
    <div className="vista vista-chat">
      <div className="chat-barra">
        <h1 className="titulo-vista">Asistente</h1>
        <div className="chat-acciones">
          <button className="btn fantasma chico" onClick={() => setVerHistorial(true)}>
            <History size={16} /> Historial{historial.length ? ` (${historial.length})` : ""}
          </button>
          {!vacio && <button className="btn secundario chico" onClick={nueva} disabled={cargando}><Plus size={16} /> Nueva conversación</button>}
        </div>
      </div>

      <div className="chat-hilo">
        {vacio && (
          <motion.div className="chat-vacio" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <LogoMarca size={52} />
            <h2 className="titular chat-titular">¿Qué quieres matricular este semestre?</h2>
            <p className="bajada">
              Pregunta en tus palabras. El asistente consulta el pensum y los cupos en vivo, usa el motor para validar cada carga y te muestra de dónde sacó cada dato.
            </p>
            <div className="chat-iniciales">
              {INICIALES.map((s) => (
                <button key={s.t} onClick={() => enviar(s.t)}>
                  <small>{s.g}</small>
                  {s.t}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {mensajes.map((m, i) =>
          m.rol === "user" ? (
            <motion.div key={i} className="msg user" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div className="msg-burbuja">{m.texto}</div>
            </motion.div>
          ) : (
            <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <Respuesta m={m} />
            </motion.div>
          )
        )}

        {cargando && (
          <div className="msg bot">
            <LogoMarca size={28} className="msg-avatar pensando" />
            <div className="msg-cuerpo">
              <div className="escribiendo"><span /><span /><span /></div>
              <p className="ayuda">Consultando fuentes oficiales…</p>
            </div>
          </div>
        )}

        {error && (
          <div className="aviso-caja error">
            <span>{error}</span>
            <button className="btn secundario chico" onClick={() => pedir(mensajes)} disabled={cargando}><RotateCcw size={14} /> Reintentar</button>
          </div>
        )}
        <div ref={finRef} />
      </div>

      <div className="compositor">
        {!cargando && sugerencias.length > 0 && (
          <div className="sugerencias">
            {sugerencias.map((s) => <button key={s} onClick={() => enviar(s)}>{s}</button>)}
          </div>
        )}
        <form className="caja-texto" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
          <textarea
            ref={areaRef}
            rows={1}
            value={entrada}
            placeholder="Escribe tu pregunta…"
            aria-label="Mensaje para el asistente"
            onChange={(e) => {
              setEntrada(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); }
            }}
          />
          <button className="enviar" type="submit" disabled={cargando || !entrada.trim()} aria-label="Enviar">
            <ArrowUp size={19} strokeWidth={2.5} />
          </button>
        </form>
        <label className="interruptor contexto">
          <input type="checkbox" checked={usarHistoria} onChange={(e) => setUsarHistoria(e.target.checked)} />
          <GraduationCap size={15} />
          {aprobadas.size
            ? `Compartir mis ${aprobadas.size} materias aprobadas con el asistente`
            : malla.estado === "ok"
              ? "Marca tus materias en la malla para que el asistente las tenga en cuenta"
              : "Compartir mi historia académica con el asistente"}
        </label>
      </div>

      <AnimatePresence>
        {verHistorial && (
          <>
            <motion.div className="velo" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setVerHistorial(false)} />
            <motion.aside
              className="cajon"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 420, damping: 40 }}
              aria-label="Historial de conversaciones"
            >
              <div className="hoja-cab">
                <b>Conversaciones guardadas</b>
                <button className="icono" onClick={() => setVerHistorial(false)} aria-label="Cerrar"><X size={20} /></button>
              </div>
              {historial.length === 0 && <p className="ayuda">Cuando empieces una conversación nueva, la anterior queda guardada aquí.</p>}
              {historial.map((c) => (
                <div key={c.id} className="hist-item">
                  <button onClick={() => abrir(c)}>
                    <b>{c.titulo}</b>
                    <small>{new Date(c.fecha).toLocaleString("es-CO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</small>
                  </button>
                  <button className="icono" onClick={() => borrar(c.id)} aria-label="Borrar conversación"><Trash2 size={15} /></button>
                </div>
              ))}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
