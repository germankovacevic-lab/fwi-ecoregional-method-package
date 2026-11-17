#!/usr/bin/env python3
"""Auditoría de zonas de fuego — paso 2: ¿cada zona representa un régimen de fuego real? ¿falta alguno?

Para cada provincia (zonas de producción, worker/src/calibracion_3.0_argentina.json) mide sobre los focos
VIIRS 2012–2024 SIN fuentes fijas, asignando cada foco a la zona más cercana (= asignación de Lloyd):
  · contaminación: % de focos de la zona que son fuente fija (antorcha/industria)
  · ecorregión: dominante de la zona y su pureza; ecorregión donde cae el centroide
  · dispersión: distancia p50/p90 de los focos al centroide (km) — un solo punto ERA5 para todo eso
  · concentración: % de la zona aportado por el año más fuerte y por el "evento" más fuerte (celda 0,25° × mes)
  · estacionalidad: mes pico y correlación del perfil mensual entre zonas
  · redundancia: pares de zonas con DC ERA5 diario casi idéntico (r) y misma ecorregión
  · huecos: ecorregiones con ≥ 5 % de los focos de la provincia que ninguna zona representa
Propuesta borrador (para discutir, no se aplica): una zona por régimen = ecorregión dentro de la provincia con
≥ 5 % de sus focos limpios; si el régimen es extenso (p90 > 150 km) se parte en 2–3 con k-means ponderado.
Salidas: data/auditoria.json, data/auditoria.md
"""
import json, os, math
import numpy as np

H = os.path.expanduser
AQ = os.path.dirname(os.path.abspath(__file__))
F = np.load(f'{AQ}/data/focos.npz')
lat, lon, prov, eco, fija = F['lat'].astype(float), F['lon'].astype(float), F['prov'], F['eco'], F['fija']
fecha = F['fecha']
pn, en = list(F['pnames']), list(F['enames'])
anio = np.array([int(s[:4]) for s in fecha]); mes = np.array([int(s[5:7]) for s in fecha])
CAL = json.load(open(f'{AQ}/../../worker/src/calibracion_3.0_argentina.json'))['zonas']
FWI = H('~/.openclaw/data/gfi_v2_fwi_cds')

def km(a1, o1, a2, o2):
    a1, o1, a2, o2 = map(np.radians, (a1, o1, a2, o2))
    h = np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin((o2 - o1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))

def dc(zid):
    p = f'{FWI}/fwi_{zid}.csv'
    if not os.path.exists(p): return None
    d = {}
    for ln in open(p).read().split('\n')[1:]:
        c = ln.split(',')
        if len(c) > 3 and c[3]: d[c[0]] = float(c[3])
    return d

def kmeans_w(la, lo, w, k):
    """k-means ponderado determinista (init farthest-point ponderado, como 01_zonas_fuego.mjs)."""
    o = np.lexsort((lo, la, -w)); la, lo, w = la[o], lo[o], w[o]
    C = [(la[0], lo[0])]
    while len(C) < k:
        d = np.min([(la - a) ** 2 + (lo - b) ** 2 for a, b in C], axis=0)
        i = int(np.argmax(w * d)); C.append((la[i], lo[i]))
    C = np.array(C)
    for _ in range(100):
        a = np.argmin([(la - c[0]) ** 2 + (lo - c[1]) ** 2 for c in C], axis=0)
        N = np.array([[np.average(la[a == g], weights=w[a == g]), np.average(lo[a == g], weights=w[a == g])] if w[a == g].sum() > 0 else C[g] for g in range(k)])
        if np.allclose(N, C): break
        C = N
    a = np.argmin([(la - c[0]) ** 2 + (lo - c[1]) ** 2 for c in C], axis=0)
    inv = np.empty_like(o); inv[o] = np.arange(len(o))
    return C, a[inv]

def grilla(la, lo, cel=0.1):
    """Agrupa focos en celdas (para k-means rápido): devuelve centros, pesos, índice de celda por foco."""
    key = np.floor(la / cel).astype(np.int64) * 100000 + np.floor(lo / cel).astype(np.int64)
    u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    cla = np.bincount(inv, la) / cnt; clo = np.bincount(inv, lo) / cnt
    return cla, clo, cnt.astype(float), inv

def perfil(m):
    p = np.bincount(m, minlength=13)[1:].astype(float)
    return p / p.sum() if p.sum() else p

