#!/usr/bin/env python3
"""Evaluación del Semáforo FWI v3 vs v4.1 (METODO_v4 §5.2 y §7).

Las dos versiones se calibran con el MISMO código y el mismo período, y se evalúan sobre el mismo blanco:
  v3   zonas de producción (115) · subregiones de producción (k-means estadístico, fwi_clases_regionales.json)
  v4   zonas v4.1 (90)          · subregiones R5b (grupos de ecorregiones), con la condición de ≥ 300 días fuertes
FWI: historia ERA5 con el motor del worker (tabla DMC por latitud). Escala ERA5 (el mapeo del vivo es aparte).
Calibración 2012–2021: día fuerte de zona = focos limpios de la zona ≥ p90 de sus días con foco; cortes de la
subregión = p10/p25/p50/p75 del FWI en los días fuertes de sus zonas (umbral de ocurrencia, igual que producción).
Clase de la provincia = la de su peor zona (igual que producción).
Blanco común (no depende de las zonas): día fuerte de PROVINCIA = focos limpios de la provincia ≥ p90 de sus días con
foco 2012–2021. Fuera de muestra: 2022-01-01 → 2026-10-30. Focos limpios = R1 v4 para las dos versiones.
Métricas: PSS de ≥ Alto y ≥ Muy alto, AUC del nivel, tasa de alarma (≥ Alto); IC 95 % de Δ (v4 − v3) por bootstrap de
meses (2000). Aceptación (§7, adaptada porque las subregiones v3 y v4 no se corresponden 1 a 1): el PSS ≥ Alto
fuera de muestra no empeora en forma significativa en ninguna de las 4 regiones (NEA, NOA, Centro, Patagonia).
Salida: data/evaluacion_fwi.json, data/evaluacion_fwi.md
"""
import json, os, sys, unicodedata
import numpy as np, pandas as pd
H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
REPO = f'{AQ}/../..'
os.environ['FOCOS_HASTA'] = '2026'
sys.argv = ['07', '--split5', '--piso=50']
src = open(f'{AQ}/07_zonas_v4.py').read()
g = {'__file__': f'{AQ}/07_zonas_v4.py', '__name__': 'x'}
exec(compile(src[:src.index('# ---------- R2/R3/R4 por provincia')], '07', 'exec'), g)
df, prov, fija, pn, lat, lon, hav = g['df'], g['prov'], g['fija'], g['pn'], g['lat'], g['lon'], g['hav']
fecha = pd.to_datetime(df.acq_date.values)
ok = ~fija & (fecha <= '2026-10-30')
lat, lon, prov, fecha = lat[ok], lon[ok], prov[ok], fecha[ok]
DIAS = pd.date_range('2012-01-01', '2026-10-30')
CAL_FIN, OOS_INI = pd.Timestamp('2021-12-31'), pd.Timestamp('2022-01-01')
PROVS = [p for p in pn if not p.startswith('Ciudad')]
CAL = json.load(open(f'{REPO}/worker/src/calibracion_3.0_argentina.json'))
REGION = CAL['provincia_region']
CLS = json.load(open(f'{REPO}/worker/src/fwi_clases_regionales.json'))
nrm = lambda s: unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()

R5B = {'chaco humedo': 'NEA húmedo', 'esteros del ibera': 'NEA húmedo', 'campos y malezales': 'NEA húmedo',
       'delta e islas del parana': 'NEA húmedo', 'selva paranense': 'NEA húmedo', 'chaco seco': 'Chaco Seco',
       'yungas': 'Yungas', 'monte de sierras y bolsones': 'Árido', 'monte de llanuras y mesetas': 'Árido', 'puna': 'Árido',
       'altos andes': 'Árido', 'espinal': 'Centro', 'pampa': 'Centro', 'estepa patagonica': 'Patagonia estepa',
       'bosques patagonicos': 'Patagonia húmeda', 'islas del atlantico sur': 'Patagonia húmeda'}
FALLBACK = {'Yungas': 'Chaco Seco', 'Patagonia húmeda': 'Patagonia estepa', 'Árido': 'Chaco Seco', 'Centro': 'Chaco Seco'}

