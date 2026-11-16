"""
Auditor INDEPENDIENTE de restricciones duras (OE2).

Reimplementa desde cero, sin reutilizar validador_service, la verificación de
una carga propuesta. Sirve para medir el indicador del OE2 ("≥ 90 % de las
propuestas cumple todas las restricciones duras") sin que el motor se califique
a sí mismo. Trabaja con minutos (no con horas enteras) para detectar también
solapes parciales.
"""
from __future__ import annotations

DIAS = {"lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"}


def _min(hhmm: str) -> int:
    h, _, m = hhmm.partition(":")
    return int(h) * 60 + int(m or 0)


def _intervalos(grupo) -> list[tuple[str, int, int]]:
    return [(s.dia, _min(s.hora_inicio), _min(s.hora_fin)) for s in grupo.horario]


def auditar(carga: list[dict], pensum: list, oferta: list, aprobadas: set[int], creditos_max: int, franja: str | None = None) -> list[str]:
    """Devuelve la lista de violaciones (vacía si la carga cumple todo).

    carga: [{"codigo": int, "grupo": str}, ...]
    pensum: objetos con .codigo .creditos .requisitos[.codigo .tipo]
    oferta: objetos con .codigo (str) y .grupos[.numero .cupos_disponibles .horario]
    """
    v: list[str] = []
    p = {m.codigo: m for m in pensum}
    o = {int(m.codigo): m for m in oferta}
    codigos = [c["codigo"] for c in carga]
    creditos_previos = sum(p[c].creditos for c in aprobadas if c in p)

    if len(set(codigos)) != len(codigos):
        v.append("materia repetida en la carga")

    intervalos = []
    total = 0
    for item in carga:
        c = item["codigo"]
        m = p.get(c)
        if m is None:
            v.append(f"{c}: no existe en el plan")
            continue
        total += m.creditos
        if c in aprobadas:
            v.append(f"{c}: ya aprobada")
        for r in m.requisitos:
            t = r.tipo.upper()
            if t == "PRERREQ" and r.codigo not in aprobadas:
                v.append(f"{c}: falta prerrequisito {r.codigo}")
            elif t == "CORREQ" and r.codigo not in aprobadas and r.codigo not in codigos:
                v.append(f"{c}: falta correquisito {r.codigo}")
            elif t == "CREDITOS" and creditos_previos < r.codigo:
                v.append(f"{c}: exige {r.codigo} créditos aprobados")
        ofertada = o.get(c)
        if ofertada is None:
            v.append(f"{c}: no ofertada")
            continue
        grupo = next((g for g in ofertada.grupos if g.numero.lstrip("0") == str(item["grupo"]).lstrip("0")), None)
        if grupo is None:
            v.append(f"{c}: grupo {item['grupo']} inexistente")
            continue
        if grupo.cupos_disponibles <= 0:
            v.append(f"{c}: grupo {grupo.numero} sin cupo")
        for dia, ini, fin in _intervalos(grupo):
            if dia not in DIAS or ini >= fin:
                v.append(f"{c}: sesión mal formada")
            if franja == "manana" and fin > 12 * 60:
                v.append(f"{c}: fuera de la franja de la mañana")
            if franja == "tarde" and not (12 * 60 <= ini and fin <= 18 * 60):
                v.append(f"{c}: fuera de la franja de la tarde")
            if franja == "noche" and ini < 18 * 60:
                v.append(f"{c}: fuera de la franja de la noche")
            for c2, d2, i2, f2 in intervalos:
                if dia == d2 and ini < f2 and i2 < fin:
                    v.append(f"cruce de horario entre {c} y {c2} ({dia})")
            intervalos.append((c, dia, ini, fin))

    if total > creditos_max:
        v.append(f"supera el tope de créditos ({total} > {creditos_max})")
    return v
