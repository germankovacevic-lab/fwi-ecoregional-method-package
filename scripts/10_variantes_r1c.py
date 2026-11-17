#!/usr/bin/env python3
"""Calibra R1(c) contra la estacionalidad: para variantes (meses mínimos, radio al pozo), cuántos focos limpios quedan
en cada zona de cuenca petrolera y si su concentración estacional se parece a vegetación o a antorcha.
También mide el costo: cuántos focos 'limpios' se pierden en zonas SIN petróleo (deberían ser ~0)."""
import json, os, sys, collections, numpy as np, pandas as pd
AQ = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['07', '--split5', '--piso=50']
src = open(f'{AQ}/07_zonas_v4.py').read()
g = {'__file__': f'{AQ}/07_zonas_v4.py', '__name__': 'x'}
exec(compile(src[:src.index('# ---------- R2/R3/R4 por provincia')], '07', 'exec'), g)
lat, lon, prov, df, hav, pn, xy, cel, nmes, fa, fb = (g[k] for k in ('lat', 'lon', 'prov', 'df', 'hav', 'pn', 'xy', 'cel', 'nmes', 'fa', 'fb'))
mes = df.acq_date.str[5:7].astype(int).values
# distancia de cada celda 0,02° con focos al pozo más cercano (km)
pk = collections.defaultdict(list)
for o, a in xy: pk[(int(np.floor(a / .02)), int(np.floor(o / .02)))].append((a, o))
cu, first = np.unique(cel, return_index=True)
dcel = {}
for c, i in zip(cu, first):
    ia, io = int(np.floor(lat[i] / .02)), int(np.floor(lon[i] / .02))
    near = [w for da in range(-3, 4) for do in range(-3, 4) for w in pk.get((ia + da, io + do), [])]
    dcel[c] = float(hav(lat[i], lon[i], np.array([w[0] for w in near]), np.array([w[1] for w in near])).min()) if near else 99.
dpozo = np.array([dcel[c] for c in cel])
nm = nmes.reindex(cel).values
D = json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas']
conc = lambda m: round(100 * np.sort(np.bincount(mes[m], minlength=13)[1:] / max(len(m), 1))[-4:].sum())
CASOS = [('Neuquén', '-38.45_-69.05'), ('Santa Cruz', '-50.67_-70.71'), ('Santa Cruz', '-46.55_-68.15'), ('Chubut', '-42.85_-70.35'),
         ('Tierra del Fuego, Antártida e Islas del Atlántico Sur', '-53.68_-67.90'), ('Mendoza', None)]
for meses, radio in [(6, 1), (4, 1), (3, 1), (3, 2), (2, 2), (2, 3), (1, 1), (1, 2)]:
    fc = (nm >= meses) & (dpozo <= radio)
    fija = fa | fb | fc
    row = []
    for P, zid in CASOS:
        i = pn.index(P); Z = D[P]; t = np.where(prov == i)[0]
        at = np.stack([hav(lat[t], lon[t], z['lat'], z['lon']) for z in Z]).argmin(0)
        if zid is None: mm = t  # provincia entera
        else: mm = t[at == [j for j, z in enumerate(Z) if z['zid'] == zid][0]]
        l = mm[~fija[mm]]
        row.append(f"{len(l):5d}/{conc(l)}%")
    # costo fuera de cuencas: focos limpios a > 10 km de cualquier pozo no deberían cambiar (siempre 0 por construcción);
    # costo cerca de pozos en regiones agrícolas (Pampa/Chaco tienen pocos pozos): focos sacados por (c) fuera de Patagonia/Cuyo
    norte = (lat > -32) & fc & ~(fa | fb)
    print(f"meses≥{meses} radio≤{radio} km | Nqn Monte {row[0]} · SC sur {row[1]} · SC GSJ {row[2]} · Chubut est {row[3]} · TDF estepa {row[4]} · Mendoza total {row[5]} | (c) al norte de 32°S: {norte.sum()}")
print('referencia: antorchas ≈ 41–50 % en 4 meses pico; vegetación patagónica ≥ 60 %')
