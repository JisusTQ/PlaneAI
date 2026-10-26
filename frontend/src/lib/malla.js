// Lógica de la malla en el cliente: estados por materia, recorridos del grafo y disposición para dibujarlo.
export const NIVEL_ELECTIVAS = 99;

export const esPre = (r) => (r.tipo || "").toUpperCase().startsWith("PRE");
export const esCo = (r) => (r.tipo || "").toUpperCase().startsWith("CO");

export const etiquetaNivel = (n) => (n === NIVEL_ELECTIVAS ? "Electivas" : `Semestre ${n}`);
export const etiquetaNivelCorta = (n) => (n === NIVEL_ELECTIVAS ? "Elect." : `S${n}`);

/** aprobada | habilitada | bloqueada */
export function estadoMateria(m, aprobadas) {
  if (aprobadas.has(m.codigo)) return "aprobada";
  return m.requisitos.filter(esPre).every((r) => aprobadas.has(r.codigo)) ? "habilitada" : "bloqueada";
}

/** Índices de sucesores (prerrequisito -> materias que lo exigen) y predecesores. */
export function indices(materias) {
  const porCodigo = new Map(materias.map((m) => [m.codigo, m]));
  const sucesores = new Map(materias.map((m) => [m.codigo, []]));
  for (const m of materias)
    for (const r of m.requisitos) if (esPre(r) && sucesores.has(r.codigo)) sucesores.get(r.codigo).push(m.codigo);
  return { porCodigo, sucesores };
}

export function ancestros(codigo, porCodigo) {
  const vistos = new Set();
  const pila = [codigo];
  while (pila.length) {
    const m = porCodigo.get(pila.pop());
    if (!m) continue;
    for (const r of m.requisitos)
      if (esPre(r) && !vistos.has(r.codigo)) {
        vistos.add(r.codigo);
        pila.push(r.codigo);
      }
  }
  return vistos;
}

export function descendientes(codigo, sucesores) {
  const vistos = new Set();
  const pila = [codigo];
  while (pila.length)
    for (const s of sucesores.get(pila.pop()) || [])
      if (!vistos.has(s)) {
        vistos.add(s);
        pila.push(s);
      }
  return vistos;
}

/** Parte un nombre en máximo 2 líneas de ~n caracteres. */
export function partirNombre(nombre, n = 24) {
  const palabras = nombre.split(/\s+/);
  const lineas = [""];
  for (const p of palabras) {
    const actual = lineas[lineas.length - 1];
    if ((actual + " " + p).trim().length <= n) lineas[lineas.length - 1] = (actual + " " + p).trim();
    else if (lineas.length < 2) lineas.push(p);
    else {
      lineas[1] = (lineas[1] + " " + p).trim();
    }
  }
  if (lineas[1] && lineas[1].length > n) lineas[1] = lineas[1].slice(0, n - 1).trimEnd() + "…";
  return lineas;
}

export const NODO = { w: 178, h: 52, gapX: 52, gapY: 12, padX: 24, padTop: 54, padBottom: 24 };

/**
 * Disposición por columnas (una por nivel). El orden dentro de cada columna se
 * ajusta con el heurístico del baricentro para reducir cruces de aristas.
 */
export function disponer(materias, { incluirElectivas = false } = {}) {
  const visibles = materias.filter((m) => incluirElectivas || m.nivel !== NIVEL_ELECTIVAS);
  const niveles = [...new Set(visibles.map((m) => m.nivel))].sort((a, b) => a - b);
  const columnas = niveles.map((n) => visibles.filter((m) => m.nivel === n));
  const colDe = new Map();
  columnas.forEach((col, i) => col.forEach((m) => colDe.set(m.codigo, i)));

  const fila = new Map();
  const reindexar = () => columnas.forEach((col) => col.forEach((m, i) => fila.set(m.codigo, i)));
  reindexar();

  const { sucesores } = indices(visibles);
  const promedio = (lista) => (lista.length ? lista.reduce((a, b) => a + b, 0) / lista.length : null);

  for (let it = 0; it < 4; it++) {
    for (let c = 1; c < columnas.length; c++) {
      const bc = new Map(
        columnas[c].map((m) => [m.codigo, promedio(m.requisitos.filter((r) => esPre(r) && fila.has(r.codigo)).map((r) => fila.get(r.codigo)))])
      );
      columnas[c].sort((a, b) => (bc.get(a.codigo) ?? fila.get(a.codigo)) - (bc.get(b.codigo) ?? fila.get(b.codigo)));
      reindexar();
    }
    for (let c = columnas.length - 2; c >= 0; c--) {
      const bc = new Map(columnas[c].map((m) => [m.codigo, promedio((sucesores.get(m.codigo) || []).map((s) => fila.get(s)))]));
      columnas[c].sort((a, b) => (bc.get(a.codigo) ?? fila.get(a.codigo)) - (bc.get(b.codigo) ?? fila.get(b.codigo)));
      reindexar();
    }
  }

  const maxFilas = Math.max(1, ...columnas.map((c) => c.length));
  const altoUtil = maxFilas * NODO.h + (maxFilas - 1) * NODO.gapY;
  const pos = new Map();
  columnas.forEach((col, c) => {
    const alto = col.length * NODO.h + (col.length - 1) * NODO.gapY;
    const y0 = NODO.padTop + (altoUtil - alto) / 2;
    col.forEach((m, i) => pos.set(m.codigo, { x: NODO.padX + c * (NODO.w + NODO.gapX), y: y0 + i * (NODO.h + NODO.gapY) }));
  });

  const aristas = [];
  for (const m of visibles)
    for (const r of m.requisitos) {
      if (!pos.has(r.codigo)) continue;
      const a = pos.get(r.codigo);
      const b = pos.get(m.codigo);
      if (esPre(r)) {
        const x1 = a.x + NODO.w, y1 = a.y + NODO.h / 2, x2 = b.x, y2 = b.y + NODO.h / 2;
        const dx = Math.max(30, (x2 - x1) / 2);
        aristas.push({ id: `${r.codigo}-${m.codigo}`, de: r.codigo, a: m.codigo, tipo: "pre", d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}` });
      } else {
        const x1 = a.x, y1 = a.y + NODO.h / 2, x2 = b.x, y2 = b.y + NODO.h / 2;
        aristas.push({ id: `${r.codigo}~${m.codigo}`, de: r.codigo, a: m.codigo, tipo: "co", d: `M${x1},${y1} C${x1 - 26},${y1} ${x2 - 26},${y2} ${x2},${y2}` });
      }
    }

  return {
    pos,
    aristas,
    niveles,
    ancho: NODO.padX * 2 + columnas.length * NODO.w + (columnas.length - 1) * NODO.gapX,
    alto: NODO.padTop + altoUtil + NODO.padBottom,
    xColumna: (c) => NODO.padX + c * (NODO.w + NODO.gapX),
  };
}

/** Busca códigos de materias del pensum en un texto pegado (p. ej. la historia académica de MARES). */
export function detectarCodigos(texto, porCodigo) {
  const encontrados = new Set();
  for (const m of texto.matchAll(/\b(\d{7})\b/g)) {
    const c = Number(m[1]);
    if (porCodigo.has(c)) encontrados.add(c);
  }
  return encontrados;
}
