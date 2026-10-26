import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Sparkles, Hand, ShieldCheck, Wand2, MessageSquareText, PencilLine, Trash2, ChevronDown, Search,
  CheckCircle2, XCircle, AlertTriangle, Network, Loader2, User, MapPin,
} from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { proponerCargas, validarCarga } from "../lib/api.js";
import { codigosEnChoque, colorDe, textoSesion } from "../lib/horario.js";
import { etiquetaNivel } from "../lib/malla.js";
import Horario from "../components/Horario.jsx";
import Segmentado from "../components/Segmentado.jsx";
import { ListaGrupos } from "../components/Grupos.jsx";
import { itemDeGrupo } from "../components/PanelMateria.jsx";

const VERIFICACIONES = ["Prerrequisitos", "Correquisitos", "Oferta y cupos", "Sin choques de horario", "Tope de créditos"];

function PuntoDePartida() {
  const { aprobadas, habilitadas, creditosAprobados, ir } = useApp();
  return (
    <div className="partida">
      <div>
        <b className="num">{aprobadas.size}</b>
        <span>materias aprobadas</span>
      </div>
      <div>
        <b className="num">{habilitadas.length}</b>
        <span>disponibles para ti</span>
      </div>
      <div>
        <b className="num">{creditosAprobados}</b>
        <span>créditos aprobados</span>
      </div>
      <button className="btn fantasma chico" onClick={() => ir("malla")}>
        <Network size={15} /> Editar en la malla
      </button>
    </div>
  );
}

