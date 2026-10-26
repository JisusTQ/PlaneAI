import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { obtenerMalla, salud } from "./api.js";
import { estadoMateria, indices, NIVEL_ELECTIVAS } from "./malla.js";
import { escribir, leer } from "./storage.js";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

export const VISTAS = ["inicio", "malla", "planificador", "asistente", "oferta", "evaluacion", "proyecto"];

function vistaDelHash() {
  const v = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return VISTAS.includes(v) ? v : "inicio";
}

export function AppProvider({ children }) {
  // --- Navegación por hash (enlaces compartibles, botón atrás del navegador) ---
  const [vista, setVista] = useState(vistaDelHash);
  useEffect(() => {
    const alCambiar = () => setVista(vistaDelHash());
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  const ir = useCallback((v) => {
    if (window.location.hash !== `#/${v}`) window.location.hash = `/${v}`;
    setVista(v);
    document.getElementById("contenido")?.scrollTo?.({ top: 0 });
  }, []);

  // --- Tema ---
  const [tema, setTemaState] = useState(() => leer("tema", "sistema"));
  const setTema = (t) => {
    setTemaState(t);
    escribir("tema", t);
    if (t === "sistema") delete document.documentElement.dataset.tema;
    else document.documentElement.dataset.tema = t;
  };

  // --- Estado del servidor (Render puede tardar ~1 min en despertar) ---
  const [servidor, setServidor] = useState("verificando");
  useEffect(() => {
    let vivo = true;
    let intentos = 0;
    const lento = setTimeout(() => vivo && setServidor((s) => (s === "verificando" ? "despertando" : s)), 3500);
    const probar = async () => {
      try {
        await salud();
        if (vivo) setServidor("ok");
      } catch {
        intentos += 1;
        if (!vivo) return;
        if (intentos < 12) {
          setServidor("despertando");
          setTimeout(probar, 5000);
        } else setServidor("caido");
      }
    };
    probar();
    return () => {
      vivo = false;
      clearTimeout(lento);
    };
  }, []);

  // --- Malla (modelo del plan de estudios) ---
  const [malla, setMalla] = useState({ estado: "cargando", materias: [], version: null, error: null });
  const cargarMalla = useCallback(async () => {
    setMalla((m) => ({ ...m, estado: "cargando", error: null }));
    try {
      const d = await obtenerMalla();
      setMalla({ estado: "ok", materias: d.materias, version: d.version_pensum, error: null });
    } catch (e) {
      setMalla({ estado: "error", materias: [], version: null, error: e.message });
    }
  }, []);
  const yaPidio = useRef(false);
  useEffect(() => {
    if (!yaPidio.current && servidor === "ok") {
      yaPidio.current = true;
      cargarMalla();
    }
    if (servidor === "caido" && malla.estado === "cargando")
      setMalla({ estado: "error", materias: [], version: null, error: "No hay conexión con el servidor de PlaneAI." });
  }, [servidor, cargarMalla, malla.estado]);

  // --- Historia académica del estudiante (se guarda solo en este navegador) ---
  const [aprobadasArr, setAprobadasArr] = useState(() => leer("aprobadas", []));
  const aprobadas = useMemo(() => new Set(aprobadasArr), [aprobadasArr]);
  const guardarAprobadas = (set) => {
    const arr = [...set].sort((a, b) => a - b);
    setAprobadasArr(arr);
    escribir("aprobadas", arr);
  };
  const alternarAprobada = (codigo) => {
    const s = new Set(aprobadas);
    s.has(codigo) ? s.delete(codigo) : s.add(codigo);
    guardarAprobadas(s);
  };
  const marcarHastaNivel = (nivel) => {
    guardarAprobadas(new Set(malla.materias.filter((m) => m.nivel !== NIVEL_ELECTIVAS && m.nivel < nivel).map((m) => m.codigo)));
  };

  const derivados = useMemo(() => {
    const { porCodigo, sucesores } = indices(malla.materias);
    const estados = new Map(malla.materias.map((m) => [m.codigo, estadoMateria(m, aprobadas)]));
    const obligatorias = malla.materias.filter((m) => m.nivel !== NIVEL_ELECTIVAS);
    const creditosTotales = obligatorias.reduce((a, m) => a + m.creditos, 0);
    const creditosAprobados = obligatorias.filter((m) => aprobadas.has(m.codigo)).reduce((a, m) => a + m.creditos, 0);
    const habilitadas = malla.materias.filter((m) => estados.get(m.codigo) === "habilitada");
    return { porCodigo, sucesores, estados, obligatorias, creditosTotales, creditosAprobados, habilitadas };
  }, [malla.materias, aprobadas]);

  // --- Carga armada a mano en el planificador (persistida) ---
  const [carga, setCargaState] = useState(() => leer("carga", []));
  const setCarga = (fn) =>
    setCargaState((prev) => {
      const nueva = typeof fn === "function" ? fn(prev) : fn;
      escribir("carga", nueva);
      return nueva;
    });

  // --- Puente hacia el asistente: otras vistas pueden dejarle una pregunta lista ---
  const [preguntaPendiente, setPreguntaPendiente] = useState(null);
  const preguntarAlAsistente = (texto) => {
    setPreguntaPendiente(texto);
    ir("asistente");
  };

  const valor = {
    vista, ir, tema, setTema, servidor,
    malla, cargarMalla, aprobadas, alternarAprobada, guardarAprobadas, marcarHastaNivel,
    ...derivados,
    carga, setCarga,
    preguntaPendiente, setPreguntaPendiente, preguntarAlAsistente,
  };
  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}
