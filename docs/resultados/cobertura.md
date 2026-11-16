# Cobertura de pruebas del backend — 2026-11-16

```
........................................................................ [ 65%]
......................................                                   [100%]
.venv/lib/python3.13/site-packages/starlette/testclient.py:40

================================ tests coverage ================================
_______________ coverage: platform linux, python 3.13.18-final-0 _______________

Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
app/__init__.py                             0      0   100%
app/config.py                              21      0   100%
app/main.py                                32      8    75%
app/routers/__init__.py                     0      0   100%
app/routers/chat.py                        22      3    86%
app/routers/cursos.py                      29     17    41%
app/routers/evaluacion.py                  23      8    65%
app/routers/planeacion.py                  75     11    85%
app/schemas/__init__.py                     0      0   100%
app/schemas/chat.py                        23      0   100%
app/schemas/curso.py                       38      0   100%
app/services/__init__.py                    0      0   100%
app/services/evaluacion_service.py         36      1    97%
app/services/gemini_service.py            214     51    76%
app/services/grafo_service.py              84      1    99%
app/services/plan_service.py               82      3    96%
app/services/rag_service.py               124      0   100%
app/services/reglas_service.py              9      0   100%
app/services/udea_horarios_service.py     129     41    68%
app/services/udea_pensum_service.py       105     29    72%
app/services/validador_service.py         219      3    99%
-----------------------------------------------------------
TOTAL                                    1265    176    86%
110 passed, 1 warning in 10.26s
```