R = {}
for pi, P in enumerate(pn):
    Z = CAL.get(P) or []
    sel = (prov == pi)
    n_tot = int(sel.sum())
    limpio = sel & ~fija
    la, lo, ec, an, ms = lat[limpio], lon[limpio], eco[limpio], anio[limpio], mes[limpio]
    n_l = len(la)
    if not Z or n_l == 0:
        R[P] = dict(n_total=n_tot, n_limpio=n_l, zonas=[], nota='sin zonas'); continue
    zl = np.array([z['lat'] for z in Z]); zo = np.array([z['lon'] for z in Z])
    # asignación de TODOS los focos (con fijas) a la zona más cercana
    la_all, lo_all, fj_all = lat[sel], lon[sel], fija[sel]
    a_all = np.argmin([(la_all - a) ** 2 + (lo_all - b) ** 2 for a, b in zip(zl, zo)], axis=0)
    a = np.argmin([(la - x) ** 2 + (lo - y) ** 2 for x, y in zip(zl, zo)], axis=0)
    # ecorregión del centroide (la del foco limpio más cercano dentro de 10 km; si no, la del más cercano)
    zonas = []
    perfiles = []
    dcs = []
    for g, z in enumerate(Z):
        m = a == g
        n = int(m.sum())
        zid = f"{z['lat']:.2f}_{z['lon']:.2f}"
        fj = float(fj_all[a_all == g].mean()) if (a_all == g).any() else 0
        if n == 0:
            zonas.append(dict(zid=zid, peso=z['peso'], n_limpio=0, fijas_pct=round(100 * fj, 1))); perfiles.append(np.zeros(12)); dcs.append(dc(zid)); continue
        d = km(la[m], lo[m], z['lat'], z['lon'])
        ecz = np.bincount(ec[m], minlength=len(en)); e0 = int(ecz.argmax())
        dd = km(la, lo, z['lat'], z['lon']); ic = int(dd.argmin())
        yr = np.bincount(an[m] - 2012, minlength=13)
        ev = np.unique(np.floor(la[m] / .25).astype(int) * 10**7 + np.floor(lo[m] / .25).astype(int) * 1000 + (an[m] - 2000) * 12 + ms[m], return_counts=True)[1]
        pf = perfil(ms[m]); perfiles.append(pf); dcs.append(dc(zid))
        zonas.append(dict(
            zid=zid, peso=z['peso'], n_limpio=n, share_limpio=round(n / n_l, 3), fijas_pct=round(100 * fj, 1),
            eco=en[e0], eco_pureza=round(ecz[e0] / n, 2), eco_centroide=en[ec[ic]], dist_foco_mas_cercano_km=round(float(dd[ic]), 1),
            focos_15km=int((dd < 15).sum()),
            r50_km=round(float(np.median(d)), 0), r90_km=round(float(np.percentile(d, 90)), 0),
            anio_top=int(2012 + yr.argmax()), anio_top_pct=round(100 * yr.max() / n, 0),
            evento_top_pct=round(100 * ev.max() / n, 0), mes_pico=int(pf.argmax() + 1)))
    # redundancia entre pares
    pares = []
    for i in range(len(Z)):
        for j in range(i + 1, len(Z)):
            d_ij = float(km(zl[i], zo[i], zl[j], zo[j]))
            rs = float(np.corrcoef(perfiles[i], perfiles[j])[0, 1]) if perfiles[i].sum() and perfiles[j].sum() else None
            rd = None
            if dcs[i] and dcs[j]:
                k = sorted(set(dcs[i]) & set(dcs[j]))
                if len(k) > 1000: rd = float(np.corrcoef([dcs[i][x] for x in k], [dcs[j][x] for x in k])[0, 1])
            pares.append(dict(a=Z[i] and zonas[i]['zid'], b=zonas[j]['zid'], km=round(d_ij), r_estacion=None if rs is None else round(rs, 2), r_dc=None if rd is None else round(rd, 3),
                              misma_eco=zonas[i].get('eco') == zonas[j].get('eco')))
    # ecorregiones de la provincia
    ecp = np.bincount(ec, minlength=len(en))
    regs = []
    for e in np.argsort(-ecp):
        if ecp[e] == 0: break
        sh = ecp[e] / n_l
        m = ec == e
        # qué zonas cubren esta ecorregión
        cov = np.bincount(a[m], minlength=len(Z)) / m.sum()
        dueña = [zonas[g]['zid'] for g in range(len(Z)) if zonas[g].get('eco') == en[e]]
        regs.append(dict(eco=en[e], share=round(float(sh), 3), n=int(ecp[e]), zonas_propias=dueña, mes_pico=int(perfil(ms[m]).argmax() + 1),
                         repartida_en={zonas[g]['zid']: round(float(cov[g]), 2) for g in np.argsort(-cov)[:3] if cov[g] > 0.05}))
    huecos = [r for r in regs if r['share'] >= 0.05 and not r['zonas_propias']]
    # propuesta borrador: régimen = ecorregión ≥ 5 % (o la mayor si ninguna), partida si es extensa
    prop = []
    for r in regs:
        if r['share'] < 0.05 and prop: continue
        e = en.index(r['eco']); m = ec == e
        cla, clo, w, inv = grilla(la[m], lo[m])
        best = None
        for k in (1, 2, 3):
            if k > len(w): break
            C, ac = kmeans_w(cla, clo, w, k)
            parts = []
            for g in range(k):
                mm = ac[inv] == g
                if not mm.any(): continue
                d = km(la[m][mm], lo[m][mm], C[g][0], C[g][1])
                parts.append(dict(lat=round(float(C[g][0]), 2), lon=round(float(C[g][1]), 2), n=int(mm.sum()), share=round(float(mm.sum() / n_l), 3),
                                  r90_km=round(float(np.percentile(d, 90))), mes_pico=int(perfil(ms[m][mm]).argmax() + 1)))
            if best is not None and min(p['share'] for p in parts) < 0.05: break
            best = parts
            if max(p['r90_km'] for p in parts) <= 150: break
        for p in best: p['eco'] = r['eco']
        prop += best
    tot = sum(p['n'] for p in prop)
    for p in prop: p['peso_en_propuesta'] = round(p['n'] / tot, 3)
    R[P] = dict(n_total=n_tot, n_limpio=n_l, fijas_pct=round(100 * (1 - n_l / n_tot), 1), zonas=zonas, pares=pares, ecorregiones=regs,
                huecos=huecos, propuesta=prop, cobertura_propuesta=round(tot / n_l, 3))

