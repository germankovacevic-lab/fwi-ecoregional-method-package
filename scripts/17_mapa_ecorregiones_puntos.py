#!/usr/bin/env python3
"""Mapa país: ecorregiones oficiales (MAyDS 2021) y los 90 puntos meteorológicos del FWI por ecorregión (E1).
Tamaño del punto = su peso dentro de la ecorregión (focos limpios 2012–2021 que representa)."""
import json, os, unicodedata, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape
H = os.path.expanduser; AQ = os.path.dirname(os.path.abspath(__file__))
nrm = lambda s: unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
eco = [f for f in json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features'] if f['properties']['ecorregion'] not in ('Mar Argentino', 'Antartida')]
PR = json.load(open(f'{AQ}/provincias.json'))
Z = json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas']
pts = [(z['lat'], z['lon'], nrm(z['regimen']), z['n_focos']) for P, v in Z.items() for z in v if not P.startswith('Ciudad')]
cmap = plt.get_cmap('tab20')
nombres = sorted({nrm(f['properties']['ecorregion']) for f in eco})
col = {n: cmap(i % 20) for i, n in enumerate(nombres)}
lindo = {nrm(f['properties']['ecorregion']): f['properties']['ecorregion'].replace('Parana', 'Paraná').replace('Ibera', 'Iberá').replace('Patagonicos', 'Patagónicos').replace('Patagonica', 'Patagónica').replace('Humedo', 'Húmedo').replace('Atlantico', 'Atlántico') for f in eco}
tot = {}
for la, lo, e, n in pts: tot[e] = tot.get(e, 0) + n
fig, ax = plt.subplots(figsize=(14, 15))
for f in eco:
    g = shape(f['geometry']); n = nrm(f['properties']['ecorregion'])
    for p in ([g] if g.geom_type == 'Polygon' else g.geoms):
        xs, ys = p.exterior.xy; ax.fill(xs, ys, color=col[n], alpha=.45, lw=.3, ec='w')
for p in PR:
    for r in p['rings']:
        a = np.array(r); ax.plot(a[:, 1], a[:, 0], color='0.25', lw=.5, ls=':')
for la, lo, e, n in pts:
    ax.scatter(lo, la, s=25 + 500 * n / tot[e], color=col[e], edgecolors='k', lw=1, zorder=5)
cnt = {}
for _, _, e, _ in pts: cnt[e] = cnt.get(e, 0) + 1
for e in nombres:
    ax.fill([], [], color=col[e], alpha=.6, label=f"{lindo[e]} — {cnt.get(e, 0)} punto{'s' if cnt.get(e, 0) != 1 else ''}")
ax.scatter([], [], s=120, facecolors='w', edgecolors='k', label='punto meteorológico (tamaño = cuánto fuego representa en su ecorregión)')
ax.plot([], [], color='0.25', lw=.6, ls=':', label='límite provincial (no corta el cálculo)')
ax.set_xlim(-74.5, -53); ax.set_ylim(-55.5, -21.5); ax.set_aspect(1 / np.cos(np.radians(-38)))
ax.set_title(f'GeoFuego · Semáforo FWI por ecorregión (propuesta E1)\necorregiones oficiales (Ministerio de Ambiente 2021) · {len(pts)} puntos meteorológicos ERA5', fontsize=12)
ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=8.5, framealpha=.95)
ax.set_xticks([]); ax.set_yticks([])
out = f'{AQ}/data/mapa_ecorregiones_puntos_fwi.png'; fig.savefig(out, dpi=130, bbox_inches='tight'); print(out)
