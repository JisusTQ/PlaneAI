import { Mail, ArrowUpRight } from "lucide-react";

import { useApp } from "../lib/AppContext.jsx";

const OBJETIVOS = [
  {
    id: "OE1",
    t: "Construir un modelo computable del plan de estudios y de la reglamentación académica aplicable.",
    i: "100 % de las materias obligatorias modeladas, grafo verificado como acíclico y coincidencia de al menos 95 % con el plan publicado.",
    v: "malla",
    donde: "Mi malla",
  },
  {
    id: "OE2",
    t: "Implementar el motor de validación y recomendación de cargas académicas factibles.",
    i: "En al menos 25 casos de prueba, 90 % o más de las propuestas cumple todas las restricciones duras.",
    v: "planificador",
    donde: "Planificador",
  },
  {
    id: "OE3",
    t: "Desarrollar la interfaz conversacional soportada en un modelo grande de lenguaje con recuperación de fuentes.",
    i: "85 % o más de respuestas correctas en un banco de 40 preguntas, con trazabilidad a la fuente en todas las respuestas.",
    v: "asistente",
    donde: "Asistente",
  },
  {
    id: "OE4",
    t: "Evaluar el prototipo con usuarios finales del programa.",
    i: "Puntaje SUS de al menos 68 con 15 estudiantes o más, y reporte de hallazgos con acciones de mejora.",
    v: "evaluacion",
    donde: "Evaluación",
  },
];

const FASES = [
  { t: "Análisis y requisitos", d: "Revisión del plan de estudios, el reglamento y la oferta; encuesta y entrevistas a estudiantes; historias de usuario priorizadas." },
  { t: "Modelado del dominio", d: "Currículo como grafo dirigido acíclico, esquemas de datos tipados y formalización de las reglas académicas." },
  { t: "Motor de validación y recomendación", d: "Validación de precedencias, cupos, horarios y créditos; generación de alternativas con poda y banco de casos de prueba." },
  { t: "Asistente conversacional e interfaz", d: "Integración del motor con el modelo de lenguaje, consulta a fuentes oficiales, interfaz web y despliegue." },
  { t: "Evaluación y cierre", d: "Sesiones guiadas con estudiantes, escala SUS, análisis de resultados e informe final." },
];

const EQUIPO = [
  { n: "Ana María Granada Rodas", c: "ana.granada1@udea.edu.co" },
  { n: "Juan Pablo Ramos Vélez", c: "juanp.ramos@udea.edu.co" },
  { n: "Jesús Estiven Torres Quintero", c: "jesus.torresq@udea.edu.co" },
];

export default function Proyecto() {
  const { ir } = useApp();
  return (
    <div className="vista proyecto">
      <header className="pr-cab">
        <h1 className="titular pr-titular">PlaneAI</h1>
        <p className="bajada">
          Asistente inteligente para la planeación de matrícula académica de los estudiantes de Ingeniería de Sistemas de la Universidad de Antioquia. Proyecto de tipo desarrollo, Proyecto Integrador I, Facultad de Ingeniería.
        </p>
      </header>

      <section className="pr-seccion">
        <h2 className="subtitulo">El problema</h2>
        <p className="pr-texto">
          En cada tanda de matrícula el estudiante tiene pocos minutos para cruzar a mano cuatro fuentes que no se comunican entre sí: su historia académica, la malla con su red de prerrequisitos y correquisitos, la oferta de grupos y cupos que cambia minuto a minuto, y los horarios. Resolver esas restricciones simultáneas contra el reloj produce matrículas incompletas o mal conformadas, cancelaciones y rezago académico.
        </p>
      </section>

      <section className="pr-seccion">
        <h2 className="subtitulo">Objetivo general</h2>
        <p className="pr-texto">
          Desarrollar un asistente inteligente, basado en modelos grandes de lenguaje y en un motor de validación de restricciones curriculares, que genere y explique propuestas de carga académica factibles para los estudiantes de Ingeniería de Sistemas de la Universidad de Antioquia.
        </p>
      </section>

      <section className="pr-seccion">
        <h2 className="subtitulo">Objetivos específicos y dónde se ven</h2>
        <div className="objetivos">
          {OBJETIVOS.map((o) => (
            <article key={o.id} className="objetivo">
              <span className="obj-id">{o.id}</span>
              <p className="obj-t">{o.t}</p>
              <p className="obj-i"><b>Indicador:</b> {o.i}</p>
              <button className="btn fantasma chico" onClick={() => ir(o.v)}>
                Ver en {o.donde} <ArrowUpRight size={15} />
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="pr-seccion">
        <h2 className="subtitulo">Metodología</h2>
        <p className="pr-texto">Enfoque incremental e iterativo inspirado en Scrum: cinco fases encadenadas, cada una cerrada con un entregable verificable.</p>
        <ol className="fases">
          {FASES.map((f, i) => (
            <li key={f.t}>
              <span className="fase-num num">F{i + 1}</span>
              <div>
                <b>{f.t}</b>
                <p>{f.d}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="pr-seccion pr-dos">
        <div>
          <h2 className="subtitulo">Equipo</h2>
          <ul className="equipo">
            {EQUIPO.map((p) => (
              <li key={p.c}>
                <b>{p.n}</b>
                <a href={`mailto:${p.c}`}><Mail size={14} /> {p.c}</a>
              </li>
            ))}
          </ul>
          <h3 className="pr-h3">Profesor asesor</h3>
          <ul className="equipo">
            <li>
              <b>Ronal Davilmar Montoya Montoya</b>
              <a href="mailto:ronal.montoya@udea.edu.co"><Mail size={14} /> ronal.montoya@udea.edu.co</a>
            </li>
          </ul>
        </div>
        <div>
          <h2 className="subtitulo">Cómo está construido</h2>
          <dl className="stack">
            <dt>Interfaz</dt><dd>React y Vite, desplegada en Vercel</dd>
            <dt>Servicio</dt><dd>Python con FastAPI, desplegado en Render</dd>
            <dt>Motor</dt><dd>Grafo dirigido acíclico, algoritmo de Kahn, búsqueda con poda priorizada por criticidad</dd>
            <dt>Asistente</dt><dd>Modelo de lenguaje con llamadas a herramientas sobre las fuentes oficiales</dd>
            <dt>Fuentes</dt><dd>Pensum oficial (Cursum) y oferta de cupos (MARES), consultados en vivo</dd>
            <dt>Privacidad</dt><dd>Tu historia académica se guarda solo en tu navegador</dd>
          </dl>
        </div>
      </section>

      <section className="pr-seccion">
        <h2 className="subtitulo">Referentes</h2>
        <ul className="refs">
          <li>Atalla, S. et al. (2023). An intelligent recommendation system for automating academic advising based on curriculum analysis and performance modeling. <i>Mathematics</i>, 11(5), 1098.</li>
          <li>Parameswaran, A., Venetis, P. y Garcia-Molina, H. (2011). Recommendation systems with complex constraints: A course recommendation perspective. <i>ACM TOIS</i>, 29(4).</li>
          <li>Lewis, P. et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. <i>NeurIPS</i>, 33.</li>
          <li>Van Deventer, H., Mills, M. y Evrard, A. E. (2024). From interests to insights: An LLM approach to course recommendations using natural language queries. arXiv:2412.19312.</li>
          <li>Brooke, J. (1996). SUS: A quick and dirty usability scale. En <i>Usability Evaluation in Industry</i>.</li>
        </ul>
      </section>
    </div>
  );
}
