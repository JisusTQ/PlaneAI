"""Análisis SUS (OE4)."""
import csv

from scripts.analizar_sus import analizar, leer, puntaje


def test_puntaje_sus_extremos():
    assert puntaje([5, 1] * 5) == 100
    assert puntaje([1, 5] * 5) == 0
    assert puntaje([3] * 10) == 50


def test_leer_combina_y_quita_duplicados(tmp_path):
    cab = ["participante", "fecha", *[f"p{i}" for i in range(1, 11)], "puntaje_sus", "comentario"]
    filas = [["P01", "2026-11-16", *[5, 1] * 5, 100, "Muy útil"], ["P02", "2026-11-16", *[4, 2] * 5, 75, ""]]
    for nombre in ("a.csv", "b.csv"):  # el mismo archivo exportado dos veces
        with open(tmp_path / nombre, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cab)
            w.writerows(filas)
    datos = leer([str(tmp_path / "a.csv"), str(tmp_path / "b.csv")])
    a = analizar(datos)
    assert a["n"] == 2 and a["media"] == 87.5 and a["comentarios"] == ["Muy útil"]
    assert not a["cumple_indicador"]  # faltan participantes
