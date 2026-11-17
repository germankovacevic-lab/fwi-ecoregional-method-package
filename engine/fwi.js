// Canadian Fire Weather Index (FWI) System — Van Wagner & Pickett 1985 (CFFDRS).
// Nació como copia de copernicus/functions/lib/fwi.js. Desde el 12/11/2026 difiere en un
// punto, a propósito: el factor de largo del día del DMC se elige POR LATITUD, igual que el
// paquete oficial cffdrs (github.com/cffdrs/cffdrs_r, función dmc), cuando la observación
// trae `lat`. Sin `lat` se comporta como antes (tabla canadiense, corrida 6 meses en el sur).
// Ecuaciones idénticas a cffdrs, validado contra su test de regresión fwi_01 (dataset
// test_fwi, 48 días). ESM puro, sin dependencias: corre en node y en Cloudflare Workers.

// Factores de largo del día del DMC (Le) por mes — tablas de cffdrs (Lawson & Armitage 2008)
const DMC_DAYLENGTH_N = [6.5, 7.5, 9.0, 12.8, 13.9, 13.9, 12.4, 10.9, 9.4, 8.0, 7.0, 6.0];      // ell01: lat > 30°N
const DMC_DAYLENGTH_N20 = [7.9, 8.4, 8.9, 9.5, 9.9, 10.2, 10.1, 9.7, 9.1, 8.6, 8.1, 7.8];       // ell02: 10°N < lat ≤ 30°N
const DMC_DAYLENGTH_S20 = [10.1, 9.6, 9.1, 8.5, 8.1, 7.8, 7.9, 8.3, 8.9, 9.4, 9.9, 10.2];       // ell03: 30°S < lat ≤ 10°S
const DMC_DAYLENGTH_S40 = [11.5, 10.5, 9.2, 7.9, 6.8, 6.2, 6.5, 7.4, 8.7, 10.0, 11.2, 11.8];    // ell04: lat ≤ 30°S
// Legado (solo cuando la observación NO trae latitud): tabla canadiense corrida 6 meses.
// No es una tabla de cffdrs; sobreestima el DMC austral de primavera-verano (13,9 en noviembre
// contra 11,2 de ell04 y 9,9 de ell03).
const DMC_DAYLENGTH_S = [12.4, 10.9, 9.4, 8.0, 7.0, 6.0, 6.5, 7.5, 9.0, 12.8, 13.9, 13.9];

// Tabla del DMC para una latitud, con los mismos cortes que cffdrs.
function dmcDaylength(lat, monthIdx) {
  if (lat > 30) return DMC_DAYLENGTH_N[monthIdx];
  if (lat > 10) return DMC_DAYLENGTH_N20[monthIdx];
  if (lat > -10) return 9;
  if (lat > -30) return DMC_DAYLENGTH_S20[monthIdx];
  return DMC_DAYLENGTH_S40[monthIdx];
}

// Day-length factors del DC (Lf) por mes, hemisferio norte (lat > 20N)
const DC_DAYLENGTH_N = [-1.6, -1.6, -1.6, 0.9, 3.8, 5.8, 6.4, 5.0, 2.4, 0.4, -1.6, -1.6];
// Hemisferio sur = mismo corrimiento de 6 meses (tabla fl02 de cffdrs, lat < -20)
const DC_DAYLENGTH_S = [6.4, 5.0, 2.4, 0.4, -1.6, -1.6, -1.6, -1.6, -1.6, 0.9, 3.8, 5.8];

// Constante de conversión FFMC↔humedad: 250·59.5/101 ≈ 147.27723 (cffdrs usa el valor
// exacto, no el 147.2 redondeado de VW&P 1985 — con 147.2 el FFMC da ~+0.06 de offset)
const FFMC_COEFFICIENT = (250.0 * 59.5) / 101.0;

