# Frontend — PlaneAI UdeA

Interfaz web de PlaneAI, construida con **React + Vite**. Responsiva (escritorio,
tableta y móvil), con modo claro/oscuro y animaciones con `framer-motion`.

No contiene lógica de negocio: la validez de una carga la decide el **motor
determinista del backend**; el frontend solo la presenta y la hace interactiva.

## Vistas y objetivos del anteproyecto

| Vista | Qué hace | Objetivo |
|---|---|---|
| **Inicio** | Malla en miniatura con el avance del estudiante, verificación del modelo del pensum y materias más críticas | — |
| **Mi malla** | Pensum como grafo dirigido acíclico: al pasar el cursor se ve la cadena de prerrequisitos y lo que desbloquea; modo para marcar aprobadas; color por criticidad; vista lista para móvil; carga de la historia académica (por semestre o pegando el texto de MARES) | OE1 |
| **Planificador** | El motor genera hasta 3 cargas sin choques (tope de créditos, franja, electivas) con horario semanal; modo manual con vista previa de grupos, detección de cruces y validación con el motor | OE2 |
| **Asistente** | Chat con el agente; cada respuesta muestra las fuentes consultadas (pensum, oferta, motor); puede compartir las materias aprobadas como contexto | OE3 |
| **Oferta y cupos** | Grupos, horarios, profesores y cupos en vivo; agrega grupos a la carga | OE2 |
| **Evaluación** | Cuestionario SUS con cálculo del puntaje, resultados con exportación a CSV y banco de 40 preguntas para medir la exactitud del asistente | OE3, OE4 |
| **Sobre el proyecto** | Problema, objetivos con indicadores, metodología y equipo | — |

La historia académica, la carga en edición, las conversaciones y las respuestas
de evaluación se guardan **solo en el navegador** (`localStorage`).

## Estructura

```
frontend/
├── index.html
├── public/favicon.svg
├── vite.config.js
└── src/
    ├── main.jsx                 # Montaje de React + MotionConfig
    ├── App.jsx                  # Shell: barra lateral, barra inferior móvil, rutas por hash
    ├── lib/
    │   ├── api.js               # Única capa que habla con la API
    │   ├── AppContext.jsx       # Estado global: malla, historia, carga, tema, servidor
    │   ├── malla.js             # Estados, recorridos del grafo y disposición por columnas
    │   ├── horario.js           # Días, horas, cruces y colores
    │   ├── evaluacion.js        # Ítems SUS y banco de preguntas
    │   └── storage.js           # localStorage seguro y exportación CSV
    ├── components/              # Logo, MallaGrafo, MallaMini, Horario, Grupos, PanelMateria…
    ├── views/                   # Inicio, Malla, Planificador, Asistente, Oferta, Evaluacion, Proyecto
    └── styles/                  # base.css (tokens), shell.css, vistas.css
```

## Cliente API (`src/lib/api.js`)

| Función | Endpoint |
|---|---|
| `salud()` | `GET /health` |
| `obtenerMalla()` | `GET /pensum/malla` |
| `obtenerResumenGrafo()` | `GET /pensum/grafo` |
| `listarCursos()` / `obtenerGrupos(c)` | `GET /cursos`, `GET /cursos/{codigo}/grupos` |
| `proponerCargas(...)` | `POST /planeacion/proponer` |
| `validarCarga(...)` | `POST /planeacion/validar` |
| `enviarMensaje(...)` / `obtenerSugerencias(...)` | `POST /chat`, `POST /chat/sugerencias` |

## Ejecutar

```bash
npm install
cp .env.example .env.local   # Windows: copy .env.example .env.local
npm run dev                  # http://localhost:5173
```

`VITE_API_URL` apunta al backend (por defecto `http://localhost:8000`). En Vercel
se configura como variable de entorno con la URL de Render.

## Logo

El logo actual es un SVG provisional en `src/components/Logo.jsx` y
`public/favicon.svg`. Para usar el definitivo, reemplaza esos dos SVG (o pon
`logo.svg` en `public/` y cámbialo en `Logo.jsx`).
