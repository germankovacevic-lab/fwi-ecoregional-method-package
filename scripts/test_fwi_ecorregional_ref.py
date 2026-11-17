#!/usr/bin/env python3
"""Referencia Python del Semáforo FWI ecorregional → data/paridad_fwi_ecorregional.json (casos fijos para el test JS).
Casos: 300 días de historia real (FWI vivo emulado de cada punto, 2021-04 → 2026-10) + 20 días con puntos faltantes."""
import json, os, numpy as np, pandas as pd
AQ = os.path.dirname(os.path.abspath(__file__)); H = os.path.expanduser
CAL = json.load(open(f'{AQ}/../../worker/src/fwi_ecorregional.json'))
def eq(z, x):
    o = CAL['zonas'][z]; qv, qe = np.array(o['q_vivo']), np.array(o['q_era5'])
    if x <= qv[0]: return float(qe[0])
    if x >= qv[-2]: return float(max(qe[-2], x * o['cola']))
    return float(np.interp(x, qv, qe))
def nivel(e, f):
    return int(sum(f >= c for c in CAL['ecorregiones'][e]['cortes']))
V = {z: pd.read_csv(H(f'~/.openclaw/data/gfi_v4_vivo/vivo_{z}.csv')).set_index('date')['sem'] for z in CAL['zonas']}
fechas = sorted(set.intersection(*[set(v.dropna().index) for v in V.values()]))
rng = np.random.default_rng(1)
sel = list(rng.choice(fechas, 320, replace=False))
casos = []
for k, d in enumerate(sel):
    fw = {z: round(float(V[z][d]), 2) for z in CAL['zonas']}
    if k >= 300:
        for z in rng.choice(list(fw), 15, replace=False): fw.pop(z)
    e = {z: eq(z, x) for z, x in fw.items()}
    ecos = {}
    for n, o in CAL['ecorregiones'].items():
        zs = [z for z in o['zonas'] if z in e]
        if not zs: continue
        w = np.array([CAL['zonas'][z]['peso_eco'] for z in zs], float)
        if w.sum() <= 0: continue
        f = float((w * np.array([e[z] for z in zs])).sum() / w.sum()); ecos[n] = dict(fwi_eq=f, nivel=nivel(n, f))
    provs = {}
    for P, pes in CAL['provincias'].items():
        num = den = 0.0
        for n, w in pes.items():
            if n in ecos: num += w * ecos[n]['nivel']; den += w
        if den > 0: provs[P] = int(np.floor(num / den + 0.5))
    casos.append(dict(fecha=d, fwi=fw, ecorregiones=ecos, provincias=provs))
json.dump(dict(sha256=CAL['sha256'], casos=casos), open(f'{AQ}/data/paridad_fwi_ecorregional.json', 'w'))
print(len(casos), 'casos')
