# OE1 — Verificación del modelo computable del plan de estudios

Generado el 2026-11-18 con `backend/scripts/verificar_modelo.py`.
Fuente: pensum versión 5 del programa 504 (origen de los datos: **snapshot**).

## Indicadores

| Indicador | Resultado |
|---|---|
| Espacios del plan modelados | 55 (44 obligatorias + 11 espacios electivos) |
| Créditos para grado | 168 (128 obligatorios + 40 electivos); Cursum: 168 |
| Niveles | 10 |
| Materias de Cursum modeladas | 108 (44 obligatorias y 64 del banco de electivas) |
| Aristas de prerrequisito | 86 |
| Correquisitos | 5 |
| Grafo acíclico (Kahn) | Sí |
| Orden topológico cubre todas las materias | Sí |
| Prerrequisitos en niveles anteriores | Sí, sin hallazgos |
| **Coincidencia con el plan publicado (por espacio)** | **96.4 %** (53/55) — meta ≥ 95 % |
| Coincidencia por atributo (nivel, créditos, requisitos) | 99.3 % (273/275) |

## Plan por niveles (AF 868)

| Nivel | Obligatorias | Espacios electivos | Créditos |
|---|---|---|---|
| 1 | 7 | — | 16 |
| 2 | 6 | — | 17 |
| 3 | 5 | — | 17 |
| 4 | 6 | — | 17 |
| 5 | 4 | E-FIS | 16 |
| 6 | 6 | — | 18 |
| 7 | 4 | E-LAB, E-LEP1 | 18 |
| 8 | 5 | E-LEP2 | 18 |
| 9 | 1 | E-LEP3, E-LEC1, E-LEC2, E-SH1, E-SH2 | 16 |
| 10 | 0 | E-SH3, E-PRA | 15 |

## Requisitos por créditos aprobados (tipo PRERREQCRED en Cursum)

- 16 créditos aprobados: 5 materias
- 48 créditos aprobados: 6 materias
- 60 créditos aprobados: 5 materias
- 65 créditos aprobados: 1 materias
- 80 créditos aprobados: 1 materias
- 132 créditos aprobados: 5 materias

Requisitos con código que no existe en la versión vigente: ninguno.

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

## Cotejo con el plan publicado (Acuerdo de Facultad 868 del 6 de febrero de 2019)

Detalle completo: `docs/datos/cotejo_plan_publicado.csv`. Espacios con diferencias o con reemplazo de código:

| Espacio | Diferencia | Nota |
|---|---|---|
| Lectoescritura | Coincide | En el modelo es Español Académico (2539130), que reemplazó a 2539101. |
| Lógica Y Representación Iii | prerrequisitos: plan [Lógica Y Representación Ii], modelo [Lógica Y Representación Ii, Teoría De La Probabilidad Y Colas] |  |
| Formación Ciudadana Y Constitucional | créditos exigidos: plan [40], modelo [ninguno] | En el modelo es Cátedra De Formación Ciudadana Y Constitucional (2517450), que reemplazó a 2517362. |

Ajustes aplicados al modelo porque Cursum no los refleja: Proyecto Integrador I exige 80 créditos aprobados
(Lineamientos PI 2026-2 y AF 868) y el requisito antiguo 2539101 (Lectoescritura) se cumple con Español
Académico (2539130), que la reemplazó en el mismo espacio.