// Fine Fuel Moisture Code
function ffmcCalc(ffmcPrev, temp, rh, wind, rain) {
  // contenido de humedad del día anterior
  let wmo = (FFMC_COEFFICIENT * (101 - ffmcPrev)) / (59.5 + ffmcPrev);
  if (rain > 0.5) {
    const ra = rain - 0.5; // solo la lluvia que atraviesa el dosel
    if (wmo > 150) {
      wmo +=
        0.0015 * (wmo - 150) * (wmo - 150) * Math.sqrt(ra) +
        42.5 * ra * Math.exp(-100 / (251 - wmo)) * (1 - Math.exp(-6.93 / ra));
    } else {
      wmo += 42.5 * ra * Math.exp(-100 / (251 - wmo)) * (1 - Math.exp(-6.93 / ra));
    }
    if (wmo > 250) wmo = 250;
  }
  const ed =
    0.942 * Math.pow(rh, 0.679) +
    11 * Math.exp((rh - 100) / 10) +
    0.18 * (21.1 - temp) * (1 - Math.exp(-0.115 * rh));
  const ew =
    0.618 * Math.pow(rh, 0.753) +
    10 * Math.exp((rh - 100) / 10) +
    0.18 * (21.1 - temp) * (1 - Math.exp(-0.115 * rh));
  let wm;
  if (wmo < ed && wmo < ew) {
    const z =
      0.424 * (1 - Math.pow((100 - rh) / 100, 1.7)) +
      0.0694 * Math.sqrt(wind) * (1 - Math.pow((100 - rh) / 100, 8));
    const x = z * 0.581 * Math.exp(0.0365 * temp);
    wm = ew - (ew - wmo) / Math.pow(10, x);
  } else if (wmo > ed) {
    const z =
      0.424 * (1 - Math.pow(rh / 100, 1.7)) +
      0.0694 * Math.sqrt(wind) * (1 - Math.pow(rh / 100, 8));
    const x = z * 0.581 * Math.exp(0.0365 * temp);
    wm = ed + (wmo - ed) / Math.pow(10, x);
  } else {
    wm = wmo;
  }
  let ffmc = (59.5 * (250 - wm)) / (FFMC_COEFFICIENT + wm);
  if (ffmc > 101) ffmc = 101;
  if (ffmc < 0) ffmc = 0;
  return ffmc;
}

// Duff Moisture Code
function dmcCalc(dmcPrev, temp, rh, rain, ell) {
  const t = Math.max(temp, -1.1);
  const rk = 1.894 * (t + 1.1) * (100 - rh) * ell * 1e-4;
  let pr;
  if (rain > 1.5) {
    const rw = 0.92 * rain - 1.27; // lluvia efectiva
    const wmi = 20 + 280 / Math.exp(0.023 * dmcPrev);
    let b;
    if (dmcPrev <= 33) b = 100 / (0.5 + 0.3 * dmcPrev);
    else if (dmcPrev <= 65) b = 14 - 1.3 * Math.log(dmcPrev);
    else b = 6.2 * Math.log(dmcPrev) - 17.2;
    const wmr = wmi + (1000 * rw) / (48.77 + b * rw);
    pr = 43.43 * (5.6348 - Math.log(wmr - 20));
  } else {
    pr = dmcPrev;
  }
  if (pr < 0) pr = 0;
  return pr + rk;
}

// Drought Code
function dcCalc(dcPrev, temp, rain, monthIdx, south) {
  const fl = (south ? DC_DAYLENGTH_S : DC_DAYLENGTH_N)[monthIdx];
  let dr = dcPrev;
  if (rain > 2.8) {
    const rw = 0.83 * rain - 1.27;
    const smi = 800 * Math.exp(-dcPrev / 400);
    dr = dcPrev - 400 * Math.log(1 + (3.937 * rw) / smi);
    if (dr < 0) dr = 0;
  }
  let pe = (0.36 * (Math.max(temp, -2.8) + 2.8) + fl) / 2;
  if (pe < 0) pe = 0; // en invierno el factor negativo puede dar evapotranspiración negativa
  const dc = dr + pe;
  return dc < 0 ? 0 : dc;
}

