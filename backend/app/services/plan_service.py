"""
Estructura del plan de estudios oficial y cotejo con el modelo.  [OE1]

El plan publicado (Acuerdo de Facultad 868 de 2019, gráfico oficial V.5) tiene
55 espacios y 168 créditos en 10 niveles: 44 asignaturas obligatorias y 11
espacios electivos (curso alternativo de física y su laboratorio, tres de la
línea de énfasis principal, dos de la complementaria, tres socio-humanísticas y
la práctica académica). Cursum publica las obligatorias por nivel y las
electivas en un "banco" (nivel 99) agrupadas por categoría; este módulo une
ambas vistas:

  - `estructura()`: los 10 niveles con obligatorias y espacios electivos, y las
    materias del banco que pueden cursarse en cada espacio.
  - `cotejo()`: compara espacio por espacio el plan publicado con el modelo
    computable (nivel, créditos, prerrequisitos, correquisitos y créditos
    exigidos) y calcula el porcentaje de coincidencia del indicador del OE1.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from app.services import udea_pensum_service as pensum

PLAN = Path(__file__).resolve().parent.parent / "data" / "plan_publicado_af868.json"

# Bancos de Cursum que alimentan cada tipo de espacio electivo del plan.
BANCOS_ENFASIS = [
    "LÍNEA ENFÁSIS ING SOFTWARE Y SISTEMAS INFORMACIÓN",
    "ENFÁSIS CIENCIA DE LA COMPUTACIÓN",
    "ENFÁSIS ING DE COMPUTADORES Y COMUNICACIÓN DATOS",
]
# Asignaturas que la versión vigente reemplazó dentro del mismo espacio del plan
# (código del plan publicado -> código en Cursum).
REEMPLAZOS = {**pensum.EQUIVALENCIAS, 2517362: 2517450}  # Formación ciudadana -> Cátedra de formación ciudadana


@lru_cache
def plan_publicado() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def espacios_electivos() -> list[dict]:
    return [e for e in plan_publicado()["espacios"] if e["tipo"] == "electiva"]


def bancos_de(espacio: dict) -> list[str]:
    bancos = []
    for b in espacio.get("bancos", []):
        bancos += BANCOS_ENFASIS if b == "ENFASIS" else [b]
    return bancos


def _opciones(espacio: dict, materias: list[pensum.MateriaPensum]) -> list[pensum.MateriaPensum]:
    bancos = set(bancos_de(espacio))
    return [m for m in materias if m.nivel == pensum.NIVEL_ELECTIVAS and m.banco in bancos]


def estructura(materias: list[pensum.MateriaPensum]) -> dict:
    """Plan por niveles (1..10) con obligatorias y espacios electivos."""
    niveles: dict[int, dict] = defaultdict(lambda: {"obligatorias": [], "electivos": [], "creditos": 0})
    for m in materias:
        if m.nivel != pensum.NIVEL_ELECTIVAS:
            niveles[m.nivel]["obligatorias"].append(m.codigo)
            niveles[m.nivel]["creditos"] += m.creditos
    espacios = []
    for e in espacios_electivos():
        opciones = _opciones(e, materias)
        niveles[e["nivel"]]["electivos"].append(e["id"])
        niveles[e["nivel"]]["creditos"] += e["creditos"]
        espacios.append(
            {
                "id": e["id"],
                "nombre": e["nombre"],
                "nivel": e["nivel"],
                "creditos": e["creditos"],
                "bancos": bancos_de(e),
                "opciones": [m.codigo for m in opciones],
            }
        )
    oblig = [m for m in materias if m.nivel != pensum.NIVEL_ELECTIVAS]
    return {
        "niveles": {str(k): v for k, v in sorted(niveles.items())},
        "espacios_electivos": espacios,
        "total_espacios": len(oblig) + len(espacios),
        "total_creditos": sum(m.creditos for m in oblig) + sum(e["creditos"] for e in espacios),
        "total_niveles": len(niveles),
        "creditos_grado_cursum": pensum.creditos_grado(),
    }


def _reqs_plan(espacio: dict) -> dict[str, set[int]]:
    r: dict[str, set[int]] = {"pre": set(), "co": set(), "creditos": set()}
    for x in espacio["requisitos"]:
        valor = REEMPLAZOS.get(x["valor"], x["valor"]) if x["tipo"] != "creditos" else x["valor"]
        r[x["tipo"]].add(valor)
    return r


def _reqs_modelo(m: pensum.MateriaPensum) -> dict[str, set[int]]:
    return {
        "pre": {r.codigo for r in m.requisitos if pensum.es_prerrequisito(r)},
        "co": {r.codigo for r in m.requisitos if pensum.es_correquisito(r)},
        "creditos": {r.codigo for r in m.requisitos if pensum.es_req_creditos(r)},
    }


def cotejo(materias: list[pensum.MateriaPensum]) -> dict:
    """Compara el plan publicado con el modelo, espacio por espacio y atributo
    por atributo (identidad, nivel, créditos y requisitos)."""
    idx = {m.codigo: m for m in materias}
    nombre = lambda c: idx[c].nombre.title() if c in idx else str(c)  # noqa: E731
    filas, atributos, coinciden_atrib = [], 0, 0

    def comparar(e: dict, m: pensum.MateriaPensum | None, nivel_modelo, creditos_modelo, reqs_modelo, nota=""):
        nonlocal atributos, coinciden_atrib
        dif = []
        rp = _reqs_plan(e)
        checks = [
            ("nivel", e["nivel"] == nivel_modelo, f"nivel {e['nivel']} en el plan y {nivel_modelo} en el modelo"),
            ("créditos", e["creditos"] == creditos_modelo, f"{e['creditos']} créditos en el plan y {creditos_modelo} en el modelo"),
        ]
        for tipo, rotulo in (("pre", "prerrequisitos"), ("co", "correquisitos"), ("creditos", "créditos exigidos")):
            a, b = rp[tipo], reqs_modelo[tipo]
            texto = lambda s: ", ".join(str(x) if tipo == "creditos" else nombre(x) for x in sorted(s)) or "ninguno"  # noqa: E731
            checks.append((rotulo, a == b, f"{rotulo}: plan [{texto(a)}], modelo [{texto(b)}]"))
        for _, ok, msg in checks:
            atributos += 1
            coinciden_atrib += ok
            if not ok:
                dif.append(msg)
        filas.append(
            {
                "espacio": e["nombre"],
                "codigo_plan": e["codigo"],
                "codigo_modelo": m.codigo if m else None,
                "nivel": e["nivel"],
                "coincide": not dif,
                "diferencias": dif,
                "nota": nota,
            }
        )

    for e in plan_publicado()["espacios"]:
        if e["tipo"] == "obligatoria":
            codigo = REEMPLAZOS.get(e["codigo"], e["codigo"])
            m = idx.get(codigo)
            nota = f"En el modelo es {m.nombre.title()} ({codigo}), que reemplazó a {e['codigo']}." if m and codigo != e["codigo"] else ""
            if m is None:
                atributos += 5
                filas.append({"espacio": e["nombre"], "codigo_plan": e["codigo"], "codigo_modelo": None, "nivel": e["nivel"], "coincide": False, "diferencias": ["no existe en el modelo"], "nota": ""})
                continue
            comparar(e, m, m.nivel, m.creditos, _reqs_modelo(m), nota)
        else:
            opciones = _opciones(e, materias)
            # El espacio coincide si el banco ofrece opciones con los créditos del
            # espacio; los requisitos se comparan con los comunes a todas las opciones.
            creditos_ok = [m for m in opciones if m.creditos == e["creditos"]]
            reqs = [_reqs_modelo(m) for m in creditos_ok]
            comunes = {k: set.intersection(*(r[k] for r in reqs)) if reqs else set() for k in ("pre", "co", "creditos")}
            if e["requisitos"] == [] and reqs:
                comunes = {k: set() for k in comunes}  # los requisitos propios de cada electiva no aplican al espacio
            nota = f"{len(opciones)} opciones en Cursum ({', '.join(bancos_de(e))})."
            comparar(e, None, e["nivel"] if opciones else None, e["creditos"] if creditos_ok else None, comunes, nota)

    n_ok = sum(1 for f in filas if f["coincide"])
    return {
        "plan": plan_publicado()["acto"],
        "espacios": len(filas),
        "espacios_coinciden": n_ok,
        "porcentaje_espacios": round(100 * n_ok / len(filas), 1),
        "atributos": atributos,
        "atributos_coinciden": coinciden_atrib,
        "porcentaje_atributos": round(100 * coinciden_atrib / atributos, 1),
        "detalle": filas,
    }
