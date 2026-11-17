#!/usr/bin/env python3
"""R5c — Semáforo FWI por ecorregión (E1 FWI ecorregional único, E2 umbral ecorregional con FWI local) vs producción.
Reglas en docs/REGLAS_ZONAS_v4.md §R5c (registradas antes de correr). Misma evaluación que 15_evaluacion_fwi.py.
Salida: data/evaluacion_fwi_ecorregional.json / .md"""
import json, os, sys, unicodedata
import numpy as np, pandas as pd
AQ = os.path.dirname(os.path.abspath(__file__))
src = open(f'{AQ}/15_evaluacion_fwi.py').read()
g = {'__file__': f'{AQ}/15_evaluacion_fwi.py', '__name__': 'x'}
exec(compile(src[:src.index("E3, E4 = evaluar('v3'), evaluar('v4')")], '15', 'exec'), g)
for k in ('np', 'pd', 'DIAS', 'CAL_FIN', 'OOS_INI', 'PROVS', 'REGION', 'EVP', 'met', 'evaluar', 'R5B', 'FALLBACK', 'nrm',
          'lat', 'lon', 'prov', 'fecha', 'pn', 'hav', 'conteo_diario', 'ok', 'H'):
    globals()[k] = g[k]
eco_all = g['g']['eco'][ok]; EN = g['g']['en']
eco_n = np.array([nrm(EN[e]) for e in eco_all])

E3 = evaluar('v3')
Zj = json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas']
Z = [dict(P=P, zid=z['zid'], lat=z['lat'], lon=z['lon'], eco=nrm(z['regimen'])) for P, v in Zj.items() for z in v if P in PROVS]
FWI = {z['zid']: pd.read_csv(H(f"~/.openclaw/data/gfi_v4_fwi_worker/fwi_{z['zid']}.csv")).set_index('date')['fwi'].reindex(DIAS.strftime('%Y-%m-%d')).values for z in Z}
calm = np.asarray(DIAS <= CAL_FIN)

# focos limpios → zona más cercana de su provincia: peso del punto y días fuertes del punto
W, FZ = {}, {}
for P in PROVS:
    zs = [z for z in Z if z['P'] == P]; ii = np.where(prov == pn.index(P))[0]
    a = np.stack([hav(lat[ii], lon[ii], z['lat'], z['lon']) for z in zs]).argmin(0)
    for k, z in enumerate(zs):
        c = conteo_diario(ii[a == k]); cal = c[calm & (c > 0)]
        W[z['zid']] = float(c[calm].sum())
        FZ[z['zid']] = (c >= np.percentile(cal, 90)) & (c > 0) if len(cal) >= 10 else np.zeros(len(DIAS), bool)
ECOS = sorted({z['eco'] for z in Z})
pts = {e: [z['zid'] for z in Z if z['eco'] == e] for e in ECOS}

def media_pond(ids):
    X = np.stack([FWI[i] for i in ids]); w = np.array([W[i] for i in ids])[:, None] * ~np.isnan(X)
    return np.where(w.sum(0) > 0, np.nansum(np.nan_to_num(X) * w, 0) / np.maximum(w.sum(0), 1e-9), np.nan)

# E1: FWI ecorregional y días fuertes de la ecorregión entera
FE = {e: media_pond(pts[e]) for e in ECOS}
FD = {}
for e in ECOS:
    c = conteo_diario(np.where(eco_n == e)[0]); cal = c[calm & (c > 0)]
    FD[e] = (c >= np.percentile(cal, 90)) & (c > 0)

