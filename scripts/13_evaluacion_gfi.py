#!/usr/bin/env python3
"""Paso 4 — término de sequía del GFI: calibración R6 y evaluación 2×2 (REGLAS_ZONAS_v4 R6/R7, METODO_v4 §6.2/§7).

Variantes (provincia-mes, 2012–2024, 23 provincias; CABA no aplica):
  A  zonas v3 (producción, 115) · regla v3: escala si alguna zona tiene DC30 de fin de mes > su umbral mensual
     (11.º menor de 13; los umbral_dc de calibracion_3.0_argentina.json)
  B  zonas v4.1 (90)            · regla v3 (umbral 11.º de 13 recalculado igual para cada zona v4)
  C  zonas v3                   · regla R6: S = máx de percentiles zonales (DC30 vs todos los días del mes 2012–2024);
                                   escala si S > T_P, T_P tal que la provincia escala el 15,4 % de los meses
  D  zonas v4.1                 · regla R6
Evento: focos limpios (R1 v4) de la provincia en el mes > mediana de ese mes calendario en la provincia (2012–2024).
Métricas: tasa de escalación, precisión, POD, POFD, Peirce = POD − POFD; IC 95 % por bootstrap de años (2000);
dejando un año afuera (R6: T_P sin ese año; regla v3: umbral 11.º de los 12 restantes); Delta Entre Ríos ago-2020;
regla nacional (≥ 16 de 23 provincias escaladas el mismo mes).
Salida: data/evaluacion_gfi.json, data/evaluacion_gfi.md
"""
import json, os, sys, glob
import numpy as np, pandas as pd
H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
REPO = f'{AQ}/../..'
TASA = 0.154
ANIOS = list(range(2012, 2025))

# ---------- focos limpios R1 v4 por provincia-mes (reutiliza 07 hasta R1)
sys.argv = ['07', '--split5', '--piso=50']
src = open(f'{AQ}/07_zonas_v4.py').read()
g = {'__file__': f'{AQ}/07_zonas_v4.py', '__name__': 'x'}
exec(compile(src[:src.index('# ---------- R2/R3/R4 por provincia')], '07', 'exec'), g)
df, prov, fija, pn = g['df'], g['prov'], g['fija'], g['pn']
ym = pd.PeriodIndex(df.acq_date.str[:7].values, freq='M')
F = pd.DataFrame({'p': np.array(pn)[prov], 'm': ym})[~fija].value_counts().unstack(0).fillna(0)
MESES = pd.period_range('2012-01', '2024-12', freq='M')
F = F.reindex(MESES).fillna(0)
PROVS = [p for p in pn if not p.startswith('Ciudad')]
med = F.groupby(F.index.month).transform('median')
EV = (F > med)[PROVS]

# ---------- DC30 de fin de mes y percentiles diarios por zona
def serie(path):
    d = pd.read_csv(path); d = d.set_index(pd.to_datetime(d[d.columns[0]]))['dc']
    return d.rolling(30, min_periods=25).mean()
def zonas_v3():
    c = json.load(open(f'{REPO}/worker/src/calibracion_3.0_argentina.json'))['zonas']
    out = {}
    for P, v in c.items():
        for z in v:
            zid = f"{z['lat']:.2f}_{z['lon']:.2f}"
            p = H(f'~/.openclaw/data/gfi_v2_fwi_cds/fwi_{zid}.csv')
            if not os.path.exists(p): p = H(f'~/.openclaw/workspace/tmp/tdf4/fwi/fwi_{zid}.csv')
            out.setdefault(P, []).append((zid, p, z.get('umbral_dc')))
    return out
def zonas_v4():
    c = json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas']
    return {P: [(z['zid'], H(f"~/.openclaw/data/gfi_v4_fwi_cds/fwi_{z['zid']}.csv"), None) for z in v] for P, v in c.items()}

def preparar(Z):
    R = {}
    for P in PROVS:
        fin, pct = {}, {}
        for zid, path, umb in Z[P]:
            d30 = serie(path)
            d30 = d30[(d30.index.year >= 2012) & (d30.index.year <= 2024)]
            m = d30.resample('ME').last(); m.index = m.index.to_period('M')
            fin[zid] = (m.reindex(MESES), umb)
            # percentil del valor de fin de mes dentro de todos los días de ese mes calendario 2012–2024
            ref = {k: np.sort(d30[d30.index.month == k].dropna().values) for k in range(1, 13)}
            pct[zid] = pd.Series([np.searchsorted(ref[p.month], v, side='right') / len(ref[p.month]) if pd.notna(v) else np.nan
                                  for p, v in m.reindex(MESES).items()], index=MESES)
        R[P] = (fin, pd.DataFrame(pct))
    return R

def umbral_11(s, excl=None):
    """11.º menor de 13 por mes calendario (con excl: 11.º de 12, la regla aplicada sin ese año → mismo rango relativo)."""
    out = {}
    for k in range(1, 13):
        v = s[(s.index.month == k) & ((s.index.year != excl) if excl else True)].dropna().values
        v = np.sort(v)
        out[k] = v[min(10, len(v) - 1) if excl is None else min(int(round(10 / 13 * len(v))), len(v) - 1)] if len(v) else np.nan
    return out

def escala_v3(R, usar_prod, excl=None):
    E = pd.DataFrame(False, index=MESES, columns=PROVS)
    for P in PROVS:
        fin, _ = R[P]
        for zid, (s, umb) in fin.items():
            if usar_prod and umb and excl is None:
                u = {k + 1: umb[k] for k in range(12)}
            else:
                u = umbral_11(s, excl)
            E[P] |= s.round(2) > s.index.month.map(u).values
    return E

