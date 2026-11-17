#!/usr/bin/env python3
"""¿Cuánto dispara cada provincia según su número de zonas? (regla A-zonal: cualquier zona > su umbral).
Estadístico operado: media móvil 30 d del DC ERA5 al último día del mes; umbral = 11.º menor de 13 (2012–2024).
Salida: data/tasa_disparo.json"""
import json, os
import numpy as np, pandas as pd
H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
CAL = json.load(open(f'{AQ}/../../worker/src/calibracion_3.0_argentina.json'))['zonas']
out = {}
for P, Z in CAL.items():
    S = {}
    for z in Z:
        zid = f"{z['lat']:.2f}_{z['lon']:.2f}"
        p = H(f'~/.openclaw/data/gfi_v2_fwi_cds/fwi_{zid}.csv')
        if not os.path.exists(p): continue
        d = pd.read_csv(p, parse_dates=['date']).set_index('date')['dc']
        m = d.rolling(30, min_periods=25).mean().resample('ME').last()
        m = m[(m.index.year >= 2012) & (m.index.year <= 2024)]
        thr = m.groupby(m.index.month).transform(lambda s: np.sort(s.values)[10] if len(s) >= 13 else np.nan)
        S[zid] = (m > thr).astype(int)
    if not S: continue
    D = pd.DataFrame(S).dropna()
    zr = D.mean()
    anyr = float(D.max(axis=1).mean())
    indep = 1 - np.prod(1 - zr.values)
    # co-disparo medio entre pares (Jaccard)
    J = []
    cols = list(D)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = D[cols[i]], D[cols[j]]
            u = ((a + b) > 0).sum()
            J.append(float(((a & b).sum()) / u) if u else 0)
    out[P] = dict(k=len(cols), tasa_zona_media=round(float(zr.mean()), 3), tasa_provincia=round(anyr, 3),
                  si_independientes=round(float(indep), 3), jaccard_medio=round(float(np.mean(J)), 2) if J else None)
json.dump(out, open(f'{AQ}/data/tasa_disparo.json', 'w'), ensure_ascii=False, indent=1)
for P, r in sorted(out.items(), key=lambda x: -x[1]['tasa_provincia']):
    print(f"{P[:28]:28s} k={r['k']} zona={r['tasa_zona_media']:.3f} prov={r['tasa_provincia']:.3f} indep={r['si_independientes']:.3f} J={r['jaccard_medio']}")
