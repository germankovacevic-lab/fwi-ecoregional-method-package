// Zonas v4.1 — copia de tools/fwi_argentina/03_vivo_emulado.mjs con las 90 zonas. Emula el cálculo EN VIVO del worker sobre el período de solape con ERA5.
// Para cada zona y cada día D: corre el motor sobre la ventana D−92…D de Open-Meteo (lo que
// pide el worker con past_days=92) y guarda el FWI de D. Tres variantes:
//   prod  = lo que estaba en producción: tabla del DMC legado, arranque 85/6/15
//   lat   = tabla del DMC por latitud, arranque 85/6/15
//   sem   = tabla por latitud + arranque sembrado: DC = DC ERA5 del día D−93 (lo que el worker
//           lee de la tabla D1 gfi_dc_era5), FFMC/DMC estándar (se equilibran en días/semanas)
//   semc  = como sem pero con el DC climatológico ERA5 del mes (respaldo si falta el DC en D1)
// Salida: data/vivo/vivo_<zid>.csv (date,prod,lat,sem,semc,dc_prod,dc_sem)
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fwiRun } from '../../worker/src/fwi.js';
const AQUI = path.dirname(fileURLToPath(import.meta.url));
const ZJ = JSON.parse(fs.readFileSync(path.join(AQUI, 'data/zonas_v4_split5_p50.json'), 'utf8')).zonas;
const ZONAS = Object.fromEntries(Object.values(ZJ).flat().map(z => [z.zid, z]));
const OUT = path.join(os.homedir(), '.openclaw/data/gfi_v4_vivo'); fs.mkdirSync(OUT, { recursive: true });
const csv = (f) => { const [h, ...r] = fs.readFileSync(f, 'utf8').trim().split('\n'); const c = h.split(','); return r.map(l => Object.fromEntries(l.split(',').map((v, i) => [c[i], i ? +v : v]))); };
const r2 = (x) => Math.round(x * 100) / 100, W = 92;
const menos = (iso, n) => new Date(Date.parse(iso) - n * 86400e3).toISOString().slice(0, 10);
let hechas = 0;
for (const [id, z] of Object.entries(ZONAS)) {
  if (process.env.ZONAS && !process.env.ZONAS.split(',').includes(id)) continue; // solo estas zonas (p. ej. tools/tdf_4zonas)
  const fo = path.join(os.homedir(), '.openclaw/data/gfi_v4_om_diario/om_' + id + '.csv'); if (!fs.existsSync(fo)) continue;
  const om = csv(fo), e5 = csv(path.join(os.homedir(), '.openclaw/data/gfi_v4_fwi_worker/fwi_' + id + '.csv'));
  const dcE = new Map(e5.map(d => [d.date, d.dc]));
  // DC climatológico por mes (mediana ERA5 2012–2025) — el respaldo
  const porMes = Array.from({ length: 12 }, () => []); for (const d of e5) if (d.date < '2026') porMes[+d.date.slice(5, 7) - 1].push(d.dc);
  const clim = porMes.map(a => { a.sort((x, y) => x - y); return a[a.length >> 1]; });
  const obs = (d, conLat) => ({ temp: d.temp, rh: d.rh, wind: d.wind, rain: d.rain24, month: +d.date.slice(5, 7), ...(conLat ? { lat: z.lat } : {}) });
  const oL = om.map(d => obs(d, true)), oP = om.map(d => obs(d, false));
  const filas = ['date,prod,lat,sem,semc,dc_prod,dc_sem'];
  for (let i = W; i < om.length; i++) {
    const D = om[i].date, d0 = om[i - W].date, ayer = menos(d0, 1);
    const p = fwiRun(oP.slice(i - W, i + 1)).at(-1), l = fwiRun(oL.slice(i - W, i + 1)).at(-1);
    const dc0 = dcE.get(ayer);
    const s = dc0 == null ? null : fwiRun(oL.slice(i - W, i + 1), { dc: dc0 }).at(-1);
    const c = fwiRun(oL.slice(i - W, i + 1), { dc: clim[+ayer.slice(5, 7) - 1] }).at(-1);
    filas.push([D, r2(p.fwi), r2(l.fwi), s ? r2(s.fwi) : '', r2(c.fwi), r2(p.dc), s ? r2(s.dc) : ''].join(','));
  }
  fs.writeFileSync(path.join(OUT, 'vivo_' + id + '.csv'), filas.join('\n') + '\n'); hechas++;
}
console.log('zonas emuladas:', hechas);
