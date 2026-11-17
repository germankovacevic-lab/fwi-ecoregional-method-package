// Payload público del Semáforo FWI (/api/fwi en el worker y su espejo /api/flama/fwi en Pages).
// Función pura (sin red ni D1) para poder probarla con casos fijos (tools/fwi_snmf/test_payload.mjs).
//
// Versión 4 (17/11/2026): el Semáforo se calcula POR ECORREGIÓN (worker/src/fwi_ecorregional.js).
//   ecorregiones[]  la unidad del cálculo: FWI equivalente ERA5 (promedio de sus puntos ponderado por fuego
//                   histórico) y clase con cortes propios, hoy y a +24/+48/+72 h.
//   puntos[]        una entrada por provincia, que ahora es un RESUMEN: clase = promedio de las clases de sus
//                   ecorregiones ponderado por dónde está su fuego (`hoy.ecorregiones[]` trae el detalle).
//                   Ya no existe la "peor zona". `zonas[]` = los puntos de cálculo de la provincia con su FWI
//                   vivo y su equivalente ERA5; los puntos no tienen clase propia (la clase es de la ecorregión).
// Compatibilidad con v3: puntos[].hoy / pronostico[] conservan `fecha`, `fwi`, `fwi_eq` y `clase`. En v4 el
// `fwi` provincial es el promedio de los FWI equivalentes de sus ecorregiones con los mismos pesos (escala ERA5).
import { CLASES, clase, FUENTES } from './clases_snmf.js';
import { CALIBRACION_ECO as CAL, clasificarDia, fichaEco } from './fwi_ecorregional.js';

const r1 = (x) => Math.round(x * 10) / 10;
const r2 = (x) => Math.round(x * 100) / 100;
// fracción mínima del fuego histórico de una provincia que debe estar en ecorregiones con dato para publicar su resumen
export const PESO_MIN_PROVINCIA = 0.5;

