#!/usr/bin/env python3
"""Mapas v3 vs v4 por provincia: ecorregiones oficiales, unidades Oyarzabal (líneas), focos limpios, zonas v3 (círculo) y v4 (estrella)."""
import json, os, sys, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import shape
H = os.path.expanduser; AQ = os.path.dirname(os.path.abspath(__file__))
V4 = json.load(open(f'{AQ}/data/{sys.argv[1] if len(sys.argv) > 1 else "zonas_v4_split5.json"}'))
F = np.load(f'{AQ}/data/focos.npz'); lat, lon, prov, fija = F['lat'], F['lon'], F['prov'], F['fija']; pn = list(F['pnames'])
CAL = json.load(open(f'{AQ}/../../worker/src/calibracion_3.0_argentina.json'))['zonas']
eco = json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features']
EC = {f['properties']['ecorregion']: plt.get_cmap('tab20')(i % 20) for i, f in enumerate(eco)}
EG = [(f['properties']['ecorregion'], shape(f['geometry'])) for f in eco]
UG = [shape(f['geometry']) for f in json.load(open(H('~/.openclaw/data/oyarzabal2018/unidades_vegetacion.geojson')))['features']]
PR = {p['n']: p['rings'] for p in json.load(open(f'{AQ}/provincias.json'))}
polys = lambda g: [g] if g.geom_type == 'Polygon' else list(getattr(g, 'geoms', []))
fk = None
if os.path.exists(H('~/.openclaw/workspace/tmp/tdf4/focos_tdf_2012_2024.json')):
    fk = json.load(open(H('~/.openclaw/workspace/tmp/tdf4/focos_tdf_2012_2024.json')))
out = f'{AQ}/data/zonas_v4_mapas.pdf'
with PdfPages(out) as pdf:
    for i, P in enumerate(pn):
        Z4 = V4['zonas'].get(P)
        if not Z4 or P.startswith('Ciudad'): continue
        m = prov == i; la, lo, fj = lat[m], lon[m], fija[m]
        if P.startswith('Tierra') and fk:
            la = np.r_[la, [f['lat'] for f in fk if f['src'] == 'fk']]; lo = np.r_[lo, [f['lon'] for f in fk if f['src'] == 'fk']]; fj = np.r_[fj, [f['fijo'] for f in fk if f['src'] == 'fk']]
        x0, x1, y0, y1 = lo.min() - .3, lo.max() + .3, la.min() - .3, la.max() + .3
        fig, ax = plt.subplots(figsize=(11, 8.5)); usadas = set()
        for nme, g in EG:
            b = g.bounds
            if b[0] > x1 or b[2] < x0 or b[1] > y1 or b[3] < y0: continue
            for p in polys(g): xs, ys = p.exterior.xy; ax.fill(xs, ys, color=EC[nme], alpha=.25, lw=0); usadas.add(nme)
        for g in UG:
            b = g.bounds
            if b[0] > x1 or b[2] < x0 or b[1] > y1 or b[3] < y0: continue
            for p in polys(g): xs, ys = p.exterior.xy; ax.plot(xs, ys, color='0.35', lw=.5, ls='--')
        for r in PR[P]: a = np.array(r); ax.plot(a[:, 1], a[:, 0], 'k-', lw=.9)
        hb = ax.hexbin(lo[~fj], la[~fj], gridsize=60, bins='log', mincnt=1, cmap='YlOrRd', alpha=.8, extent=(x0, x1, y0, y1))
        for z in CAL.get(P, []): ax.scatter(z['lon'], z['lat'], s=60 + 700 * z['peso'], facecolors='none', edgecolors='0.3', lw=1.5)
        for z in Z4:
            ax.scatter(z['lon'], z['lat'], s=120 + 900 * z['peso'], marker='*', c='b', edgecolors='w', lw=.8)
            lab = (z.get('unidad') or z['regimen']).split(' ', 1)[-1] if z.get('unidad') else z['regimen']
            ax.annotate(f"{lab[:26]} {z['peso']:.2f}", (z['lon'], z['lat']), xytext=(7, -10), textcoords='offset points', fontsize=7.5, weight='bold', color='navy')
        for nme in usadas: ax.fill([], [], color=EC[nme], alpha=.4, label=nme)
        ax.plot([], [], color='0.35', lw=.6, ls='--', label='unidades Oyarzabal 2018')
        ax.scatter([], [], s=120, facecolors='none', edgecolors='0.3', label=f'v3 ({len(CAL.get(P, []))} zonas)')
        ax.scatter([], [], s=150, marker='*', c='b', label=f'v4 ({len(Z4)} zonas)')
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect(1 / np.cos(np.radians((y0 + y1) / 2)))
        ax.set_title(f'{P} — zonas v3 {len(CAL.get(P, []))} → v4 {len(Z4)}', fontsize=12); ax.legend(loc='lower left', fontsize=7, framealpha=.85)
        fig.colorbar(hb, ax=ax, shrink=.6, label='focos limpios 2012–2024 (log)')
        pdf.savefig(fig, bbox_inches='tight'); plt.close(fig)
print(out)