def escala_r6(R, excl=None):
    E = pd.DataFrame(False, index=MESES, columns=PROVS); T = {}
    for P in PROVS:
        # máximo de percentiles; empates (saturación en 1,0) se desempatan por el promedio de percentiles de las zonas
        S = R[P][1].max(axis=1) + 1e-3 * R[P][1].mean(axis=1)
        cal = S[S.index.year != excl] if excl else S
        tp = np.nanquantile(cal.values, 1 - TASA)
        T[P] = float(tp); E[P] = S > tp
    return E, T

def metricas(E, ev, years=None):
    if years is not None:
        idx = [m for y in years for m in MESES if m.year == y]
        E, ev = E.loc[idx], ev.loc[idx]
    e, o = E.values.ravel(), ev.values.ravel()
    tp, fp, fn, tn = (e & o).sum(), (e & ~o).sum(), (~e & o).sum(), (~e & ~o).sum()
    pod = tp / max(tp + fn, 1); pofd = fp / max(fp + tn, 1)
    return dict(tasa=float(e.mean()), precision=float(tp / max(tp + fp, 1)), pod=float(pod), pofd=float(pofd), peirce=float(pod - pofd), base=float(o.mean()))

R3, R4 = preparar(zonas_v3()), preparar(zonas_v4())
V = {'A': escala_v3(R3, True), 'B': escala_v3(R4, False)}
V['C'], T3 = escala_r6(R3); V['D'], T4 = escala_r6(R4)
# dejando un año afuera: para cada año, la regla calibrada sin ese año evaluada en ese año
L = {k: pd.DataFrame(False, index=MESES, columns=PROVS) for k in 'ABCD'}
for y in ANIOS:
    sel = MESES.year == y
    L['A'][sel] = escala_v3(R3, False, y)[sel]; L['B'][sel] = escala_v3(R4, False, y)[sel]
    L['C'][sel] = escala_r6(R3, y)[0][sel];    L['D'][sel] = escala_r6(R4, y)[0][sel]
EVb = EV.astype(bool)
rng = np.random.default_rng(20261117)
res = {}
for k in 'ABCD':
    res[k] = dict(in_sample=metricas(V[k], EVb), loyo=metricas(L[k], EVb),
                  tasa_por_provincia={P: round(float(V[k][P].mean()), 3) for P in PROVS},
                  nacional_meses=int((V[k].sum(axis=1) >= 16).sum()),
                  delta_ER_ago2020=bool(V[k].loc[pd.Period('2020-08', 'M'), 'Entre Ríos']))
# bootstrap de años: diferencias de Peirce (LOYO) respecto de A
boot = {k: [] for k in 'BCD'}
for _ in range(2000):
    ys = list(rng.choice(ANIOS, len(ANIOS), replace=True))
    pa = metricas(L['A'], EVb, ys)['peirce']
    for k in 'BCD': boot[k].append(metricas(L[k], EVb, ys)['peirce'] - pa)
for k in 'BCD':
    res[k]['dif_peirce_vs_A_loyo'] = dict(media=float(np.mean(boot[k])), ic95=[float(np.percentile(boot[k], 2.5)), float(np.percentile(boot[k], 97.5))])
for k in 'ABCD':
    b = [metricas(L[k], EVb, list(rng.choice(ANIOS, len(ANIOS), replace=True)))['peirce'] for _ in range(2000)]
    res[k]['peirce_loyo_ic95'] = [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]
res['T_P'] = {'v3': T3, 'v4': T4}
json.dump(res, open(f'{AQ}/data/evaluacion_gfi.json', 'w'), ensure_ascii=False, indent=1)

N = {'A': 'zonas v3 · regla v3 (PRODUCCIÓN)', 'B': 'zonas v4.1 · regla v3', 'C': 'zonas v3 · regla R6', 'D': 'zonas v4.1 · regla R6 (PROPUESTA)'}
L_ = ['# Evaluación del término de sequía del GFI — 2×2 (provincia-mes 2012–2024, 23 provincias)\n',
      f"Evento: focos limpios del mes > mediana del mes calendario de la provincia (tasa base {res['A']['in_sample']['base']:.1%}).\n",
      '| variante | tasa escalación | precisión | POD | POFD | Peirce (in) | Peirce LOYO [IC 95 %] | Δ Peirce vs A (LOYO) [IC 95 %] | meses regla nacional | Delta ER ago-2020 |',
      '|---|---|---|---|---|---|---|---|---|---|']
for k in 'ABCD':
    r = res[k]; i, l = r['in_sample'], r['loyo']
    d = r.get('dif_peirce_vs_A_loyo')
    L_.append(f"| **{k}** {N[k]} | {i['tasa']:.1%} | {i['precision']:.1%} | {i['pod']:.1%} | {i['pofd']:.1%} | {i['peirce']:.3f} | {l['peirce']:.3f} [{r['peirce_loyo_ic95'][0]:.3f}, {r['peirce_loyo_ic95'][1]:.3f}] | "
              + (f"{d['media']:+.3f} [{d['ic95'][0]:+.3f}, {d['ic95'][1]:+.3f}]" if d else '—') + f" | {r['nacional_meses']} | {'sí' if r['delta_ER_ago2020'] else 'no'} |")
L_.append('\n## Tasa de escalación por provincia\n')
L_.append('| provincia | A | B | C | D |'); L_.append('|---|---|---|---|---|')
for P in PROVS: L_.append(f"| {P} | " + ' | '.join(f"{res[k]['tasa_por_provincia'][P]:.0%}" for k in 'ABCD') + ' |')
open(f'{AQ}/data/evaluacion_gfi.md', 'w').write('\n'.join(L_) + '\n')
print('\n'.join(L_[:8]))