// zonas: [[id, {lat, lon, provincia, ecorregion, peso_eco}]]  (CALIBRACION_ECO.zonas)
// res:   Map(id → {hoy, pronostico[], arrastre}); hoy/pronostico[k] = {fecha, fwi, fwi_eq, ffmc, dmc, dc, isi, bui, temp, rh, wind, rain}
export function armarPayloadFwi(zonas, res, ahoraISO = new Date().toISOString()) {
  // días publicados: el "hoy" más frecuente entre los puntos y los 3 siguientes
  const cuenta = new Map();
  for (const r of res.values()) cuenta.set(r.hoy.fecha, (cuenta.get(r.hoy.fecha) || 0) + 1);
  const hoyF = [...cuenta].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? 1 : -1))[0]?.[0];
  const dias = hoyF ? [0, 1, 2, 3].map(n => new Date(Date.parse(hoyF) + n * 86400e3).toISOString().slice(0, 10)) : [];
  const delDia = (r, f) => (r.hoy.fecha === f ? r.hoy : r.pronostico.find(d => d.fecha === f)) || null;

  // clasificación de cada día: ecorregiones y provincias
  const K = dias.map(f => {
    const eq = new Map();
    for (const [id] of zonas) { const r = res.get(id), d = r && delDia(r, f); if (d) eq.set(id, d.fwi_eq); }
    return clasificarDia(eq);
  });

  const nomEco = (eco) => { const e = CAL.ecorregiones[eco]; return { clave: eco, nombre_es: e.nombre_es, nombre_en: e.nombre_en }; };
  const diaEco = (k, eco) => { const x = K[k].ecorregiones[eco];
    return x ? { fecha: dias[k], fwi_eq: r1(x.fwi_eq), clase: clase(x.nivel), puntos: x.puntos } : null; };
  const ecorregiones = [];
  for (const eco of Object.keys(CAL.ecorregiones)) {
    const hoy = dias.length ? diaEco(0, eco) : null;
    if (!hoy) continue;
    ecorregiones.push({ ...fichaEco(eco), puntos_total: CAL.ecorregiones[eco].zonas.length,
      provincias: Object.entries(CAL.provincias).filter(([, w]) => (w[eco] || 0) >= 0.01).map(([p]) => p),
      hoy, pronostico: [1, 2, 3].map(k => diaEco(k, eco)).filter(Boolean) });
  }
  ecorregiones.sort((a, b) => a.nombre_es.localeCompare(b.nombre_es));

  const porProv = new Map(), totalZonas = new Map();
  for (const [id, z] of zonas) {
    totalZonas.set(z.provincia, (totalZonas.get(z.provincia) || 0) + 1);
    const r = res.get(id);
    if (r) (porProv.get(z.provincia) || porProv.set(z.provincia, []).get(z.provincia)).push({ id, z, r });
  }
  // meteo de la provincia: promedio de sus puntos ponderado por fuego histórico (la lluvia también: es un resumen)
  const meteoProv = (zs, f) => {
    const acc = { temp: 0, rh: 0, wind: 0, rain: 0 }; let den = 0;
    for (const { z, r } of zs) { const d = delDia(r, f); if (!d) continue; const w = z.peso_eco || 1;
      for (const k in acc) acc[k] += w * d[k]; den += w; }
    return den ? { temp: r1(acc.temp / den), rh: Math.round(acc.rh / den), wind: r1(acc.wind / den), rain: r1(acc.rain / den) } : {};
  };
  const diaProv = (k, prov, zs, completa) => {
    const x = K[k].provincias[prov];
    if (!x || x.peso_con_dato < PESO_MIN_PROVINCIA) return null;
    let num = 0, den = 0;
    for (const e of x.ecorregiones) { num += e.peso * e.fwi_eq; den += e.peso; }
    const f = r1(num / den);
    return { fecha: dias[k], fwi: f, fwi_eq: f, indice: r2(x.indice), clase: clase(x.nivel, completa), ...meteoProv(zs, dias[k]),
      ecorregiones: x.ecorregiones.slice().sort((a, b) => b.peso - a.peso)
        .map(e => ({ ...nomEco(e.eco), peso: e.peso, fwi_eq: r1(e.fwi_eq), clase: clase(e.nivel) })) };
  };

  const puntos = [];
  for (const [prov, zs] of porProv) {
    const hoy = dias.length ? diaProv(0, prov, zs, true) : null;
    if (!hoy) continue;
    const ref = zs.reduce((a, b) => ((b.z.peso_eco || 0) > (a.z.peso_eco || 0) ? b : a));   // punto de más fuego: ubica la provincia en el mapa
    puntos.push({
      provincia: prov, lat: ref.z.lat, lon: ref.z.lon,
      hoy, pronostico: [1, 2, 3].map(k => diaProv(k, prov, zs, false)).filter(Boolean),
      zonas_con_dato: zs.length, zonas_total: totalZonas.get(prov),
      zonas: zs.map(({ id, z, r }) => ({ id, lat: z.lat, lon: z.lon, peso: z.peso_eco, ecorregion: nomEco(z.ecorregion),
        fecha: r.hoy.fecha, fwi: r1(r.hoy.fwi), fwi_eq: r1(r.hoy.fwi_eq),
        ffmc: r.hoy.ffmc, dmc: r.hoy.dmc, dc: r.hoy.dc, isi: r.hoy.isi, bui: r.hoy.bui,
        temp: r.hoy.temp, rh: r.hoy.rh, wind: r.hoy.wind, rain: r.hoy.rain,
        pronostico: r.pronostico.map(d => ({ fecha: d.fecha, fwi: r1(d.fwi), fwi_eq: r1(d.fwi_eq), temp: d.temp, rh: d.rh, wind: d.wind, rain: d.rain })),
        arrastre: r.arrastre })),
    });
  }
  puntos.sort((a, b) => a.provincia.localeCompare(b.provincia));
  const fallidas = Object.keys(CAL.provincias).filter(p => !puntos.some(q => q.provincia === p)).sort();
  // provincia más comprometida: mayor clase; a igual clase, mayor índice (promedio de niveles sin redondear) y después mayor FWI
  const orden = (a, b) => (b.hoy.clase.nivel - a.hoy.clase.nivel) || (b.hoy.indice - a.hoy.indice) || (b.hoy.fwi_eq - a.hoy.fwi_eq);
  const alta = puntos.slice().sort(orden)[0];
  const porClase = (arr) => { const o = {}; for (const c of CLASES) o[c.key] = arr.filter(p => p.hoy.clase.key === c.key).length; return o; };
  const ecos = {};
  for (const eco of Object.keys(CAL.ecorregiones)) ecos[eco] = { ...fichaEco(eco), dias_fuertes_2012_2025: CAL.ecorregiones[eco].dias_fuertes_2012_2025, puntos: CAL.ecorregiones[eco].zonas.length };
  return {
    version: 4,
    actualizado: ahoraISO,
    metodo: 'FWI canadiense (Van Wagner 1987) calculado por ecorregión, sobre el mapa oficial de Ecorregiones de la Argentina (Ministerio de Ambiente, 2021). En cada uno de los 89 puntos de fuego histórico se calcula el FWI con la meteorología de Open-Meteo a las 12:00 locales y se lo lleva a escala ERA5. El FWI de cada ecorregión es el promedio de sus puntos, ponderado por el fuego histórico de cada uno. La clase (Bajo, Moderado, Alto, Muy alto, Extremo: las cinco del Servicio Nacional de Manejo del Fuego) sale de umbrales propios de cada ecorregión: cada clase arranca en el FWI en que ocurrió su fuego fuerte (percentiles 10/25/50/75 de los días de fuego fuerte, ERA5 2012–2025). La clase de cada provincia es un resumen: el promedio de las clases de sus ecorregiones, ponderado por dónde ocurre su fuego; el mapa muestra además la clase de cada ecorregión. Pronóstico a 24, 48 y 72 h con el mismo cálculo sobre la meteorología prevista. Los umbrales son una estimación de GEOFUEGO; los oficiales no son públicos. El índice es solo meteorológico: no considera carga de combustible, topografía ni el secado de pastizales vivos. El mapa oficial de peligro es el del SNMF y el Servicio Meteorológico Nacional.',
    metodo_en: 'Canadian FWI (Van Wagner 1987) computed by ecoregion, on the official map of Argentina\'s ecoregions (Ministry of Environment, 2021). At each of the 89 historical fire points the FWI is computed from Open-Meteo weather at 12:00 local time and mapped to the ERA5 scale. Each ecoregion\'s FWI is the average of its points, weighted by each point\'s historical fire. The class (Low, Moderate, High, Very high, Extreme: the five used by Argentina\'s National Fire Management Service, SNMF) comes from thresholds specific to each ecoregion: each class starts at the FWI at which its strong fires occurred (10th/25th/50th/75th percentiles of strong-fire days, ERA5 2012–2025). Each province\'s class is a summary: the average of the classes of its ecoregions, weighted by where its fire occurs; the map also shows the class of each ecoregion. 24, 48 and 72 h outlook with the same computation on forecast weather. Thresholds are GEOFUEGO\'s own estimate; the official ones are not public. The index is weather-only: it does not account for fuel load, topography or the curing of live grasslands. The official danger map is published by SNMF and the National Weather Service (SMN).',
    escala: {
      nombre_es: 'Clases de peligro del SNMF, umbrales por ecorregión', nombre_en: 'SNMF fire-danger classes, thresholds by ecoregion',
      version: CAL.version, generado: CAL.generado, sha256: CAL.sha256,
      clases: CLASES.map((c, i) => clase(i, true)),
      criterio_es: CAL.criterio, criterio_en: CAL.criterio_en, escala: CAL.escala,
      ecorregiones: ecos, verificacion: CAL.verificacion,
      fuentes: { ...FUENTES, ecorregiones: { nombre: 'Ecorregiones de la Argentina — Ministerio de Ambiente y Desarrollo Sostenible (2021), sobre Burkart et al. (1999)', url: 'https://geo.ambiente.gob.ar/' } },
    },
    dias,
    peor: alta ? { provincia: alta.provincia, fwi: alta.hoy.fwi, fwi_eq: alta.hoy.fwi_eq, indice: alta.hoy.indice, clase: clase(alta.hoy.clase.nivel - 1) } : null,
    provincias_por_clase: porClase(puntos),
    ecorregiones_por_clase: porClase(ecorregiones),
    fallidas,
    ecorregiones,
    puntos,
  };
}
