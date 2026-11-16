// Lógica de la malla en el cliente: estados por materia, recorridos del grafo y disposición para dibujarlo.
export const NIVEL_ELECTIVAS = 99;

// Tipos normalizados por el backend: PRERREQ, CORREQ, CREDITOS (el "código" es el
// número de créditos aprobados exigidos) y EXTERNO (materia de otra versión del plan).
export const esPre = (r) => (r.tipo || "").toUpperCase() === "PRERREQ";
export const esCo = (r) => (r.tipo || "").toUpperCase() === "CORREQ";
export const esCreditos = (r) => (r.tipo || "").toUpperCase() === "CREDITOS";
export const esExterno = (r) => (r.tipo || "").toUpperCase() === "EXTERNO";

export const etiquetaNivel = (n) => (n === NIVEL_ELECTIVAS ? "Electivas" : `Semestre ${n}`);
export const etiquetaNivelCorta = (n) => (n === NIVEL_ELECTIVAS ? "Elect." : `S${n}`);

/** aprobada | habilitada | bloqueada (prerrequisitos y créditos aprobados mínimos). */
export function estadoMateria(m, aprobadas, creditosAcumulados = 0) {
  if (aprobadas.has(m.codigo)) return "aprobada";
  const pre = m.requisitos.filter(esPre).every((r) => aprobadas.has(r.codigo));
  const cred = m.requisitos.filter(esCreditos).every((r) => creditosAcumulados >= r.codigo);
  return pre && cred ? "habilitada" : "bloqueada";
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
export function disponer(materias, { incluirElectivas = false, espacios = [] } = {}) {
  const visibles = materias.filter((m) => incluirElectivas || m.nivel !== NIVEL_ELECTIVAS);
  // Los espacios electivos del plan oficial (línea de énfasis, socio-humanísticas,
  // práctica académica...) se dibujan al final de su columna, como en el gráfico de la Facultad.
  const niveles = [...new Set([...visibles.map((m) => m.nivel), ...espacios.map((e) => e.nivel)])].sort((a, b) => a - b);
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

  const espaciosDe = (n) => espacios.filter((e) => e.nivel === n);
  const maxFilas = Math.max(1, ...columnas.map((c, i) => c.length + espaciosDe(niveles[i]).length));
  const altoUtil = maxFilas * NODO.h + (maxFilas - 1) * NODO.gapY;
  const pos = new Map();
  const posEspacios = new Map();
  columnas.forEach((col, c) => {
    const extra = espaciosDe(niveles[c]);
    const filas = col.length + extra.length;
    const alto = filas * NODO.h + (filas - 1) * NODO.gapY;
    const y0 = NODO.padTop + (altoUtil - alto) / 2;
    const x = NODO.padX + c * (NODO.w + NODO.gapX);
    col.forEach((m, i) => pos.set(m.codigo, { x, y: y0 + i * (NODO.h + NODO.gapY) }));
    extra.forEach((e, i) => posEspacios.set(e.id, { x, y: y0 + (col.length + i) * (NODO.h + NODO.gapY) }));
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
    posEspacios,
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