json.dump(R, open(f'{AQ}/data/auditoria.json', 'w'), ensure_ascii=False, indent=1)

# ---- informe markdown con banderas
L = ['# Auditoría de zonas de fuego — 23 jurisdicciones (TDF ya rehecha)\n',
     'Focos VIIRS S-NPP 2012–2024 (conf≠l, type 0), sin fuentes fijas; ecorregiones oficiales (Ministerio de Ambiente 2021).\n',
     'Banderas: **FIJ** ≥ 15 % fuente fija · **EVT** evento (celda 0,25°×mes) ≥ 25 % de la zona · **AÑO** un año ≥ 50 % · '
     '**EXT** p90 > 150 km · **MEZ** pureza de ecorregión < 60 % · **VAC** centroide sin focos a < 15 km · '
     '**FLA** < 2 % de los focos limpios de la provincia · **RED** par con DC r ≥ 0,985 y misma ecorregión · **HUECO** ecorregión ≥ 5 % sin zona propia\n']
for P in pn:
    if P.startswith('Tierra del Fuego'): continue
    r = R[P]
    if not r['zonas']: continue
    L.append(f"\n## {P} — {len(r['zonas'])} zonas hoy → {len(r['propuesta'])} en la propuesta borrador\n")
    L.append(f"{r['n_total']:,} focos · {r['fijas_pct']} % fuente fija\n")
    L.append('| zona | peso | % limpio | ecorregión (pureza) | centroide cae en | r50/r90 km | pico | año top | evento top | banderas |')
    L.append('|---|---|---|---|---|---|---|---|---|---|')
    red = {p['a'] for p in r['pares'] if p['r_dc'] and p['r_dc'] >= .985 and p['misma_eco']} | {p['b'] for p in r['pares'] if p['r_dc'] and p['r_dc'] >= .985 and p['misma_eco']}
    for z in r['zonas']:
        if not z.get('n_limpio'):
            L.append(f"| {z['zid']} | {z['peso']} | 0 | — | — | — | — | — | — | VACÍA |"); continue
        b = []
        if z['fijas_pct'] >= 15: b.append('FIJ')
        if z['evento_top_pct'] >= 25: b.append('EVT')
        if z['anio_top_pct'] >= 50: b.append('AÑO')
        if z['r90_km'] > 150: b.append('EXT')
        if z['eco_pureza'] < .6: b.append('MEZ')
        if z['focos_15km'] == 0: b.append('VAC')
        if z['share_limpio'] < .02: b.append('FLA')
        if z['zid'] in red: b.append('RED')
        z['banderas'] = b
        L.append(f"| {z['zid']} | {z['peso']} | {round(100*z['share_limpio'])} % | {z['eco']} ({round(100*z['eco_pureza'])} %) | {z['eco_centroide']} | {int(z['r50_km'])}/{int(z['r90_km'])} | {z['mes_pico']} | {z['anio_top']} ({int(z['anio_top_pct'])} %) | {int(z['evento_top_pct'])} % | {' '.join(b)} |")
    L.append('\nEcorregiones: ' + ' · '.join(f"{e['eco']} {round(100*e['share'])} %" + ('' if e['zonas_propias'] else ' (sin zona propia)') for e in r['ecorregiones'] if e['share'] >= .02))
    rp = [p for p in r['pares'] if p['r_dc'] and p['r_dc'] >= .985]
    if rp: L.append('\nPares con DC casi idéntico: ' + ' · '.join(f"{p['a']}↔{p['b']} r={p['r_dc']} {p['km']} km{' misma eco' if p['misma_eco'] else ''}" for p in rp))
    if r['huecos']: L.append('\n**HUECO:** ' + ', '.join(f"{h['eco']} ({round(100*h['share'])} %, pico mes {h['mes_pico']})" for h in r['huecos']))
    L.append('\nPropuesta borrador: ' + ' · '.join(f"{p['eco']} ({p['lat']},{p['lon']}) {round(100*p['share'])} % r90 {p['r90_km']} km" for p in r['propuesta']) + f" — cubre {round(100*r['cobertura_propuesta'])} % de los focos")
    R[P] = r
json.dump(R, open(f'{AQ}/data/auditoria.json', 'w'), ensure_ascii=False, indent=1)
open(f'{AQ}/data/auditoria.md', 'w').write('\n'.join(L) + '\n')
print('ok', sum(len(R[p]['propuesta']) for p in pn if R[p].get('propuesta')), 'zonas en la propuesta')
