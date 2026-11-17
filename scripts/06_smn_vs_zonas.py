#!/usr/bin/env python3
"""¿Cuánto coinciden las zonas de GeoFuego con los puntos del mapa SMN/SNMF? Mide cobertura del fuego real."""
import json, os, numpy as np
H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
F = np.load(f'{AQ}/data/focos.npz'); lat, lon, prov, eco, fija = F['lat'].astype(float), F['lon'].astype(float), F['prov'], F['eco'], F['fija']
pn, en = list(F['pnames']), list(F['enames'])
S = json.load(open(H('~/.openclaw/data/smn/mapa_2026-11-16/estaciones_fwi_smn.json')))['estaciones']
CAL = json.load(open(f'{AQ}/../../worker/src/calibracion_3.0_argentina.json'))['zonas']
Z = [(P, z['lat'], z['lon'], z['peso']) for P, zz in CAL.items() for z in zz]
sl, so = np.array([s['lat'] for s in S]), np.array([s['lon'] for s in S])
zl, zo = np.array([z[1] for z in Z]), np.array([z[2] for z in Z])
def dmin(la, lo, A, O, chunk=200000):
    out = np.empty(len(la))
    for i in range(0, len(la), chunk):
        a, o = np.radians(la[i:i+chunk])[:, None], np.radians(lo[i:i+chunk])[:, None]
        b, p = np.radians(A)[None], np.radians(O)[None]
        h = np.sin((b - a) / 2) ** 2 + np.cos(a) * np.cos(b) * np.sin((p - o) / 2) ** 2
        out[i:i+chunk] = (2 * 6371 * np.arcsin(np.sqrt(h))).min(1)
    return out
m = (prov >= 0) & ~fija
la, lo, pr, ec = lat[m], lon[m], prov[m], eco[m]
ds, dz = dmin(la, lo, sl, so), dmin(la, lo, zl, zo)
print(f'focos limpios {len(la):,}')
for r in (25, 50, 100):
    print(f'  a ≤{r} km  · de un punto SMN {100*(ds<=r).mean():.0f} %  · de una zona GeoFuego {100*(dz<=r).mean():.0f} %')
print(f'  distancia mediana: SMN {np.median(ds):.0f} km · GeoFuego {np.median(dz):.0f} km')
dzs = dmin(zl, zo, sl, so)
print(f'zonas GeoFuego con un punto SMN a ≤25 km: {(dzs<=25).sum()}/{len(Z)} · ≤50 km: {(dzs<=50).sum()}/{len(Z)} · mediana {np.median(dzs):.0f} km')
# coincidencia exacta de ubicación
print(f'puntos SMN: {len(S)}  (en padrón SMN {sum(s["residuo_px"]<=3 for s in S)})')
# por provincia
PROV_SMN = {}
import unicodedata
nrm = lambda s: unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()
from shapely.geometry import Polygon; import shapely
PR = json.load(open(f'{AQ}/provincias.json'))
pg = {p['n']: shapely.MultiPolygon([Polygon([(x, y) for y, x in r]) for r in p['rings']]).buffer(0) for p in PR}
def prov_de(a, o):
    for n, g in pg.items():
        if g.contains(shapely.Point(o, a)): return n
    d = {n: g.distance(shapely.Point(o, a)) for n, g in pg.items()}; return min(d, key=d.get)
cnt = {}
for s in S: cnt[prov_de(s['lat'], s['lon'])] = cnt.get(prov_de(s['lat'], s['lon']), 0) + 1
print('\nprovincia | puntos SMN | zonas GF | % fuego a ≤50 km SMN | GF | dist mediana SMN/GF km')
rows = []
for i, P in enumerate(pn):
    mm = pr == i
    if mm.sum() < 50: continue
    rows.append((P, cnt.get(P, 0), len(CAL.get(P, [])), 100 * (ds[mm] <= 50).mean(), 100 * (dz[mm] <= 50).mean(), np.median(ds[mm]), np.median(dz[mm]), mm.sum()))
for r in sorted(rows, key=lambda r: r[3]):
    print(f'{r[0][:24]:24s} | {r[1]:2d} | {r[2]} | {r[3]:3.0f} % | {r[4]:3.0f} % | {r[5]:4.0f} / {r[6]:3.0f}')
print('\necorregión | % del fuego | puntos SMN | % fuego a ≤50 km SMN | GF')
se = {}
eco_g = json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features']
from shapely.geometry import shape
EG = [(f['properties']['ecorregion'], shape(f['geometry']).buffer(0)) for f in eco_g]
for s in S:
    p = shapely.Point(s['lon'], s['lat']); n = next((n for n, g in EG if g.contains(p)), None)
    if n is None: n = min(EG, key=lambda t: t[1].distance(p))[0]
    se[n] = se.get(n, 0) + 1
for e in np.argsort(-np.bincount(ec, minlength=len(en))):
    mm = ec == e
    if mm.mean() < .005: continue
    print(f'{en[e][:28]:28s} | {100*mm.mean():4.1f} % | {se.get(en[e],0):2d} | {100*(ds[mm]<=50).mean():3.0f} % | {100*(dz[mm]<=50).mean():3.0f} %')