from shapely.geometry import shape, Point
_ECO = [(f['properties']['ecorregion'], shape(f['geometry']).buffer(0)) for f in json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features'] if f['properties']['ecorregion'] not in ('Mar Argentino', 'Antartida')]
def eco_de(la, lo):
    p = Point(lo, la)
    for n, g in _ECO:
        if g.contains(p): return n
    return min(_ECO, key=lambda t: t[1].distance(p))[0]

def kmeans2(X, iters=50):
    c = np.array([X[np.argmin(X[:, 0])], X[np.argmax(X[:, 0])]])
    for _ in range(iters):
        lab = np.argmin(((X[:, None, :] - c[None]) ** 2).sum(2), 1)
        nc = np.array([X[lab == k].mean(0) if (lab == k).any() else c[k] for k in range(2)])
        if np.allclose(nc, c): break
        c = nc
    return lab

def subs_fwi(Z):
    """Algoritmo de producción (tools/fwi_snmf/02_tablas_regionales.py): k=2 sobre log(p70,p90) del FWI 2012–2025 dentro de cada región."""
    q = {}
    for z in Z:
        x = pd.read_csv(z['path']).set_index('date')['fwi']; x = x[(x.index >= '2012-01-01') & (x.index <= '2025-12-31')]
        q[z['zid']] = (x.quantile(.7), x.quantile(.9))
    for r in set(REGION[z['P']] for z in Z):
        zs = [z for z in Z if REGION[z['P']] == r]
        p90 = np.array([q[z['zid']][1] for z in zs])
        if p90.max() / max(p90.min(), .1) > 4:
            lab = kmeans2(np.log1p(np.array([q[z['zid']] for z in zs])))
            if p90[lab == 0].mean() > p90[lab == 1].mean(): lab = 1 - lab
            for z, l in zip(zs, lab): z['sub'] = f"{r} {'húmeda' if l == 0 else 'seca'}"
        else:
            for z in zs: z['sub'] = r
    return Z

def version(nombre, subs_mode=None):
    Z = []
    if nombre == 'v3':
        sub = {z: s for s, o in CLS['subregiones'].items() for z in o['zonas']}
        for P, v in CAL['zonas'].items():
            for z in v:
                zid = f"{z['lat']:.2f}_{z['lon']:.2f}"
                Z.append(dict(P=P, zid=zid, lat=z['lat'], lon=z['lon'], sub=sub.get(zid), path=f'{REPO}/tools/fwi_argentina/data/era5/fwi_{zid}.csv'))
    else:
        for P, v in json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas'].items():
            for z in v:
                Z.append(dict(P=P, zid=z['zid'], lat=z['lat'], lon=z['lon'], sub=R5B[nrm(z['regimen'])],
                              path=H(f"~/.openclaw/data/gfi_v4_fwi_worker/fwi_{z['zid']}.csv")))
    Z = [z for z in Z if z['P'] in PROVS]
    if subs_mode == 'fwi': Z = subs_fwi(Z)
    if subs_mode == 'r5b':
        for z in Z: z['sub'] = R5B[nrm(eco_de(z['lat'], z['lon']))]
    return Z

def conteo_diario(idx):
    c = pd.Series(fecha[idx]).value_counts()
    return c.reindex(DIAS).fillna(0).values

# blanco común: día fuerte de provincia
EVP = {}
for P in PROVS:
    c = conteo_diario(np.where(prov == pn.index(P))[0])
    cal = c[(DIAS <= CAL_FIN) & (c > 0)]
    EVP[P] = c >= np.percentile(cal, 90) if len(cal) else np.zeros(len(DIAS), bool)
EVP = pd.DataFrame(EVP, index=DIAS)

def evaluar(nombre, subs_mode=None):
    Z = version(nombre, subs_mode)
    usa_r5b = (nombre == 'v4' and subs_mode is None) or subs_mode == 'r5b'
    FWI = {z['zid']: pd.read_csv(z['path']).set_index('date')['fwi'].reindex(DIAS.strftime('%Y-%m-%d')).values for z in Z}
    # focos limpios → zona más cercana de su provincia; día fuerte de zona
    fuerte = {}
    for P in PROVS:
        zs = [z for z in Z if z['P'] == P]
        ii = np.where(prov == pn.index(P))[0]
        a = np.stack([hav(lat[ii], lon[ii], z['lat'], z['lon']) for z in zs]).argmin(0)
        for k, z in enumerate(zs):
            c = conteo_diario(ii[a == k]); cal = c[(DIAS <= CAL_FIN) & (c > 0)]
            fuerte[z['zid']] = (c >= np.percentile(cal, 90)) & (c > 0) if len(cal) >= 10 else np.zeros(len(DIAS), bool)
    calm = DIAS <= CAL_FIN
    subs = {}
    for z in Z: subs.setdefault(z['sub'], []).append(z['zid'])
    n_fuertes = {s: int(sum((fuerte[i] & calm).sum() for i in v)) for s, v in subs.items()}
    fusion = {}
    if usa_r5b:  # condición de muestra R5b
        for s, n in n_fuertes.items():
            if n < 300: fusion[s] = FALLBACK[s]
        for z in Z:
            while z['sub'] in fusion: z['sub'] = fusion[z['sub']]
        subs = {}
        for z in Z: subs.setdefault(z['sub'], []).append(z['zid'])
    cortes = {}
    for s, v in subs.items():
        x = np.concatenate([FWI[i][fuerte[i] & calm] for i in v]); x = x[~np.isnan(x)]
        cortes[s] = [round(float(q), 1) for q in np.percentile(x, [10, 25, 50, 75])]
    nivel = {z['zid']: np.where(np.isnan(FWI[z['zid']]), -1, np.digitize(FWI[z['zid']], cortes[z['sub']])) for z in Z}
    NP = pd.DataFrame({P: np.max([nivel[z['zid']] for z in Z if z['P'] == P], axis=0) for P in PROVS}, index=DIAS)
    return dict(NP=NP, nivel=nivel, Z=Z, cortes=cortes, n_fuertes=n_fuertes, fusion=fusion, n_zonas=len(Z),
                subs={s: len(v) for s, v in subs.items()})

def auc(score, y):
    from scipy.stats import rankdata
    r = rankdata(score); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else np.nan

def met(NP, ev, mask):
    l = NP.values[mask].ravel(); y = ev.values[mask].ravel(); v = l >= 0; l, y = l[v], y[v]
    def pss(th):
        a = l >= th; h = (a & y).sum() / max(y.sum(), 1); f = (a & ~y).sum() / max((~y).sum(), 1); return float(h - f)
    return dict(pss_alto=pss(2), pss_muyalto=pss(3), auc=auc(l, y), alarma=float((l >= 2).mean()), n_eventos=int(y.sum()))

E3, E4 = evaluar('v3'), evaluar('v4')
EX = {'v3 zonas + subregiones R5b': evaluar('v3', 'r5b'), 'v4 zonas + subregiones estadísticas (algoritmo de producción)': evaluar('v4', 'fwi')}
oos = np.asarray(DIAS >= OOS_INI)
meses = DIAS[oos].to_period('M')
um = meses.unique()
rng = np.random.default_rng(20261117)
GRUPOS = {'País': PROVS}
for P in PROVS: GRUPOS.setdefault(REGION[P], []).append(P)
res = dict(cortes_v3=E3['cortes'], cortes_v4=E4['cortes'], fuertes_v3=E3['n_fuertes'], fuertes_v4=E4['n_fuertes'],
           fusion_v4=E4['fusion'], subregiones_v4=E4['subs'], grupos={}, provincias={})
for gname, ps in list(GRUPOS.items()) + [(P, [P]) for P in PROVS]:
    ev = EVP[ps]; a3, a4 = E3['NP'][ps], E4['NP'][ps]
    m3, m4 = met(a3, ev, oos), met(a4, ev, oos)
    i3, i4 = met(a3, ev, ~oos), met(a4, ev, ~oos)
    # bootstrap de meses fuera de muestra
    L3, L4, Y = a3.values[oos], a4.values[oos], ev.values[oos]
    bloques = [np.where(meses == m)[0] for m in um]
    d = []
    for _ in range(2000):
        ix = np.concatenate([bloques[k] for k in rng.integers(0, len(bloques), len(bloques))])
        def p(L):
            l, y = L[ix].ravel(), Y[ix].ravel(); v = l >= 0; l, y = l[v], y[v]; a = l >= 2
            return (a & y).sum() / max(y.sum(), 1) - (a & ~y).sum() / max((~y).sum(), 1)
        d.append(p(L4) - p(L3))
    r = dict(oos_v3=m3, oos_v4=m4, in_v3=i3, in_v4=i4, dif_pss_alto=dict(media=float(np.mean(d)), ic95=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]))
    (res['grupos'] if gname in GRUPOS else res['provincias'])[gname] = r
