# Protocolo de evaluación con usuarios — PlaneAI (OE4)

**Objetivo.** Medir la usabilidad del prototipo con estudiantes de Ingeniería de Sistemas de la UdeA
mediante la escala SUS (Brooke, 1996) y recoger hallazgos cualitativos para el reporte de mejoras.
**Meta del indicador:** puntaje SUS promedio ≥ 68 con al menos 15 estudiantes.

## 1. Participantes

- Mínimo 15 estudiantes activos del programa, idealmente repartidos entre semestres bajos (1–3), medios (4–6) y altos (7+).
- Criterio de exclusión: integrantes del equipo y personas que hayan participado en el desarrollo.
- Se registra solo un código anónimo (P01, P02…) y el semestre; no se piden nombres ni documentos.

## 2. Roles por sesión

| Rol | Responsable | Tarea |
|---|---|---|
| Moderador | (integrante) | Lee el guion, presenta las tareas y no ayuda salvo bloqueo total. |
| Observador | (integrante) | Toma tiempos, anota errores, dudas y comentarios en la hoja de observación. |

## 3. Preparación (antes de cada sesión)

1. Abrir https://plane-ai-udea.vercel.app y esperar a que el indicador del servidor quede en verde (el backend gratuito de Render puede tardar ~1 minuto en despertar).
2. En **Evaluación → Resultados**, confirmar que el equipo está registrando en el mismo navegador de las sesiones anteriores o, si es otro computador, exportar/importar el CSV al final.
3. Borrar el progreso de la sesión anterior: en **Mi malla**, quitar las materias aprobadas; en el **Asistente**, iniciar conversación nueva.

## 4. Guion (20–25 minutos)

**Bienvenida (2 min).** "Gracias por participar. Vamos a evaluar la herramienta, no a ti: no hay respuestas
incorrectas. Piensa en voz alta mientras la usas. Tus respuestas son anónimas y solo se usan para el
proyecto de curso. Puedes retirarte cuando quieras." Confirmar consentimiento verbal y anotarlo.

**Tareas (15 min).** Leer cada tarea y dejar que el participante la resuelva solo.

| # | Tarea | Éxito si… | Tiempo esperado |
|---|---|---|---|
| T1 | "Registra en PlaneAI las materias que ya aprobaste" (puede usar *Mi malla* o importar la historia de MARES). | Las materias aprobadas quedan marcadas. | 3 min |
| T2 | "Pide una propuesta de horario para el próximo semestre que solo use la franja que prefieras." (*Planificador*) | Obtiene al menos una carga y la puede leer en el horario semanal. | 3 min |
| T3 | "Arma tu propia carga con dos materias y verifica si es válida." (*Planificador* → validar) | Identifica el veredicto y, si hay error, entiende por qué. | 3 min |
| T4 | "Pregúntale al asistente cuántas veces puedes cancelar una materia." (*Asistente*) | Lee la respuesta y reconoce la fuente citada (art. 75). | 2 min |
| T5 | "Averigua qué grupos de Cálculo Integral tienen cupo." (*Oferta y cupos* o *Asistente*) | Encuentra al menos un grupo con su horario. | 2 min |

**Cuestionario SUS (3 min).** Abrir **Evaluación → Cuestionario**, escribir el código del participante
(P01…) y dejar que responda las 10 afirmaciones y el comentario opcional.

**Cierre (2 min).** Preguntas abiertas: ¿qué fue lo más útil?, ¿qué fue lo más confuso?, ¿la usarías en tu
próxima matrícula?, ¿confías en las cargas que propone? Anotar las respuestas.

## 5. Hoja de observación (una por participante)

| Campo | Valor |
|---|---|
| Código / semestre | |
| Consentimiento verbal | Sí / No |
| T1…T5: éxito (sí / con ayuda / no) y tiempo | |
| Errores o dudas observadas | |
| Comentarios en voz alta relevantes | |
| Respuestas del cierre | |

## 6. Datos y análisis

1. Al terminar todas las sesiones, en **Evaluación → Resultados** pulsar **Exportar CSV** en cada computador usado
   (o **Importar CSV** para unirlos en uno).
2. Ejecutar `cd backend && python scripts/analizar_sus.py ruta/planeai-sus.csv` → genera
   `docs/resultados/oe4_sus.md` con promedio, IC 95 %, resultados por ítem y comentarios.
3. Completar en ese archivo la tabla **Hallazgos y acciones de mejora** con la evidencia de las hojas de
   observación (tareas con más errores, ítems SUS más débiles, comentarios repetidos).

---

## Anexo A — Encuesta estructurada (fase F1, mínimo 20 estudiantes)

1. Semestre actual y número de matrículas realizadas en la UdeA.
2. ¿Cuánto tiempo dedicas a planear tu matrícula antes de tu tanda? (< 15 min / 15–60 min / 1–3 h / > 3 h)
3. ¿Qué fuentes consultas? (MARES, malla en PDF, portal de cupos, asesor, compañeros, grupos de WhatsApp, otra)
4. En tu última matrícula, ¿te pasó alguna de estas situaciones? (no alcanzaste cupo; inscribiste algo sin el prerrequisito; tuviste cruce de horario; quedaste con menos créditos de los que querías; cancelaste por mala planeación)
5. Del 1 al 5, ¿qué tan difícil es armar un horario sin cruces con las materias que te corresponden?
6. Del 1 al 5, ¿qué tan claro tienes las reglas de créditos mínimos/máximos y cancelaciones del Reglamento?
7. ¿Usarías un asistente que te proponga cargas válidas y te explique por qué? (sí / tal vez / no) ¿Por qué?
8. ¿Qué función sería imprescindible para ti?

## Anexo B — Guion de entrevista en profundidad (fase F1, 5 estudiantes, 20 min)

1. Cuéntame paso a paso cómo preparaste tu última matrícula.
2. ¿Qué fue lo más difícil o estresante durante la tanda de 30 minutos?
3. ¿Alguna vez una mala decisión de matrícula te retrasó? ¿Qué pasó?
4. ¿Cómo decides qué materias priorizar cuando no te caben todas?
5. ¿Has consultado el Reglamento Estudiantil? ¿Para qué y qué tan fácil fue?
6. Si tuvieras un asistente, ¿qué le preguntarías primero? ¿Qué necesitarías para confiar en lo que te propone?