def cortes_con_respaldo(muestras):
    """muestras[e] = (valores FWI en días fuertes de calibración). < 300 → grupo R5b → respaldo R5b."""
    def pool(gname):
        v = [muestras[x] for x in ECOS if R5B[x] == gname]
        return np.concatenate(v) if v else np.array([])
    out, origen = {}, {}
    for e in ECOS:
        if len(muestras[e]) >= 300: out[e] = muestras[e]; origen[e] = e; continue
        gname = R5B[e]; p = pool(gname)
        while len(p) < 300 and gname in FALLBACK:
            gname = FALLBACK[gname]; p = pool(gname)
        out[e] = p; origen[e] = gname
    return {e: [round(float(q), 1) for q in np.percentile(v[~np.isnan(v)], [10, 25, 50, 75])] for e, v in out.items()}, origen, {e: int(len(muestras[e])) for e in ECOS}

m1 = {e: FE[e][FD[e] & calm] for e in ECOS}
C1, O1, N1 = cortes_con_respaldo(m1)
m2 = {e: np.concatenate([FWI[i][FZ[i] & calm] for i in pts[e]]) for e in ECOS}
C2, O2, N2 = cortes_con_respaldo(m2)

def lvl(x, c): return np.where(np.isnan(x), np.nan, np.digitize(np.nan_to_num(x), c))

# peso de cada ecorregión en cada provincia (focos limpios de calibración)
WP = {}
cal_dias = set(DIAS[calm])
fcal = np.asarray(fecha <= CAL_FIN)
for P in PROVS:
    m = (prov == pn.index(P)) & fcal
    c = pd.Series(eco_n[m]).value_counts()
    WP[P] = {e: float(v) for e, v in c.items() if e in ECOS}

def provincia(nivel_eco_prov):
    out = {}
    for P in PROVS:
        num = np.zeros(len(DIAS)); den = np.zeros(len(DIAS))
        for e, w in WP[P].items():
            l = nivel_eco_prov(P, e)
            v = ~np.isnan(l); num[v] += w * l[v]; den[v] += w
        out[P] = np.where(den > 0, np.floor(num / np.maximum(den, 1e-9) + 0.5), -1)
    return pd.DataFrame(out, index=DIAS)

L1 = {e: lvl(FE[e], C1[e]) for e in ECOS}
NP1 = provincia(lambda P, e: L1[e])
LZ = {z['zid']: lvl(FWI[z['zid']], C2[z['eco']]) for z in Z}
def e2(P, e):
    ids = [z['zid'] for z in Z if z['eco'] == e and z['P'] == P] or pts[e]   # sin punto propio: los puntos nacionales
    X = np.stack([LZ[i] for i in ids]); w = np.array([W[i] for i in ids])[:, None] * ~np.isnan(X)
    return np.where(w.sum(0) > 0, np.nansum(np.nan_to_num(X) * w, 0) / np.maximum(w.sum(0), 1e-9), np.nan)
NP2 = provincia(e2)

# DIAGNÓSTICO (no es una variante candidata): producción con la provincia como promedio ponderado por fuego de sus
# zonas en vez de la peor zona — separa el efecto de la agregación del efecto de la ecorregión
def prom_zonas(E):
    Wz = {}
    for P in PROVS:
        zs = [z for z in E['Z'] if z['P'] == P]; ii = np.where(prov == pn.index(P))[0]
        a = np.stack([hav(lat[ii], lon[ii], z['lat'], z['lon']) for z in zs]).argmin(0)
        for k, z in enumerate(zs): Wz[z['zid']] = float(((a == k) & np.asarray(fecha[ii] <= CAL_FIN)).sum())
    out = {}
    for P in PROVS:
        ids = [z['zid'] for z in E['Z'] if z['P'] == P]
        X = np.stack([E['nivel'][i] for i in ids]).astype(float); X[X < 0] = np.nan
        w = np.array([Wz[i] for i in ids])[:, None] * ~np.isnan(X)
        out[P] = np.where(w.sum(0) > 0, np.floor(np.nansum(np.nan_to_num(X) * w, 0) / np.maximum(w.sum(0), 1e-9) + 0.5), -1)
    return pd.DataFrame(out, index=DIAS)