res['diagnostico_2x2'] = {}
for nom, EXk in EX.items():
    res['diagnostico_2x2'][nom] = {gname: met(EXk['NP'][ps], EVP[ps], oos)['pss_alto'] for gname, ps in GRUPOS.items()}
    for gname, ps in GRUPOS.items():
        L3, LX, Y = E3['NP'][ps].values[oos], EXk['NP'][ps].values[oos], EVP[ps].values[oos]
        bl = [np.where(meses == m)[0] for m in um]; d = []
        for _ in range(2000):
            ix = np.concatenate([bl[k] for k in rng.integers(0, len(bl), len(bl))])
            def p(L):
                l, y = L[ix].ravel(), Y[ix].ravel(); v = l >= 0; l, y = l[v], y[v]; a = l >= 2
                return (a & y).sum() / max(y.sum(), 1) - (a & ~y).sum() / max((~y).sum(), 1)
            d.append(p(LX) - p(L3))
        res['diagnostico_2x2'][nom][gname + '_dif_ic95'] = [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)]
    res['diagnostico_2x2'][nom]['_subregiones'] = EXk['subs']; res['diagnostico_2x2'][nom]['_fusion'] = EXk['fusion']
json.dump(res, open(f'{AQ}/data/evaluacion_fwi.json', 'w'), ensure_ascii=False, indent=1)

