#!/usr/bin/env python3
"""Mapas de la auditoría: una página por provincia → data/auditoria_zonas_mapas.pdf"""
import json, os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import shape
H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
F = np.load(f'{AQ}/data/focos.npz')
lat, lon, prov, fija = F['lat'], F['lon'], F['prov'], F['fija']
pn = list(F['pnames'])
R = json.load(open(f'{AQ}/data/auditoria.json'))
T = json.load(open(f'{AQ}/data/tasa_disparo.json'))
eco = json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features']
cmap = plt.get_cmap('tab20')
EC = {f['properties']['ecorregion']: cmap(i % 20) for i, f in enumerate(eco)}
EG = [(f['properties']['ecorregion'], shape(f['geometry'])) for f in eco]
PR = {p['n']: p['rings'] for p in json.load(open(f'{AQ}/provincias.json'))}
def polys(g):
    return [g] if g.geom_type == 'Polygon' else list(g.geoms) if hasattr(g, 'geoms') else []
with PdfPages(f'{AQ}/data/auditoria_zonas_mapas.pdf') as pdf:
    for i, P in enumerate(pn):
        r = R.get(P)
        if not r or not r.get('zonas') or P.startswith('Ciudad'): continue
        m = prov == i
        la, lo, fj = lat[m], lon[m], fija[m]
        x0, x1, y0, y1 = lo.min() - .3, lo.max() + .3, la.min() - .3, la.max() + .3
        fig, ax = plt.subplots(figsize=(11, 8.5))
        usadas = set()
        for n, g in EG:
            if g.bounds[0] > x1 or g.bounds[2] < x0 or g.bounds[1] > y1 or g.bounds[3] < y0: continue
            for p in polys(g):
                xs, ys = p.exterior.xy
                ax.fill(xs, ys, color=EC[n], alpha=.25, lw=0); usadas.add(n)
        for ring in PR[P]:
            a = np.array(ring); ax.plot(a[:, 1], a[:, 0], 'k-', lw=.8)
        hb = ax.hexbin(lo[~fj], la[~fj], gridsize=60, bins='log', mincnt=1, cmap='YlOrRd', alpha=.85, extent=(x0, x1, y0, y1))
        if fj.any(): ax.scatter(lo[fj], la[fj], s=2, c='m', marker='x', lw=.5, label=f'fuente fija ({fj.mean()*100:.0f} %)')
        for z in r['zonas']:
            zl, zo = map(float, z['zid'].split('_'))
            ax.scatter(zo, zl, s=60 + 900 * z['peso'], facecolors='none', edgecolors='k', lw=2)
            ax.annotate(f"{z['peso']:.2f}" + (' ' + ' '.join(z.get('banderas', [])) if z.get('banderas') else ''), (zo, zl), xytext=(6, 6), textcoords='offset points', fontsize=8, weight='bold')
        for p in r['propuesta']:
            ax.scatter(p['lon'], p['lat'], s=140, marker='*', c='b', edgecolors='w', lw=.6)
        for n in usadas: ax.fill([], [], color=EC[n], alpha=.4, label=n)
        ax.scatter([], [], s=150, facecolors='none', edgecolors='k', lw=2, label='zona actual (tamaño = peso)')
        ax.scatter([], [], s=140, marker='*', c='b', label='propuesta borrador (ecorregión)')
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect(1 / np.cos(np.radians((y0 + y1) / 2)))
        t = T.get(P, {})
        ax.set_title(f"{P} — {len(r['zonas'])} zonas · {r['n_total']:,} focos VIIRS 2012–2024 · provincia escala en {t.get('tasa_provincia',0)*100:.0f} % de los meses", fontsize=11)
        ax.legend(loc='lower left', fontsize=7, framealpha=.8)
        fig.colorbar(hb, ax=ax, shrink=.6, label='focos limpios (log)')
        pdf.savefig(fig, bbox_inches='tight'); plt.close(fig)
print('ok')
