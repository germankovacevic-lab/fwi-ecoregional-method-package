// FWI ERA5 de las 90 zonas v4.1 con el MOTOR DEL WORKER (tabla DMC por latitud), igual que
// tools/fwi_argentina/02_historia_era5.mjs. Salida: ~/.openclaw/data/gfi_v4_fwi_worker/fwi_<zid>.csv
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fwiRun } from '../../worker/src/fwi.js';
const AQUI = path.dirname(fileURLToPath(import.meta.url));
const Z = JSON.parse(fs.readFileSync(path.join(AQUI, 'data/zonas_v4_split5_p50.json'), 'utf8')).zonas;
const METEO = path.join(os.homedir(), '.openclaw/data/gfi_v4_cds'), OUT = path.join(os.homedir(), '.openclaw/data/gfi_v4_fwi_worker');
fs.mkdirSync(OUT, { recursive: true });
const csv = (f) => { const [h, ...r] = fs.readFileSync(f, 'utf8').trim().split('\n'); const c = h.split(','); return r.map(l => Object.fromEntries(l.split(',').map((v, i) => [c[i], i ? +v : v]))); };
const r2 = (x) => Math.round(x * 100) / 100;
let n = 0;
for (const zz of Object.values(Z)) for (const z of zz) {
  const m = csv(path.join(METEO, 'meteo_' + z.zid + '.csv')).filter(d => Number.isFinite(d.temp) && Number.isFinite(d.rh) && Number.isFinite(d.wind));
  const s = fwiRun(m.map(d => ({ temp: d.temp, rh: d.rh, wind: d.wind, rain: Number.isFinite(d.rain24) ? d.rain24 : 0, month: +d.date.slice(5, 7), lat: z.lat })));
  const f = ['date,ffmc,dmc,dc,isi,bui,fwi'];
  m.forEach((d, i) => { if (d.date >= '2012-01-01') f.push([d.date, r2(s[i].ffmc), r2(s[i].dmc), r2(s[i].dc), r2(s[i].isi), r2(s[i].bui), r2(s[i].fwi)].join(',')); });
  fs.writeFileSync(path.join(OUT, 'fwi_' + z.zid + '.csv'), f.join('\n') + '\n'); n++;
}
console.log(n, 'zonas →', OUT);
