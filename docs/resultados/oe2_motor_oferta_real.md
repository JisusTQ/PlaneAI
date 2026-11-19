# OE2 — Banco de casos del motor de validación y recomendación

Generado el 2026-11-18 con `backend/scripts/banco_motor.py`. Datos: plan real v5 (snapshot) + oferta REAL de MARES (OFERTA_MARES_2026-11-18T21:32:55.353Z, 475 grupos de 78 materias del plan).
Cada carga propuesta por el motor se verificó con un auditor independiente
(`backend/scripts/auditor.py`) que reimplementa las restricciones duras:
existencia en el plan, no aprobada, prerrequisitos, correquisitos, créditos
aprobados mínimos, oferta, grupo y cupo, cruces de horario al minuto, franja
pedida y tope de créditos.

## Resultado del indicador

| Casos | Propuestas generadas | Cumplen todas las restricciones | Porcentaje | Meta |
|---|---|---|---|---|
| 25 | 49 | 49 | **100.0 %** | ≥ 90 % → cumplida |

## Escenarios

| Caso | Descripción | Franja | Tope | Propuestas | Cumplen | Créditos por propuesta |
|---|---|---|---|---|---|---|
| E01 | Primíparo sin materias aprobadas | cualquiera | 24 | 1 | 1 | 15 |
| E02 | Aprobó todo el nivel 1 | cualquiera | 24 | 1 | 1 | 19 |
| E03 | Aprobó niveles 1 y 2 | cualquiera | 24 | 1 | 1 | 18 |
| E04 | Aprobó niveles 1 a 3 | cualquiera | 24 | 1 | 1 | 19 |
| E05 | Aprobó niveles 1 a 4 | cualquiera | 24 | 3 | 3 | 21, 21, 22 |
| E06 | Aprobó niveles 1 a 5 | cualquiera | 24 | 3 | 3 | 24, 23, 23 |
| E07 | Aprobó niveles 1 a 6 | cualquiera | 24 | 1 | 1 | 22 |
| E08 | Aprobó niveles 1 a 7 | cualquiera | 24 | 1 | 1 | 15 |
| E09 | Aprobó niveles 1 a 8 (solo le queda Ética y la modalidad de grado) | cualquiera | 24 | 3 | 3 | 22, 22, 22 |
| E10 | Primíparo que solo estudia en la mañana | manana | 24 | 3 | 3 | 14, 12, 9 |
| E11 | Niveles 1-2 aprobados, solo en la tarde | tarde | 24 | 1 | 1 | 8 |
| E12 | Niveles 1-4 aprobados, solo en la noche | noche | 24 | 1 | 1 | 3 |
| E13 | Niveles 1-3 aprobados con tope de 12 créditos (trabaja) | cualquiera | 12 | 3 | 3 | 12, 12, 12 |
| E14 | Niveles 1-3 aprobados con tope de 16 créditos | cualquiera | 16 | 3 | 3 | 16, 15, 16 |
| E15 | Niveles 1-5 aprobados, quiere el máximo (24) | cualquiera | 24 | 3 | 3 | 24, 23, 23 |
| E16 | Perdió Cálculo Diferencial en nivel 1 | cualquiera | 24 | 1 | 1 | 16 |
| E17 | Niveles 1-2 sin Matemáticas Discretas I (rezago en la cadena crítica) | cualquiera | 24 | 1 | 1 | 11 |
| E18 | Niveles 1-3 sin Técnicas de Programación | cualquiera | 24 | 1 | 1 | 16 |
| E19 | Niveles 1-4 sin Inglés 3 ni Métodos Estadísticos | cualquiera | 24 | 3 | 3 | 21, 21, 22 |
| E20 | Niveles 1-5 incluyendo electivas habilitadas | cualquiera | 24 | 3 | 3 | 24, 23, 24 |
| E21 | Niveles 1-6 con electivas y tope de 15 créditos | cualquiera | 15 | 3 | 3 | 15, 14, 15 |
| E22 | Estudiante irregular: niveles 1-3 más Bases de Datos adelantada | cualquiera | 24 | 1 | 1 | 23 |
| E23 | Niveles 1-2 sin Lógica I (correquisitos en juego) | cualquiera | 24 | 1 | 1 | 14 |
| E24 | Niveles 1-6 solo en la mañana con electivas | manana | 24 | 3 | 3 | 19, 19, 20 |
| E25 | Niveles 1-7 con tope de 10 créditos | cualquiera | 10 | 3 | 3 | 9, 10, 8 |

Todos los escenarios produjeron al menos una propuesta.

## Violaciones encontradas por el auditor

Ninguna.
