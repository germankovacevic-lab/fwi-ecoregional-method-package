// Semáforo FWI por ECORREGIÓN (v4, 17/11/2026) — reemplaza la clase por "peor zona" de fwi_clases.js.
//
// Unidad de cálculo: las ecorregiones oficiales del Ministerio de Ambiente (2021), sin cortes provinciales.
//  1. Cada punto (89 zonas v4.1) calcula su FWI vivo (Open-Meteo) y lo lleva a su equivalente ERA5 por mapeo de
//     cuantiles (misma aritmética que fwi_clases.js / tools/fwi_snmf/03_calibracion.py).
//  2. FWI de la ecorregión = promedio de los equivalentes de sus puntos, ponderado por el fuego histórico de cada
//     punto (peso_eco). Clase = cortes propios de la ecorregión (umbral de ocurrencia SNMF: p10/25/50/75 del FWI en
//     sus días de fuego fuerte, ERA5 2012–2025).
//  3. Provincia = redondeo (medio hacia arriba) del promedio de los niveles de sus ecorregiones, ponderado por la
//     fracción de su fuego histórico en cada una. El mapa muestra además la clase de cada ecorregión.
// Calibración: worker/src/fwi_ecorregional.json (tools/auditoria_zonas/20_calibracion_fwi_ecorregional.py).
// Verificación fuera de muestra 2022–2026: tools/auditoria_zonas/16_fwi_ecorregional.py (REGLAS_ZONAS_v4 §R5c).
// ESM puro, sin estado: corre en node y en Cloudflare Workers.
import CAL from './fwi_ecorregional.json' with { type: 'json' };

export const CALIBRACION_ECO = CAL;

/** FWI vivo de un punto → equivalente ERA5 (mapeo de cuantiles, convención de numpy para empates). */
export function equivalenteEra5Eco(zid, fwi) {
  const z = CAL.zonas[zid];
  if (!z) return null;
  const qv = z.q_vivo, qe = z.q_era5, n = qv.length;
  if (!(fwi > qv[0])) return qe[0];
  if (fwi >= qv[n - 2]) return Math.max(qe[n - 2], fwi * z.cola);
  let lo = 0, hi = n - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (qv[m] <= fwi) lo = m; else hi = m - 1; }
  if (qv[lo] === fwi) return qe[lo];
  const d = qv[lo + 1] - qv[lo];
  return d > 0 ? qe[lo] + (qe[lo + 1] - qe[lo]) * (fwi - qv[lo]) / d : qe[lo];
}

export function dcClimatologicoEco(zid, mes) {
  const z = CAL.zonas[zid];
  return z ? z.dc_clim[mes - 1] : null;
}

/** Nivel 0 (Bajo) … 4 (Extremo) de un FWI en escala ERA5 contra los cortes de la ecorregión. */
export function nivelEco(eco, fwiEq) {
  const c = CAL.ecorregiones[eco].cortes;
  let i = 0;
  while (i < c.length && fwiEq >= c[i]) i++;
  return i;
}

/**
 * Clasifica un día.
 * eq: Map|objeto zid → FWI equivalente ERA5 del punto (los puntos sin dato se omiten).
 * Devuelve { ecorregiones: {eco: {fwi_eq, nivel, puntos}}, provincias: {prov: {nivel, indice, peso_con_dato, ecorregiones: [{eco, peso, nivel, fwi_eq}]}} }.
 * indice = promedio ponderado de niveles sin redondear (0–4); peso_con_dato = fracción del fuego de la provincia en ecorregiones con dato.
 */
export function clasificarDia(eq) {
  const get = (k) => (eq instanceof Map ? eq.get(k) : eq[k]);
  const ecorregiones = {};
  for (const [eco, e] of Object.entries(CAL.ecorregiones)) {
    let num = 0, den = 0, n = 0;
    for (const zid of e.zonas) {
      const v = get(zid);
      if (v == null || !Number.isFinite(v)) continue;
      const w = CAL.zonas[zid].peso_eco;
      num += w * v; den += w; n++;
    }
    if (den > 0) { const f = num / den; ecorregiones[eco] = { fwi_eq: f, nivel: nivelEco(eco, f), puntos: n }; }
  }
  const provincias = {};
  for (const [prov, pesos] of Object.entries(CAL.provincias)) {
    let num = 0, den = 0; const det = [];
    for (const [eco, w] of Object.entries(pesos)) {
      const r = ecorregiones[eco];
      if (!r) continue;
      num += w * r.nivel; den += w;
      det.push({ eco, peso: w, nivel: r.nivel, fwi_eq: r.fwi_eq });
    }
    if (den > 0) provincias[prov] = { nivel: Math.floor(num / den + 0.5), indice: num / den, peso_con_dato: den, ecorregiones: det };
  }
  return { ecorregiones, provincias };
}

/** Ficha pública de una ecorregión (sin curvas de mapeo). */
export function fichaEco(eco) {
  const e = CAL.ecorregiones[eco];
  return e ? { clave: eco, nombre_es: e.nombre_es, nombre_en: e.nombre_en, cortes: e.cortes, cortes_origen: e.cortes_origen } : null;
}