NPd3 = prom_zonas(E3)
NPd4 = prom_zonas(evaluar('v4'))
oos = np.asarray(DIAS >= OOS_INI); meses = DIAS[oos].to_period('M'); um = meses.unique()
rng = np.random.default_rng(20261117)
GRUPOS = {'País': PROVS}
for P in PROVS: GRUPOS.setdefault(REGION[P], []).append(P)
res = dict(cortes_E1=C1, origen_E1=O1, dias_fuertes_E1=N1, cortes_E2=C2, origen_E2=O2, dias_fuertes_E2=N2, tabla={})
def boot(LX, L3, Y):
    bl = [np.where(meses == m)[0] for m in um]; d = []
    for _ in range(2000):
        ix = np.concatenate([bl[k] for k in rng.integers(0, len(bl), len(bl))])
        def p(L):
            l, y = L[ix].ravel(), Y[ix].ravel(); v = l >= 0; l, y = l[v], y[v]; a = l >= 2
            return (a & y).sum() / max(y.sum(), 1) - (a & ~y).sum() / max((~y).sum(), 1)
        d.append(p(LX) - p(L3))
    return [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)]
for gname, ps in list(GRUPOS.items()) + [(P, [P]) for P in PROVS]:
    ev = EVP[ps]; r = {}
    r['v3'] = met(E3['NP'][ps], ev, oos)
    for nom, NP in (('E1', NP1), ('E2', NP2), ('D3', NPd3), ('D4', NPd4)):
        r[nom] = met(NP[ps], ev, oos); r[nom]['dif_ic95'] = boot(NP[ps].values[oos], E3['NP'][ps].values[oos], ev.values[oos])
    res['tabla'][gname] = r
json.dump(res, open(f'{AQ}/data/evaluacion_fwi_ecorregional.json', 'w'), ensure_ascii=False, indent=1)
def s(r, k):
    d = r[k]['dif_ic95']; sig = '✅' if d[0] > 0 else ('❌' if d[1] < 0 else '≈')
    return f"{r[k]['pss_alto']:.3f} ({r[k]['pss_alto'] - r['v3']['pss_alto']:+.3f} [{d[0]:+.3f}, {d[1]:+.3f}] {sig}) · alarma {r[k]['alarma']:.0%}"
Ls = ['# Semáforo FWI por ecorregión (R5c) vs producción — fuera de muestra 2022-01 → 2026-10\n',
      f'Cortes E1: {C1}', f'Origen E1: {O1}', f'Días fuertes E1: {N1}', f'Cortes E2: {C2}', f'Origen E2: {O2}\n',
      '| | producción PSS ≥Alto · alarma | E1 ecorregional único | E2 umbral ecorregional, FWI local | diag: producción con promedio ponderado | diag: v4.1 (R5b) con promedio ponderado |', '|---|---|---|---|---|---|']
for gname, r in res['tabla'].items():
    Ls.append(f"| {gname} | {r['v3']['pss_alto']:.3f} · {r['v3']['alarma']:.0%} | {s(r, 'E1')} | {s(r, 'E2')} | {s(r, 'D3')} | {s(r, 'D4')} |")
open(f'{AQ}/data/evaluacion_fwi_ecorregional.md', 'w').write('\n'.join(Ls) + '\n')
print('\n'.join(Ls[:14]))

# E1 contra el diagnóstico D3 (¿cuánto agrega la ecorregión por encima del cambio de agregación?)
print('\nE1 − D3 (PSS ≥Alto, IC 95 %):')
res['E1_vs_D3'] = {}
for gname, ps in GRUPOS.items():
    ev = EVP[ps]
    ic = boot(NP1[ps].values[oos], NPd3[ps].values[oos], ev.values[oos])
    d = met(NP1[ps], ev, oos)['pss_alto'] - met(NPd3[ps], ev, oos)['pss_alto']
    res['E1_vs_D3'][gname] = dict(dif=round(d, 3), ic95=ic); print(f'  {gname}: {d:+.3f} {ic}')
json.dump(res, open(f'{AQ}/data/evaluacion_fwi_ecorregional.json', 'w'), ensure_ascii=False, indent=1)