def fila(n, r):
    a, b, d = r['oos_v3'], r['oos_v4'], r['dif_pss_alto']
    sig = '✅' if d['ic95'][0] > 0 else ('❌' if d['ic95'][1] < 0 else '≈')
    return (f"| {n} | {a['pss_alto']:.3f} | {b['pss_alto']:.3f} | {d['media']:+.3f} [{d['ic95'][0]:+.3f}, {d['ic95'][1]:+.3f}] {sig} | "
            f"{a['pss_muyalto']:.3f} | {b['pss_muyalto']:.3f} | {a['auc']:.3f} | {b['auc']:.3f} | {a['alarma']:.0%} | {b['alarma']:.0%} | {a['n_eventos']} |")
H_ = '| | PSS ≥Alto v3 | v4 | Δ [IC 95 %] | PSS ≥Muy alto v3 | v4 | AUC v3 | v4 | alarma v3 | v4 | días fuertes |\n|---|---|---|---|---|---|---|---|---|---|---|'
L = ['# Semáforo FWI v3 vs v4.1 — fuera de muestra 2022-01 → 2026-10 (provincia-día, clase de la peor zona)\n',
     f"Subregiones v4: {res['subregiones_v4']} · fusiones por muestra: {res['fusion_v4'] or 'ninguna'}",
     f"Días fuertes de calibración v4: {res['fuertes_v4']}\n", f"Cortes v3: {res['cortes_v3']}", f"Cortes v4: {res['cortes_v4']}\n",
     '## Regiones (criterio de aceptación)\n', H_] + [fila(k, v) for k, v in res['grupos'].items()] + ['\n## Provincias\n', H_] + [fila(k, v) for k, v in res['provincias'].items()]
open(f'{AQ}/data/evaluacion_fwi.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L[:14]))
print('\nDiagnóstico 2×2 (PSS ≥Alto fuera de muestra):')
G = list(GRUPOS)
print('variante | ' + ' | '.join(G))
print('v3 zonas + subs producción | ' + ' | '.join(f"{res['grupos'][g]['oos_v3']['pss_alto']:.3f}" for g in G))
for nom in EX: print(nom + ' | ' + ' | '.join(f"{res['diagnostico_2x2'][nom][g]:.3f} {res['diagnostico_2x2'][nom][g + '_dif_ic95']}" for g in G), res['diagnostico_2x2'][nom]['_subregiones'], res['diagnostico_2x2'][nom]['_fusion'])
print('v4 zonas + subs R5b | ' + ' | '.join(f"{res['grupos'][g]['oos_v4']['pss_alto']:.3f}" for g in G))
