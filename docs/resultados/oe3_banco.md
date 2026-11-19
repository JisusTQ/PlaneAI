# OE3 — Banco de 40 preguntas del asistente

Revisión del 2026-11-18 sobre `docs/resultados/oe3_banco.csv`.

| Indicador | Resultado | Meta |
|---|---|---|
| Preguntas evaluadas | 40 de 40 | 40 |
| Respuestas correctas | **95.0 %** (38) | ≥ 85 % |
| Respuestas con la fuente esperada | **100.0 %** | 100 % |
| Malla / Reglamento correctas | 18/20 / 20/20 | |
| Latencia de extremo a extremo (mediana / p90 / máx.) | 3.6 s / 6.1 s / 13.9 s | |
| Precalificación automática que coincide con la revisión humana | 37/40 | |
| Indicador del OE3 | Cumplido | |

## Respuestas incorrectas
- P10: ¿Cuál es la materia de la que más materias dependen en el pensum? — Incorrecta: responde Cálculo Integral (28 dependientes); la respuesta es Álgebra y Trigonometría y Cálculo Diferencial (30 cada una). Pregunta de agregación global: ninguna herramienta devuelve el ranking de criticidad.
- P16: ¿Cuántos cursos de inglés tiene el plan de estudios? — Incorrecta: afirma que el plan no tiene cursos de inglés; tiene English 1 a 5. Pregunta de conteo transversal a varios niveles.

## Respuestas sin la fuente esperada
Ninguna.
