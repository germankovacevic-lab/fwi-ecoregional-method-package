// Zonas v4.1 — copia de tools/fwi_argentina/01_om_historico.mjs con las 90 zonas. Historia de la MISMA fuente que el vivo.
// El worker calcula el FWI con Open-Meteo /v1/forecast (past_days=92). La API
// "historical-forecast" de Open-Meteo sirve ese mismo archivo desde 2021-01-01
// (verificado 12/11/2026: 0 diferencias en 2.160 horas contra el pedido del vivo).
// Baja la serie horaria por zona y la reduce a la observación diaria del sistema FWI,
// con el MISMO recorte que worker/src/index.js: aire a las 12:00 locales + lluvia de
// las 24 h previas al mediodía. Salida: data/om_diario/om_<zid>.csv (date,temp,rh,wind,rain24)
// Uso: node 01_om_historico.mjs [hasta=YYYY-MM-DD]   (idempotente: saltea lo ya bajado)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const AQUI = path.dirname(fileURLToPath(import.meta.url));
const ZJ = JSON.parse(fs.readFileSync(path.join(AQUI, 'data/zonas_v4_split5_p50.json'), 'utf8')).zonas;
const ZONAS = Object.fromEntries(Object.values(ZJ).flat().map(z => [z.zid, z]));
const OUT = path.join(process.env.HOME, '.openclaw/data/gfi_v4_om_diario');
const DESDE = '2021-01-01', HASTA = process.argv[2] || new Date(Date.now() - 3 * 3600e3).toISOString().slice(0, 10);
fs.mkdirSync(OUT, { recursive: true });
const dormir = (ms) => new Promise(r => setTimeout(r, ms));
let n = 0;
for (const [id, z] of Object.entries(ZONAS)) {
  const f = path.join(OUT, 'om_' + id + '.csv');
  if (fs.existsSync(f)) { n++; continue; }
  const u = 'https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=' + z.lat + '&longitude=' + z.lon +
    '&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation&start_date=' + DESDE + '&end_date=' + HASTA +
    '&timezone=America%2FArgentina%2FBuenos_Aires';
  let h = null;
  for (let k = 0; k < 40 && !h; k++) {
    try {
      const r = await fetch(u, { signal: AbortSignal.timeout(90000) });
      if (r.status === 429) { console.log(id, '429, espero', 60 * (k + 1), 's'); await dormir(60000 * Math.min(k + 1, 10)); continue; }
      if (!r.ok) throw new Error('http ' + r.status);
      h = (await r.json()).hourly;
    } catch (e) { console.log(id, e.message); await dormir(15000); }
  }
  if (!h) { console.log(id, 'SIN DATO'); continue; }
  const filas = ['date,temp,rh,wind,rain24'];
  for (let i = 0; i < h.time.length; i++) {
    if (!h.time[i].endsWith('T12:00') || h.temperature_2m[i] == null) continue;
    let lluvia = 0;
    for (let k = Math.max(0, i - 23); k <= i; k++) lluvia += h.precipitation[k] || 0;
    filas.push([h.time[i].slice(0, 10), h.temperature_2m[i], h.relative_humidity_2m[i], h.wind_speed_10m[i], Math.round(lluvia * 100) / 100].join(','));
  }
  fs.writeFileSync(f, filas.join('\n') + '\n');
  n++; console.log(n, id, filas.length - 1, 'días');
  await dormir(2500);
}
console.log('listo', n, 'zonas');
