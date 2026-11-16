# OE1 — Verificación del modelo computable del plan de estudios

Generado el 2026-11-15 con `backend/scripts/verificar_modelo.py`.
Fuente: pensum versión 5 del programa 504 (origen de los datos: **snapshot**).

## Indicadores

| Indicador | Resultado |
|---|---|
| Materias del pensum modeladas | 108 (44 obligatorias, 64 electivas) |
| Créditos obligatorios | 128 |
| Niveles con obligatorias | 9 |
| Aristas de prerrequisito | 84 |
| Correquisitos | 5 |
| Grafo acíclico (Kahn) | Sí |
| Orden topológico cubre todas las materias | Sí |
| Prerrequisitos en niveles anteriores | Sí, sin hallazgos |
| Coincidencia con el plan publicado | hoja creada, pendiente de cotejo |

## Materias y créditos obligatorios por nivel

| Nivel | Materias | Créditos |
|---|---|---|
| 1 | 7 | 16 |
| 2 | 6 | 17 |
| 3 | 5 | 17 |
| 4 | 6 | 17 |
| 5 | 4 | 13 |
| 6 | 6 | 18 |
| 7 | 4 | 14 |
| 8 | 5 | 15 |
| 9 | 1 | 1 |

## Requisitos por créditos aprobados (tipo PRERREQCRED en Cursum)

- 16 créditos aprobados: 5 materias
- 48 créditos aprobados: 6 materias
- 60 créditos aprobados: 5 materias
- 65 créditos aprobados: 1 materias
- 132 créditos aprobados: 5 materias

Requisitos con código que no existe en la versión vigente: 2539101.

## Materias más críticas (dependientes transitivos)

| Materia | Nivel | Dependientes |
|---|---|---|
| ÁLGEBRA Y TRIGONOMETRÍA | 1 | 30 |
| CÁLCULO DIFERENCIAL | 1 | 30 |
| CÁLCULO INTEGRAL | 2 | 28 |
| TÉCNICAS DE PROGRAMACIÓN Y LABORATORIO | 3 | 28 |
| TEORÍA DE LA PROBABILIDAD Y COLAS | 3 | 19 |
| ANÁLISIS Y DISEÑO DE SISTEMAS I | 4 | 16 |
| LÓGICA Y REPRESENTACIÓN I | 2 | 14 |
| GEOMETRÍA VECTORIAL Y ANALÍTICA | 1 | 13 |
| LÓGICA Y REPRESENTACIÓN II | 3 | 13 |
| INTRODUCCIÓN A LA INGENIERÍA DE SISTEMAS | 1 | 12 |

## Consistencia de niveles

Todos los prerrequisitos de las materias obligatorias están en un nivel anterior y los correquisitos en el mismo nivel o uno anterior.

## Cotejo con el plan publicado

Estado: hoja creada, pendiente de cotejo. Hoja: `docs/datos/cotejo_plan_publicado.csv`. Para cada materia obligatoria, comparar nombre,
nivel, créditos y requisitos contra el documento oficial del plan y escribir `sí` o `no` en la columna
`coincide` (con la diferencia en `observacion`); luego volver a ejecutar este script.