// Initial Spread Index
function isiCalc(ffmc, wind) {
  const fm = (FFMC_COEFFICIENT * (101 - ffmc)) / (59.5 + ffmc);
  const fw = Math.exp(0.05039 * wind);
  const ff = 91.9 * Math.exp(-0.1386 * fm) * (1 + Math.pow(fm, 5.31) / 4.93e7);
  return 0.208 * fw * ff;
}

// Buildup Index
function buiCalc(dmc, dc) {
  let bui = dmc === 0 && dc === 0 ? 0 : (0.8 * dc * dmc) / (dmc + 0.4 * dc);
  if (bui < dmc) {
    const p = dmc === 0 ? 0 : (dmc - bui) / dmc;
    const cc = 0.92 + Math.pow(0.0114 * dmc, 1.7);
    bui = dmc - cc * p;
    if (bui < 0) bui = 0;
  }
  return bui;
}

// Fire Weather Index
function fwiCalc(isi, bui) {
  const bb =
    bui > 80
      ? 0.1 * isi * (1000 / (25 + 108.64 / Math.exp(0.023 * bui)))
      : 0.1 * isi * (0.626 * Math.pow(bui, 0.809) + 2);
  return bb <= 1 ? bb : Math.exp(2.72 * Math.pow(0.434 * Math.log(bb), 0.647));
}

/**
 * Un paso diario del sistema FWI.
 * @param {{ffmc:number, dmc:number, dc:number}} prev — estado del día anterior
 * @param {{temp:number, rh:number, wind:number, rain:number, month:number, lat?:number, hemisphere?:'N'|'S'}} obs
 *   temp °C (mediodía), rh % (0-100), wind km/h, rain mm acumulados 24h, month 1-12.
 *   lat (opcional, grados): si viene, el factor de largo del día del DMC sale de las tablas
 *   de cffdrs para esa latitud. Sin lat: tabla canadiense según hemisphere ('S' default,
 *   corrida 6 meses; 'N' canónica) — comportamiento previo, se conserva por compatibilidad.
 * @returns {{ffmc:number, dmc:number, dc:number, isi:number, bui:number, fwi:number}}
 */
export function fwiStep(prev, obs) {
  const south = (obs.hemisphere ?? 'S') !== 'N';
  const m = obs.month - 1;
  const rh = Math.min(obs.rh, 99.9999); // rh=100 exacto degenera las ecuaciones de equilibrio
  const ffmc = ffmcCalc(prev.ffmc, obs.temp, rh, obs.wind, obs.rain);
  const ell = Number.isFinite(obs.lat) ? dmcDaylength(obs.lat, m)
    : (south ? DMC_DAYLENGTH_S : DMC_DAYLENGTH_N)[m];
  const dmc = dmcCalc(prev.dmc, obs.temp, rh, obs.rain, ell);
  const dc = dcCalc(prev.dc, obs.temp, obs.rain, m, south);
  const isi = isiCalc(ffmc, obs.wind);
  const bui = buiCalc(dmc, dc);
  const fwi = fwiCalc(isi, bui);
  return { ffmc, dmc, dc, isi, bui, fwi };
}

/**
 * Corre la secuencia completa de días desde un estado inicial.
 * @param {Array<object>} days — observaciones (formato de obs en fwiStep)
 * @param {{ffmc?:number, dmc?:number, dc?:number}} [init] — default estándar CFFDRS: 85 / 6 / 15
 * @returns {Array<{ffmc,dmc,dc,isi,bui,fwi}>} un resultado por día
 */
export function fwiRun(days, init = {}) {
  let state = { ffmc: init.ffmc ?? 85, dmc: init.dmc ?? 6, dc: init.dc ?? 15 };
  const out = [];
  for (const day of days) {
    const r = fwiStep(state, day);
    out.push(r);
    state = { ffmc: r.ffmc, dmc: r.dmc, dc: r.dc };
  }
  return out;
}