function ListaCarga({ items, choques, onQuitar }) {
  return (
    <ul className="carga-lista">
      <AnimatePresence initial={false}>
        {items.map((it, i) => (
          <motion.li
            key={it.codigo}
            layout
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            className={choques?.has(it.codigo) ? "choque" : ""}
            style={{ "--c": colorDe(i) }}
          >
            <i className="carga-color" />
            <div className="carga-info">
              <b>{it.nombre}</b>
              <span className="ayuda">
                Grupo {it.grupo} · {it.horario?.map(textoSesion).join(", ") || "sin horario"}
              </span>
              {(it.profesor || it.aula) && (
                <span className="carga-extra">
                  {it.profesor && <><User size={12} /> {it.profesor}</>}
                  {it.aula && <><MapPin size={12} /> {it.aula}</>}
                </span>
              )}
            </div>
            <span className="num carga-cr">{it.creditos} cr</span>
            {onQuitar && (
              <button className="icono" onClick={() => onQuitar(it.codigo)} aria-label={`Quitar ${it.nombre}`}><Trash2 size={16} /></button>
            )}
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  );
}

function ModoMotor({ onEditar }) {
  const { aprobadas, preguntarAlAsistente } = useApp();
  const [creditos, setCreditos] = useState(20);
  const [franja, setFranja] = useState("");
  const [electivas, setElectivas] = useState(false);
  const [estado, setEstado] = useState({ cargando: false, cargas: null, error: null });
  const [idx, setIdx] = useState(0);

  async function generar() {
    setEstado({ cargando: true, cargas: estado.cargas, error: null });
    try {
      const cargas = await proponerCargas({ aprobadas: [...aprobadas], creditosMax: creditos, franja, incluirElectivas: electivas });
      setEstado({ cargando: false, cargas, error: null });
      setIdx(0);
    } catch (e) {
      setEstado({ cargando: false, cargas: null, error: e.message });
    }
  }

  const actual = estado.cargas?.[idx];
  const items = actual?.materias.map((m, i) => ({ ...m, color: colorDe(i) })) ?? [];

  const explicar = () =>
    preguntarAlAsistente(
      `El motor me propuso esta carga de ${actual.creditos} créditos: ` +
        actual.materias.map((m) => `${m.nombre} (código ${m.codigo}) grupo ${m.grupo}`).join("; ") +
        ". Explícame por qué estas materias y en qué orden me conviene priorizarlas."
    );

  return (
    <div className="plan-grid">
      <section className="plan-controles">
        <h2 className="subtitulo">Condiciones</h2>
        <div className="control">
          <div className="control-cab">
            <label htmlFor="creditos">Tope de créditos</label>
            <b className="num">{creditos}</b>
          </div>
          <input id="creditos" type="range" min={8} max={24} value={creditos} onChange={(e) => setCreditos(Number(e.target.value))} />
        </div>
        <div className="control">
          <span className="control-cab"><label>Franja horaria</label></span>
          <Segmentado
            etiqueta="Franja horaria"
            valor={franja}
            onChange={setFranja}
            opciones={[
              { v: "", t: "Cualquiera" },
              { v: "manana", t: "Mañana" },
              { v: "tarde", t: "Tarde" },
              { v: "noche", t: "Noche" },
            ]}
          />
        </div>
        <label className="interruptor">
          <input type="checkbox" checked={electivas} onChange={(e) => setElectivas(e.target.checked)} />
          Incluir electivas
        </label>
        <button className="btn primario generar" onClick={generar} disabled={estado.cargando}>
          {estado.cargando ? <Loader2 size={17} className="gira" /> : <Wand2 size={17} />}
          {estado.cargando ? "Buscando combinaciones…" : estado.cargas ? "Generar de nuevo" : "Generar cargas"}
        </button>
        <p className="ayuda">
          El motor recorre las combinaciones posibles, descarta las que rompen alguna regla y prioriza las materias que desbloquean más camino.
        </p>
      </section>

      <section className="plan-resultado">
        {estado.error && <div className="aviso-caja error"><XCircle size={18} /> {estado.error}</div>}
        {!estado.cargas && !estado.error && (
          <div className="vacio">
            <Sparkles size={26} />
            <p className="subtitulo">Hasta tres cargas distintas, listas para matricular</p>
            <p>Ajusta las condiciones y pulsa «Generar cargas». Cada alternativa pasa por las cinco verificaciones del motor antes de mostrarse.</p>
          </div>
        )}
        {estado.cargas?.length === 0 && (
          <div className="vacio">
            <AlertTriangle size={24} />
            <p className="subtitulo">No hay cargas que cumplan esas condiciones</p>
            <p>Prueba con otra franja, sube el tope de créditos o revisa tu historia en la malla.</p>
          </div>
        )}
        {actual && (
          <motion.div key={idx} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="alternativa">
            <div className="alt-cab">
              <div className="alt-tabs" role="tablist">
                {estado.cargas.map((c, i) => (
                  <button key={i} role="tab" aria-selected={i === idx} className={i === idx ? "on" : ""} onClick={() => setIdx(i)}>
                    Alternativa {i + 1}
                    <small className="num">{c.creditos} cr · {c.materias.length} materias</small>
                  </button>
                ))}
              </div>
            </div>
            <div className="verificado">
              <ShieldCheck size={18} />
              <span>Verificada por el motor:</span>
              {VERIFICACIONES.map((v) => (
                <span key={v} className="etiqueta ok"><CheckCircle2 size={12} /> {v}</span>
              ))}
            </div>
            {actual.advertencias?.map((a, i) => (
              <div key={i} className="aviso-caja aviso"><AlertTriangle size={16} /> {a.mensaje}</div>
            ))}
            <Horario items={items} />
            <ListaCarga items={items} />
            <div className="alt-acciones">
              <button className="btn secundario" onClick={() => onEditar(items)}><PencilLine size={16} /> Ajustar a mano</button>
              <button className="btn fantasma" onClick={explicar}><MessageSquareText size={16} /> Pedir explicación al asistente</button>
            </div>
          </motion.div>
        )}
      </section>
    </div>
  );
}

function ModoManual() {
  const { aprobadas, habilitadas, carga, setCarga, preguntarAlAsistente } = useApp();
  const [abierta, setAbierta] = useState(null);
  const [fantasma, setFantasma] = useState(null);
  const [q, setQ] = useState("");
  const [validacion, setValidacion] = useState({ cargando: false, r: null, error: null, firma: "" });

  const firma = carga.map((c) => `${c.codigo}:${c.grupo}`).join(";");
  const choques = useMemo(() => codigosEnChoque(carga), [carga]);
  const creditos = carga.reduce((a, c) => a + c.creditos, 0);
  const items = carga.map((c, i) => ({ ...c, color: colorDe(i), choque: choques.has(c.codigo) }));
  const conFantasma = fantasma ? [...items.filter((x) => x.codigo !== fantasma.codigo), { ...fantasma, color: "var(--tinta-3)", fantasma: true }] : items;

  const lista = habilitadas
    .filter((m) => !q.trim() || m.nombre.toLowerCase().includes(q.trim().toLowerCase()))
    .sort((a, b) => (b.dependientes || 0) - (a.dependientes || 0) || a.nivel - b.nivel);

  async function validar() {
    setValidacion({ cargando: true, r: null, error: null, firma });
    try {
      const r = await validarCarga({ aprobadas: [...aprobadas], propuesta: carga.map((c) => ({ codigo: c.codigo, grupo: c.grupo })) });
      setValidacion({ cargando: false, r, error: null, firma });
    } catch (e) {
      setValidacion({ cargando: false, r: null, error: e.message, firma });
    }
  }
  const vigente = validacion.firma === firma;

  return (
    <div className="plan-grid manual">
      <section className="plan-catalogo">
        <h2 className="subtitulo">Materias que puedes ver</h2>
        <label className="campo">
          <Search size={16} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filtrar" aria-label="Filtrar materias" />
        </label>
        {lista.length === 0 && <p className="ayuda">No hay materias disponibles con tu historia actual. Revisa la malla.</p>}
        <div className="catalogo-lista">
          {lista.map((m) => {
            const enCarga = carga.find((x) => x.codigo === m.codigo);
            const open = abierta === m.codigo;
            return (
              <div key={m.codigo} className={`cat-item ${open ? "abierta" : ""} ${enCarga ? "en-carga" : ""}`}>
                <button className="cat-cab" onClick={() => setAbierta(open ? null : m.codigo)} aria-expanded={open}>
                  <span>
                    <b>{m.nombre}</b>
                    <small>
                      {etiquetaNivel(m.nivel)}, {m.creditos} cr{m.dependientes ? `, desbloquea ${m.dependientes}` : ""}
                    </small>
                  </span>
                  {enCarga && <span className="etiqueta oro">Gr {enCarga.grupo}</span>}
                  <ChevronDown size={17} className="cat-flecha" />
                </button>
                <AnimatePresence initial={false}>
                  {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="cat-grupos">
                      <ListaGrupos
                        codigo={m.codigo}
                        compacto
                        grupoEnCarga={enCarga?.grupo}
                        onHover={(g) => setFantasma(g ? { ...itemDeGrupo(m, g) } : null)}
                        onAgregar={(g) => {
                          setFantasma(null);
                          setCarga((prev) =>
                            enCarga?.grupo === g.numero ? prev.filter((x) => x.codigo !== m.codigo) : [...prev.filter((x) => x.codigo !== m.codigo), itemDeGrupo(m, g)]
                          );
                        }}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </section>

      <section className="plan-resultado">
        <div className="manual-cab">
          <div className="medidor">
            <span><b className="num">{creditos}</b> créditos</span>
            <span className={choques.size ? "con-choque" : ""}>
              {choques.size ? <><XCircle size={15} /> {choques.size} materias se cruzan</> : carga.length ? <><CheckCircle2 size={15} /> Sin cruces</> : "Tu carga está vacía"}
            </span>
          </div>
          <div className="manual-acciones">
            {carga.length > 0 && <button className="btn fantasma chico" onClick={() => setCarga([])}><Trash2 size={15} /> Vaciar</button>}
            <button className="btn primario" onClick={validar} disabled={!carga.length || validacion.cargando}>
              {validacion.cargando ? <Loader2 size={16} className="gira" /> : <ShieldCheck size={16} />} Validar con el motor
            </button>
          </div>
        </div>

        <AnimatePresence>
          {vigente && validacion.error && <div className="aviso-caja error"><XCircle size={18} /> {validacion.error}</div>}
          {vigente && validacion.r && (
            <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} className={`veredicto ${validacion.r.valida ? "ok" : "error"}`}>
              <div className="veredicto-cab">
                {validacion.r.valida ? <CheckCircle2 size={22} /> : <XCircle size={22} />}
                <b>{validacion.r.valida ? "Carga válida: puedes matricularla así." : `La carga no es válida (${validacion.r.errores.length} ${validacion.r.errores.length === 1 ? "problema" : "problemas"}).`}</b>
              </div>
              {validacion.r.errores.map((e, i) => <p key={i}><XCircle size={14} /> {e.mensaje}</p>)}
              {validacion.r.advertencias.map((a, i) => <p key={`a${i}`} className="adv"><AlertTriangle size={14} /> {a.mensaje}</p>)}
              {!validacion.r.valida && (
                <button
                  className="btn secundario chico"
                  onClick={() => preguntarAlAsistente(`Validé mi carga y el motor encontró estos problemas: ${validacion.r.errores.map((e) => e.mensaje).join(" ")} ¿Cómo la corrijo?`)}
                >
                  <MessageSquareText size={15} /> ¿Cómo la corrijo?
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <Horario items={conFantasma} />
        {carga.length ? (
          <ListaCarga items={items} choques={choques} onQuitar={(c) => setCarga((p) => p.filter((x) => x.codigo !== c))} />
        ) : (
          <p className="ayuda">Abre una materia a la izquierda y pasa el cursor sobre sus grupos para ver cómo quedarían en tu semana.</p>
        )}
      </section>
    </div>
  );
}

export default function Planificador() {
  const { malla, setCarga } = useApp();
  const [modo, setModo] = useState("motor");

  return (
    <div className="vista">
      <div className="vista-cab">
        <div>
          <h1 className="titulo-vista">Planificador</h1>
          <p className="bajada">Deja que el motor proponga cargas sin choques, o arma la tuya grupo por grupo y valídala antes de matricular.</p>
        </div>
        <Segmentado
          etiqueta="Modo de planeación"
          valor={modo}
          onChange={setModo}
          opciones={[
            { v: "motor", t: "Que el motor proponga", Icon: Sparkles },
            { v: "manual", t: "Armar a mano", Icon: Hand },
          ]}
        />
      </div>
      {malla.estado === "ok" && <PuntoDePartida />}
      {malla.estado === "cargando" && <div className="esqueleto" style={{ height: 360 }} />}
      {malla.estado === "error" && <div className="aviso-caja error">No se pudo cargar el pensum: {malla.error}</div>}
      {malla.estado === "ok" &&
        (modo === "motor" ? (
          <ModoMotor
            onEditar={(items) => {
              setCarga(items.map(({ color, ...resto }) => resto)); // eslint-disable-line no-unused-vars
              setModo("manual");
            }}
          />
        ) : (
          <ModoManual />
        ))}
    </div>
  );
}
