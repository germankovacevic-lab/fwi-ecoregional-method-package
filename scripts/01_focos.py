#!/usr/bin/env python3
"""Auditoría de zonas de fuego — paso 1: focos VIIRS 2012–2024 con provincia, ecorregión y marca de fuente fija.

Mismos filtros que tools/gfi_v2/01_zonas_fuego.mjs (conf != l, type == 0, PIP provincias IGN).
Ecorregión: capa oficial areas_protegidas:ecoregiones2021 (Ministerio de Ambiente, geo.ambiente.gob.ar),
bajada a ~/.openclaw/data/ecorregiones/eco2021.json.
Fuente fija: (a) máscara de producción worker/src/fuentes_fijas.json (≤ radio_m) o
(b) celda 0,02° con focos en ≥ 9 meses distintos dentro de una ventana de 12 (criterio de ventana de 01b_focos_sin_fijas.mjs).
Salida: data/focos.npz
"""
import json, os, glob
import numpy as np, pandas as pd
import shapely
from shapely.geometry import shape, Polygon

H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f'{AQ}/data', exist_ok=True)

prov = json.load(open(f'{AQ}/provincias.json'))
pnames = [p['n'] for p in prov]
pgeo = [shapely.MultiPolygon([Polygon([(x, y) for y, x in r]) for r in p['rings']]).buffer(0) for p in prov]

eco = json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features']
enames = [f['properties']['ecorregion'] for f in eco]
egeo = [shape(f['geometry']).buffer(0) for f in eco]

frames = []
for y in range(2012, 2025):
    df = pd.read_csv(H(f'~/.openclaw/data/firms_ar/viirs_{y}.csv'),
                     usecols=['latitude', 'longitude', 'acq_date', 'confidence', 'frp', 'type'],
                     dtype={'confidence': str, 'type': str})
    df = df[(df.confidence != 'l') & (df['type'].str.strip() == '0')]
    frames.append(df[['latitude', 'longitude', 'acq_date', 'frp']])
    print(y, len(df), flush=True)
df = pd.concat(frames, ignore_index=True)
lat, lon = df.latitude.values, df.longitude.values

pi = np.full(len(df), -1, np.int16)
for i, g in enumerate(pgeo):
    shapely.prepare(g)
    m = (pi < 0) & shapely.contains_xy(g, lon, lat)
    pi[m] = i
ei = np.full(len(df), -1, np.int16)
for i, g in enumerate(egeo):
    shapely.prepare(g)
    m = (ei < 0) & shapely.contains_xy(g, lon, lat)
    ei[m] = i
# focos fuera de todo polígono de ecorregión (costa, simplificación): ecorregión del polígono más cercano
sin = np.where((ei < 0) & (pi >= 0))[0]
if len(sin):
    pts = shapely.points(lon[sin], lat[sin])
    d = np.stack([shapely.distance(g, pts) for g in egeo])
    ei[sin] = d.argmin(0)

# (a) máscara de producción
ff = json.load(open(f'{AQ}/../../worker/src/fuentes_fijas.json'))
R = ff['radio_m']
fl = np.array([[a, b] for a, b, *_ in ff['fuentes']])
fija_a = np.zeros(len(df), bool)
for a, b in fl:
    dl = np.radians(lat - a); dn = np.radians(lon - b)
    near = (np.abs(lat - a) < 0.02) & (np.abs(lon - b) < 0.03)
    if not near.any(): continue
    idx = np.where(near)[0]
    h = np.sin(dl[idx] / 2) ** 2 + np.cos(np.radians(a)) * np.cos(np.radians(lat[idx])) * np.sin(dn[idx] / 2) ** 2
    fija_a[idx[2 * 6371000 * np.arcsin(np.sqrt(h)) <= R]] = True
# (b) celdas persistentes
ym = df.acq_date.str[:7].values
cal = df.acq_date.str[5:7].values
cel = (np.floor(lat / 0.02).astype(np.int64) * 100000 + np.floor(lon / 0.02).astype(np.int64))
# criterio de ventana del 01b (producción, 13/11): ≥ 9 meses distintos dentro de alguna ventana de 12 meses
t = pd.DataFrame({'c': cel, 'k': df.acq_date.str[:4].astype(int).values * 12 + df.acq_date.str[5:7].astype(int).values - 1})
t = t.drop_duplicates().sort_values(['c', 'k'])
pers = set()
for c, kk in t.groupby('c').k:
    a = kk.values
    if len(a) < 9: continue
    j = 0
    for i in range(len(a)):
        while a[i] - a[j] >= 12: j += 1
        if i - j + 1 >= 9: pers.add(c); break
fija_b = np.isin(cel, list(pers))

np.savez_compressed(f'{AQ}/data/focos.npz', lat=lat.astype(np.float32), lon=lon.astype(np.float32),
                    fecha=df.acq_date.values.astype('U10'), frp=df.frp.values.astype(np.float32),
                    prov=pi, eco=ei, fija=(fija_a | fija_b), fija_a=fija_a,
                    pnames=np.array(pnames), enames=np.array(enames))
print('total', len(df), 'sin provincia', int((pi < 0).sum()), 'fijas a', int(fija_a.sum()), 'fijas a|b', int((fija_a | fija_b).sum()))
