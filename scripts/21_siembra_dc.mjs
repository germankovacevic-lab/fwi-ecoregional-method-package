// ¿Cuánto cambia el Semáforo ecorregional si el DC se siembra con la climatología (semc) en vez del ERA5 real (sem)?
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path';
import { CALIBRACION_ECO as CAL, equivalenteEra5Eco, clasificarDia } from '../../worker/src/fwi_ecorregional.js';
const dir = path.join(os.homedir(), '.openclaw/data/gfi_v4_vivo');
const S = new Map(), C = new Map(); // fecha → {zid: eq}
for (const zid of Object.keys(CAL.zonas)) {
  const f = path.join(dir, 'vivo_' + zid + '.csv'); if (!fs.existsSync(f)) { console.log('falta', zid); continue; }
  const L = fs.readFileSync(f, 'utf8').trim().split('\n').slice(1);
  for (const l of L) { const [d, , , sem, semc] = l.split(','); if (sem === '' || d < '2022-01-01') continue;
    (S.get(d) || S.set(d, {}).get(d))[zid] = equivalenteEra5Eco(zid, +sem);
    (C.get(d) || C.set(d, {}).get(d))[zid] = equivalenteEra5Eco(zid, +semc); }
}
const eco = {}, prov = { n: 0, dif: 0, alto_s: 0, alto_c: 0, sube: 0, baja: 0 }; let ecoT = { n: 0, dif: 0, d2: 0 };
for (const [d, s] of S) { const a = clasificarDia(s), b = clasificarDia(C.get(d));
  for (const k in a.ecorregiones) { const x = a.ecorregiones[k], y = b.ecorregiones[k]; if (!y) continue;
    const e = eco[k] || (eco[k] = { n: 0, dif: 0, d2: 0, sube: 0, baja: 0, abs: 0 });
    e.n++; ecoT.n++; const dn = y.nivel - x.nivel; if (dn) { e.dif++; ecoT.dif++; } if (Math.abs(dn) >= 2) { e.d2++; ecoT.d2++; } if (dn > 0) e.sube++; if (dn < 0) e.baja++; e.abs += Math.abs(y.fwi_eq - x.fwi_eq); }
  for (const k in a.provincias) { const x = a.provincias[k].nivel, y = b.provincias[k]?.nivel; if (y == null) continue;
    prov.n++; if (x !== y) prov.dif++; if (y > x) prov.sube++; if (y < x) prov.baja++; if (x >= 2) prov.alto_s++; if (y >= 2) prov.alto_c++; } }
const p = (a, b) => (100 * a / b).toFixed(1) + ' %';
console.log('días', S.size, '· ecorregión-días', ecoT.n, '· clase distinta', p(ecoT.dif, ecoT.n), '· ≥2 clases', p(ecoT.d2, ecoT.n));
for (const [k, e] of Object.entries(eco).sort((a, b) => b[1].dif / b[1].n - a[1].dif / a[1].n))
  console.log(k.padEnd(30), 'distinta', p(e.dif, e.n).padStart(7), ' sube', p(e.sube, e.n).padStart(7), ' baja', p(e.baja, e.n).padStart(7), ' |ΔFWIeq| medio', (e.abs / e.n).toFixed(2));
console.log('provincia-días', prov.n, '· clase distinta', p(prov.dif, prov.n), '(sube', p(prov.sube, prov.n), '· baja', p(prov.baja, prov.n) + ')', '· ≥Alto con ERA5', p(prov.alto_s, prov.n), '· con climatología', p(prov.alto_c, prov.n));
