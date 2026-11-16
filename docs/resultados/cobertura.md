# Cobertura de pruebas del backend — 2026-11-15

```
........................................................................ [ 79%]
...................                                                      [100%]
.venv/lib/python3.13/site-packages/starlette/testclient.py:40

================================ tests coverage ================================
_______________ coverage: platform linux, python 3.13.18-final-0 _______________

Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
app/__init__.py                             0      0   100%
app/config.py                              19      0   100%
app/main.py                                28      8    71%
app/routers/__init__.py                     0      0   100%
app/routers/chat.py                        18      6    67%
app/routers/cursos.py                      29     17    41%
app/routers/evaluacion.py                  19      4    79%
app/routers/planeacion.py                  66      9    86%
app/schemas/__init__.py                     0      0   100%
app/schemas/chat.py                        23      0   100%
app/schemas/curso.py                       38      0   100%
app/services/__init__.py                    0      0   100%
app/services/evaluacion_service.py         36      1    97%
app/services/gemini_service.py            183     51    72%
app/services/grafo_service.py              78      1    99%
app/services/rag_service.py               106      0   100%
app/services/reglas_service.py              9      0   100%
app/services/udea_horarios_service.py     129     41    68%
app/services/udea_pensum_service.py        92     26    72%
app/services/validador_service.py         217      3    99%
-----------------------------------------------------------
TOTAL                                    1090    167    85%
91 passed, 1 warning in 9.07s
```
