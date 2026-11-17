#!/usr/bin/env python3
"""Control R7.2 en zonas con muchas fuentes fijas: ¿los focos que quedan como 'limpios' tienen estacionalidad de
vegetación (concentrados en la temporada) o son antorchas que el filtro no detectó (parejas todo el año, ~33 %)?"""
import json, os, sys, numpy as np
AQ = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['07', '--split5', '--piso=50']
src = open(f'{AQ}/07_zonas_v4.py').read()
g = {'__file__': f'{AQ}/07_zonas_v4.py', '__name__': 'x'}
exec(compile(src[:src.index('# ---------- R2/R3/R4 por provincia')], '07', 'exec'), g)
lat, lon, fija, prov, df, hav, pn = g['lat'], g['lon'], g['fija'], g['prov'], g['df'], g['hav'], g['pn']
mes = df.acq_date.str[5:7].astype(int).values
D = json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas']
conc = lambda m: round(100 * np.sort(np.bincount(mes[m], minlength=13)[1:] / max(len(m), 1))[-4:].sum())
out = {}
for P, Z in D.items():
    if P.startswith('Ciudad'): continue
    i = pn.index(P); t = np.where(prov == i)[0]
    at = np.stack([hav(lat[t], lon[t], z['lat'], z['lon']) for z in Z]).argmin(0)
    for k, z in enumerate(Z):
        mm = t[at == k]; l = mm[~fija[mm]]; f = mm[fija[mm]]
        if z.get('fijas_pct', 0) >= 15:
            out[z['zid']] = dict(prov=P, limpios=int(len(l)), conc_limpios=conc(l), fijos=int(len(f)), conc_fijos=conc(f))
            print(f"{P[:14]:14s} {z['zid']}: limpios {len(l):5d} → 4 meses pico {conc(l)} % · fijos {len(f):5d} → {conc(f)} %")
json.dump(out, open(f'{AQ}/data/control_fijas_v4.json', 'w'), ensure_ascii=False, indent=1)
print('referencia: parejo todo el año = 33 %')
