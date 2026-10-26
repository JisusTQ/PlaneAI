import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Home, Network, CalendarRange, MessageSquareText, Ticket, ClipboardCheck, BookOpen,
  MoreHorizontal, Sun, Moon, Monitor, X,
} from "lucide-react";

import { useApp } from "./lib/AppContext.jsx";
import { Logo, LogoMarca } from "./components/Logo.jsx";
import EstadoServidor from "./components/EstadoServidor.jsx";
import Inicio from "./views/Inicio.jsx";
import Malla from "./views/Malla.jsx";
import Planificador from "./views/Planificador.jsx";
import Asistente from "./views/Asistente.jsx";
import Oferta from "./views/Oferta.jsx";
import Evaluacion from "./views/Evaluacion.jsx";
import Proyecto from "./views/Proyecto.jsx";

const NAV = [
  { id: "inicio", label: "Inicio", corto: "Inicio", Icon: Home },
  { id: "malla", label: "Mi malla", corto: "Malla", Icon: Network },
  { id: "planificador", label: "Planificador", corto: "Planear", Icon: CalendarRange },
  { id: "asistente", label: "Asistente", corto: "Asistente", Icon: MessageSquareText },
  { id: "oferta", label: "Oferta y cupos", Icon: Ticket },
  { id: "evaluacion", label: "Evaluación", Icon: ClipboardCheck },
];
const NAV_MOVIL = ["inicio", "malla", "planificador", "asistente"];

const VISTAS = { inicio: Inicio, malla: Malla, planificador: Planificador, asistente: Asistente, oferta: Oferta, evaluacion: Evaluacion, proyecto: Proyecto };

function SelectorTema() {
  const { tema, setTema } = useApp();
  const opciones = [
    { v: "claro", Icon: Sun, t: "Claro" },
    { v: "sistema", Icon: Monitor, t: "Sistema" },
    { v: "oscuro", Icon: Moon, t: "Oscuro" },
  ];
  return (
    <div className="tema" role="radiogroup" aria-label="Tema">
      {opciones.map(({ v, Icon, t }) => (
        <button key={v} role="radio" aria-checked={tema === v} className={tema === v ? "on" : ""} onClick={() => setTema(v)} title={t}>
          <Icon size={15} />
        </button>
      ))}
    </div>
  );
}

function Avance() {
  const { creditosAprobados, creditosTotales, malla, ir } = useApp();
  if (malla.estado !== "ok" || !creditosTotales) return null;
  const pct = Math.round((creditosAprobados / creditosTotales) * 100);
  const r = 17, c = 2 * Math.PI * r;
  return (
    <button className="avance" onClick={() => ir("malla")}>
      <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden>
        <circle cx="22" cy="22" r={r} className="avance-pista" />
        <circle cx="22" cy="22" r={r} className="avance-arco" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)} />
      </svg>
      <span>
        <b>{creditosAprobados} de {creditosTotales} créditos</b>
        <small>{pct}% del plan aprobado</small>
      </span>
    </button>
  );
}

export default function App() {
  const { vista, ir } = useApp();
  const [mas, setMas] = useState(false);
  const Vista = VISTAS[vista];

  return (
    <div className="shell">
      <a href="#contenido" className="saltar">Saltar al contenido</a>

      <aside className="rail">
        <button className="rail-logo" onClick={() => ir("inicio")} aria-label="Ir al inicio">
          <Logo />
        </button>
        <nav className="rail-nav" aria-label="Principal">
          {NAV.map(({ id, label, Icon }) => (
            <button key={id} className={`rail-item ${vista === id ? "on" : ""}`} aria-current={vista === id ? "page" : undefined} onClick={() => ir(id)}>
              {vista === id && <motion.span layoutId="rail-marca" className="rail-marca" transition={{ type: "spring", stiffness: 500, damping: 40 }} />}
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="rail-pie">
          <Avance />
          <button className={`rail-item sutil ${vista === "proyecto" ? "on" : ""}`} onClick={() => ir("proyecto")}>
            <BookOpen size={18} />
            <span>Sobre el proyecto</span>
          </button>
          <div className="rail-fila">
            <EstadoServidor />
            <SelectorTema />
          </div>
        </div>
      </aside>

      <header className="barra-movil">
        <button onClick={() => ir("inicio")} aria-label="Ir al inicio" className="barra-logo">
          <LogoMarca size={30} />
          <b>PlaneAI</b>
        </button>
        <EstadoServidor compacto />
      </header>

      <main id="contenido" className="contenido" tabIndex={-1}>
        {/* Transición solo de entrada: el cambio de vista nunca espera a que termine una animación de salida. */}
        <motion.div
          key={vista}
          className="vista-wrap"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Vista />
        </motion.div>
      </main>

      <nav className="tabbar" aria-label="Principal">
        {NAV.filter((n) => NAV_MOVIL.includes(n.id)).map(({ id, corto, Icon }) => (
          <button key={id} className={vista === id ? "on" : ""} aria-current={vista === id ? "page" : undefined} onClick={() => ir(id)}>
            <Icon size={21} />
            <span>{corto}</span>
          </button>
        ))}
        <button className={["oferta", "evaluacion", "proyecto"].includes(vista) ? "on" : ""} onClick={() => setMas(true)}>
          <MoreHorizontal size={21} />
          <span>Más</span>
        </button>
      </nav>

      <AnimatePresence>
        {mas && (
          <>
            <motion.div className="velo" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMas(false)} />
            <motion.div
              className="hoja"
              role="dialog"
              aria-label="Más opciones"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", stiffness: 420, damping: 40 }}
            >
              <div className="hoja-cab">
                <b>Más</b>
                <button className="icono" onClick={() => setMas(false)} aria-label="Cerrar"><X size={20} /></button>
              </div>
              {[
                { id: "oferta", label: "Oferta y cupos", Icon: Ticket },
                { id: "evaluacion", label: "Evaluación de usabilidad", Icon: ClipboardCheck },
                { id: "proyecto", label: "Sobre el proyecto", Icon: BookOpen },
              ].map(({ id, label, Icon }) => (
                <button key={id} className="hoja-item" onClick={() => { setMas(false); ir(id); }}>
                  <Icon size={20} /> {label}
                </button>
              ))}
              <Avance />
              <div className="hoja-tema">
                <span>Tema</span>
                <SelectorTema />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
