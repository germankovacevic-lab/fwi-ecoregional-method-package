// Paridad JS (worker/src/fwi_ecorregional.js) ↔ Python (test_fwi_ecorregional_ref.py). Uso: node test_fwi_ecorregional.mjs
import fs from 'node:fs';
import { CALIBRACION_ECO, equivalenteEra5Eco, clasificarDia } from '../../worker/src/fwi_ecorregional.js';
const P = JSON.parse(fs.readFileSync(new URL('./data/paridad_fwi_ecorregional.json', import.meta.url)));
if (P.sha256 !== CALIBRACION_ECO.sha256) { console.error('FALLA: fixture de otra calibración'); process.exit(1); }
let difEq = 0, difNivEco = 0, difNivProv = 0, nE = 0, nP = 0;
for (const c of P.casos) {
  const eq = {}; for (const [z, x] of Object.entries(c.fwi)) eq[z] = equivalenteEra5Eco(z, x);
  const r = clasificarDia(eq);
  for (const [e, o] of Object.entries(c.ecorregiones)) {
    nE++; const j = r.ecorregiones[e];
    if (!j) { difNivEco++; continue; }
    difEq = Math.max(difEq, Math.abs(j.fwi_eq - o.fwi_eq)); if (j.nivel !== o.nivel) difNivEco++;
  }
  if (Object.keys(r.ecorregiones).length !== Object.keys(c.ecorregiones).length) difNivEco++;
  for (const [p, n] of Object.entries(c.provincias)) { nP++; if (!r.provincias[p] || r.provincias[p].nivel !== n) difNivProv++; }
}
console.log(`casos ${P.casos.length} · ecorregión-días ${nE} · provincia-días ${nP} · máx |ΔFWI eq| ${difEq.toExponential(2)} · niveles distintos: eco ${difNivEco}, prov ${difNivProv}`);
if (difEq > 1e-6 || difNivEco || difNivProv) { console.error('FALLA'); process.exit(1); }
console.log('OK');
