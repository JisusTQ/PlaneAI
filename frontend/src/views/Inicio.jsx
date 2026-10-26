import { useEffect, useState } from "react";
import { Upload, MessageSquareText, Network, CalendarRange, ClipboardCheck, ShieldCheck, Sparkles, ArrowRight } from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";
import { obtenerResumenGrafo } from "../lib/api.js";
import MallaMini from "../components/MallaMini.jsx";

const PASOS = [
  { v: "malla", Icon: Network, t: "Marca lo que ya aprobaste", d: "Toca las materias en la malla o pega tu historia de MARES. Al instante ves qué se desbloquea." },
  { v: "planificador", Icon: CalendarRange, t: "Genera o arma tu carga", d: "El motor propone hasta tres combinaciones sin choques, o armas la tuya grupo por grupo." },
  { v: "asistente", Icon: MessageSquareText, t: "Resuelve dudas conversando", d: "Pregunta por cupos, horarios o requisitos. Cada respuesta muestra la fuente que consultó." },
  { v: "evaluacion", Icon: ClipboardCheck, t: "Cuéntanos cómo te fue", d: "Diez afirmaciones rápidas para medir la usabilidad de la herramienta." },
];

export default function Inicio() {
  const { ir, malla, aprobadas, habilitadas, servidor } = useApp();
  const [resumen, setResumen] = useState(null);

  useEffect(() => {
    if (servidor === "ok") obtenerResumenGrafo().then(setResumen).catch(() => {});
  }, [servidor]);

  const tieneHistoria = aprobadas.size > 0;

  return (
    <div className="vista inicio">
      <section className="hero">
        <h1 className="titular hero-titular">Arma tu matrícula sobre la malla real.</h1>
        <div className="hero-texto">
          <p className="hero-bajada">
            PlaneAI cruza tu historia académica con los prerrequisitos del pensum y los cupos del semestre, y te propone cargas que ya pasaron por un motor de validación. Para estudiantes de Ingeniería de Sistemas de la UdeA.
          </p>
          <div className="hero-cta">
            {tieneHistoria ? (
              <button className="btn primario" onClick={() => ir("planificador")}><Sparkles size={17} /> Generar mi carga</button>
            ) : (
              <button className="btn primario" onClick={() => ir("malla")}><Upload size={17} /> Marcar mis materias aprobadas</button>
            )}
            <button className="btn secundario" onClick={() => ir("asistente")}><MessageSquareText size={17} /> Preguntarle al asistente</button>
          </div>
          {tieneHistoria && malla.estado === "ok" && (
            <p className="hero-estado">
              Tienes <b className="num">{aprobadas.size}</b> materias aprobadas y <b className="num">{habilitadas.length}</b> disponibles para matricular.
            </p>
          )}
        </div>
        <button className="hero-malla" onClick={() => ir("malla")} aria-label="Abrir la malla interactiva">
          <MallaMini />
          <span className="hero-malla-pie">
            <span><i className="ley aprobada" /> Aprobada</span>
            <span><i className="ley habilitada" /> Disponible</span>
            <span><i className="ley bloqueada" /> Bloqueada</span>
            <span className="hero-abrir">Abrir malla <ArrowRight size={14} /></span>
          </span>
        </button>
      </section>

      <section className="verificacion" aria-label="Modelo del plan de estudios">
        <ShieldCheck size={22} />
        {resumen ? (
          <p>
            Pensum vigente{resumen.version_pensum ? ` (versión ${resumen.version_pensum})` : ""}:{" "}
            <b>{resumen.materias_obligatorias} materias obligatorias</b>, <b>{resumen.creditos_obligatorios} créditos</b> en <b>{resumen.niveles} semestres</b>, unidas por{" "}
            <b>{resumen.aristas_prerrequisito} prerrequisitos</b> y {resumen.correquisitos} correquisitos.{" "}
            {resumen.es_aciclico ? "El grafo se verificó sin ciclos: toda materia tiene un orden válido para cursarse." : "Atención: el grafo presenta ciclos."}
          </p>
        ) : (
          <p className="ayuda">{servidor === "caido" ? "Sin conexión con el servidor." : "Verificando el modelo del plan de estudios…"}</p>
        )}
      </section>

      <section className="pasos">
        <h2 className="subtitulo">Cómo se usa</h2>
        <ol>
          {PASOS.map(({ v, Icon, t, d }, i) => (
            <li key={v}>
              <button onClick={() => ir(v)}>
                <span className="paso-num num">{i + 1}</span>
                <Icon size={20} className="paso-icono" />
                <b>{t}</b>
                <span>{d}</span>
              </button>
            </li>
          ))}
        </ol>
      </section>

      <section className="dos-capas">
        <div>
          <h2 className="subtitulo">El motor decide. El asistente explica.</h2>
          <p className="bajada">
            Que una carga sea válida no depende de la IA. Un motor determinista revisa prerrequisitos, correquisitos, cupos, cruces de horario y el tope de créditos; el asistente conversacional solo traduce ese resultado a lenguaje natural y cita de dónde sacó cada dato.
          </p>
        </div>
        <div className="capas" aria-hidden>
          <div className="capa">
            <b>Asistente conversacional</b>
            <span>Modelo de lenguaje con consulta a fuentes</span>
          </div>
          <div className="capa-flecha" />
          <div className="capa fuerte">
            <b>Motor de validación</b>
            <span>Grafo de prerrequisitos y búsqueda con poda</span>
          </div>
          <div className="capa-flecha" />
          <div className="capa base">
            <b>Fuentes oficiales UdeA</b>
            <span>Pensum (Cursum) y oferta de cupos (MARES)</span>
          </div>
        </div>
      </section>

      {resumen?.materias_mas_criticas?.length > 0 && (
        <section className="criticas">
          <h2 className="subtitulo">Las materias que más camino abren</h2>
          <p className="bajada">Si pierdes una de estas, se retrasa la mayor cantidad de materias del plan.</p>
          <ul>
            {resumen.materias_mas_criticas.map((m) => (
              <li key={m.codigo}>
                <span>{m.nombre}</span>
                <span className="crit-barra"><i style={{ width: `${(m.dependientes / resumen.materias_mas_criticas[0].dependientes) * 100}%` }} /></span>
                <b className="num">{m.dependientes}</b>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="pie-inicio">
        <span>PlaneAI, Proyecto Integrador I, Departamento de Ingeniería de Sistemas, Universidad de Antioquia.</span>
        <button className="btn fantasma chico" onClick={() => ir("proyecto")}>Sobre el proyecto</button>
      </footer>
    </div>
  );
}
