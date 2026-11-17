#!/usr/bin/env python3
"""Zonas de fuego v4: aplica docs/REGLAS_ZONAS_v4.md (firmadas 17/11/2026) al pie de la letra.

R1 fuentes fijas  (a) máscara curada worker/src/fuentes_fijas.json ≤ radio_m
                  (b) celda 0,02° con focos en ≥ 9 meses distintos dentro de una ventana de 12
                  (c) celda 0,02° con focos en ≥ 6 meses distintos y ≤ 1 km de un pozo (SE, Capítulo IV – Pozos)
R2 régimen        ecorregión × provincia con ≥ 5 % de los focos limpios, o ≥ 100 focos y ≥ 2 %
R3 partición      unidad de Oyarzabal 2018 que cumple R2 (sobre el total provincial) → zona propia; si el régimen tiene
                  0 o 1 unidad que cumple, es una sola zona; los focos de unidades que no cumplen van a la zona más
                  cercana del mismo régimen. Islas: masa de tierra (parte del polígono IGN) separada por mar del cuerpo
                  principal (la parte con más focos limpios) → unidad aparte si cumple R2.
R4 centroide      media de los focos limpios; si cae fuera de su zona (otra provincia/ecorregión/unidad/isla) o en una
                  celda 0,1° sin focos limpios → centro de la celda 0,1° más cercana al centroide original entre las del
                  decil superior de focos de la zona. Peso = fracción de focos limpios de la provincia (focos de regímenes
                  sin zona → zona más cercana).
Insumos 2012–2024: archivo FIRMS Argentina (VIIRS S-NPP) + archivo Falkland_Islands (Islas Malvinas → TDF, AeIAS).
Salidas: data/zonas_v4.json · data/zonas_v4_resumen.md
"""
import json, os, glob, collections
import numpy as np, pandas as pd, shapely
from shapely.geometry import shape, Polygon, Point

H = os.path.expanduser
import sys
R3_DOM = '--literal' not in sys.argv
R3_5 = '--split5' in sys.argv
AQ = os.path.dirname(os.path.abspath(__file__))
REPO = f'{AQ}/../..'
TDF = 'Tierra del Fuego, Antártida e Islas del Atlántico Sur'

def hav(a1, o1, a2, o2):
    a1, o1, a2, o2 = map(np.radians, (a1, o1, a2, o2))
    h = np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin((o2 - o1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))

# ---------- focos 2012–2024 (AR + Malvinas)
fr = []
# FOCOS_HASTA=2026 extiende el archivo para la verificación fuera de muestra (las zonas se construyen con 2012–2024)
HASTA = int(os.environ.get('FOCOS_HASTA', 2024))
for y in range(2012, HASTA + 1):
    for src, path in (('ar', f'~/.openclaw/data/firms_ar/viirs_{y}.csv' if y < 2026 else '~/.openclaw/data/firms_ar/viirs_2026_area.csv'),
                      ('fk', f'~/.openclaw/data/firms_malvinas/viirs_{y}.csv')):
        p = H(path)
        if not os.path.exists(p): continue
        d = pd.read_csv(p, usecols=['latitude', 'longitude', 'acq_date', 'confidence', 'type'], dtype={'confidence': str, 'type': str}, on_bad_lines='skip')
        t = d['type'].astype(str).str.strip()
        d = d[(d.confidence != 'l') & ((t == '0') | t.str.startswith('VIIRS_SNPP_NRT')) & d.acq_date.astype(str).str.match(r'^\d{4}-\d\d-\d\d$')][['latitude', 'longitude', 'acq_date']]
        d['src'] = src; fr.append(d)
df = pd.concat(fr, ignore_index=True)
lat, lon = df.latitude.values.astype(float), df.longitude.values.astype(float)
n = len(df)

# ---------- provincia
PR = json.load(open(f'{AQ}/provincias.json'))
pn = [p['n'] for p in PR]
pparts = {p['n']: [Polygon([(x, y) for y, x in r]).buffer(0) for r in p['rings']] for p in PR}
pgeo = [shapely.MultiPolygon([q for q in pparts[p] if q.geom_type == 'Polygon']).buffer(0) for p in pn]
prov = np.full(n, -1, np.int16)
for i, g in enumerate(pgeo):
    shapely.prepare(g); m = (prov < 0) & shapely.contains_xy(g, lon, lat); prov[m] = i
# Malvinas: el polígono IGN simplificado puede no cubrir toda la costa → todo foco del archivo Falkland_Islands es TDF
prov[(df.src.values == 'fk')] = pn.index(TDF)
keep = prov >= 0
df, lat, lon, prov = df[keep].reset_index(drop=True), lat[keep], lon[keep], prov[keep]
n = len(df)

# ---------- ecorregión (terrestre; los focos costeros fuera de polígono → ecorregión terrestre más cercana)
eco_f = [f for f in json.load(open(H('~/.openclaw/data/ecorregiones/eco2021.json')))['features']
         if f['properties']['ecorregion'] not in ('Mar Argentino', 'Antartida')]
en = [f['properties']['ecorregion'] for f in eco_f]
eg = [shape(f['geometry']).buffer(0) for f in eco_f]
eco = np.full(n, -1, np.int16)
for i, g in enumerate(eg):
    shapely.prepare(g); m = (eco < 0) & shapely.contains_xy(g, lon, lat); eco[m] = i
s = np.where(eco < 0)[0]
if len(s):
    pts = shapely.points(lon[s], lat[s]); eco[s] = np.stack([shapely.distance(g, pts) for g in eg]).argmin(0)

# ---------- unidad de vegetación (Oyarzabal 2018)
uv_f = json.load(open(H('~/.openclaw/data/oyarzabal2018/unidades_vegetacion.geojson')))['features']
un = [f"{f['properties']['CODIGO']} {f['properties'].get('NOMVULGAR') or 'Islas Malvinas'}" for f in uv_f]
ug = [shape(f['geometry']).buffer(0) for f in uv_f]
# ecorregión dominante de cada unidad (por área) — R3 v4.1
_EA = [shape(f['geometry']).buffer(0) for f in eco_f]
uv_dom = [int(np.argmax([g.intersection(e).area for e in _EA])) for g in ug]
uv = np.full(n, -1, np.int16)
for i, g in enumerate(ug):
    shapely.prepare(g); m = (uv < 0) & shapely.contains_xy(g, lon, lat); uv[m] = i
s = np.where(uv < 0)[0]
if len(s):
    pts = shapely.points(lon[s], lat[s]); uv[s] = np.stack([shapely.distance(g, pts) for g in ug]).argmin(0)

# ---------- masa de tierra (parte del polígono provincial); Malvinas: partes del polígono de la unidad 51
part = np.full(n, -1, np.int32)
partgeo = {}
for i, P in enumerate(pn):
    m = np.where(prov == i)[0]
    parts = [q for q in pparts[P] if q.area > 0]
    if P == TDF:  # Malvinas por la geometría de Oyarzabal (más fiel a la costa que el IGN simplificado)
        mal = next(g for g, f in zip(ug, uv_f) if str(f['properties']['CODIGO']) == '51')
        parts = [q for q in parts if not q.intersects(mal.buffer(.2))]  # sin duplicar Malvinas (IGN + Oyarzabal)
        parts += sorted(list(mal.geoms) if hasattr(mal, 'geoms') else [mal], key=lambda q: -q.area)
    for k, q in enumerate(parts):
        partgeo[(i, k)] = q
    if len(parts) == 1: part[m] = 0; continue
    pts = shapely.points(lon[m], lat[m])
    d = np.stack([shapely.distance(q, pts) for q in parts])
    part[m] = d.argmin(0)

# ---------- R1 fuentes fijas
ff = json.load(open(f'{REPO}/worker/src/fuentes_fijas.json'))
def cerca(pa, po, km_max):
    out = np.zeros(n, bool)
    for a, b in zip(pa, po):
        idx = np.where((np.abs(lat - a) < km_max / 100) & (np.abs(lon - b) < km_max / 70))[0]
        if len(idx): out[idx[hav(lat[idx], lon[idx], a, b) <= km_max]] = True
    return out
fa = cerca([f[0] for f in ff['fuentes']], [f[1] for f in ff['fuentes']], ff['radio_m'] / 1000)
cel = np.floor(lat / .02).astype(np.int64) * 100000 + np.floor(lon / .02).astype(np.int64)
k12 = df.acq_date.str[:4].astype(int).values * 12 + df.acq_date.str[5:7].astype(int).values - 1
t = pd.DataFrame({'c': cel, 'k': k12}).drop_duplicates().sort_values(['c', 'k'])
nmes = t.groupby('c').k.size()
pers9 = set()
for c, kk in t.groupby('c').k:
    a = kk.values
    if len(a) < 9: continue
    j = 0
    for i in range(len(a)):
        while a[i] - a[j] >= 12: j += 1
        if i - j + 1 >= 9: pers9.add(c); break
fb = np.isin(cel, list(pers9))
pz = pd.read_csv(H('~/.openclaw/data/pozos_se/capitulo-iv-pozos.csv'), usecols=['geojson'])
xy = np.array([json.loads(g)['coordinates'][:2] for g in pz.geojson.dropna() if '"Point"' in g])
xy = xy[(xy[:, 1] < -20) & (xy[:, 1] > -56) & (xy[:, 0] < -50) & (xy[:, 0] > -75)]
c6 = set(nmes[nmes >= 6].index)
cand = np.isin(cel, list(c6))
fc = np.zeros(n, bool)
ci = np.where(cand)[0]
if len(ci):
    # celda candidata a ≤ 1 km de un pozo: grilla de pozos 0,02°
    pk = collections.defaultdict(list)
    for o, a in xy: pk[(int(np.floor(a / .02)), int(np.floor(o / .02)))].append((a, o))
    ok_cel = {}
    for i in ci:
        c = cel[i]
        if c in ok_cel: fc[i] = ok_cel[c]; continue
        ia, io = int(np.floor(lat[i] / .02)), int(np.floor(lon[i] / .02))
        near = [w for da in (-1, 0, 1) for do in (-1, 0, 1) for w in pk.get((ia + da, io + do), [])]
        r = bool(near) and bool((hav(lat[i], lon[i], np.array([w[0] for w in near]), np.array([w[1] for w in near])) <= 1.0).any())
        # criterio por celda: basta que algún foco de la celda esté a ≤ 1 km de un pozo
        ok_cel[c] = ok_cel.get(c, False) or r
        fc[i] = ok_cel[c]
    fc = np.isin(cel, [c for c, v in ok_cel.items() if v])
fija = fa | fb | fc
print(f'focos {n:,} · fijas (a) {fa.sum():,} (b) {fb.sum():,} (c) {fc.sum():,} · total {fija.sum():,} ({100*fija.mean():.1f} %) · pozos {len(xy):,}')

# ---------- R2/R3/R4 por provincia
PISO = int(next((a.split('=')[1] for a in sys.argv if a.startswith('--piso=')), 100))
def cumple(c, N): return c >= .05 * N or (c >= PISO and c >= .02 * N)
ZON = {}
INF = {}
CAIDAS = []
MES = df.acq_date.str[5:7].astype(int).values
for i, P in enumerate(pn):
    m = (prov == i) & ~fija
    N = int(m.sum())
    if P.startswith('Ciudad'): continue
    if N == 0: continue
    idx = np.where(m)[0]
    # masa de tierra principal = parte con más focos limpios
    pc = collections.Counter(part[idx]); main = pc.most_common(1)[0][0]
    unidades = []   # (clave, régimen, índices, índices propios)
    ec = collections.Counter(eco[idx])
    regs = [e for e, c in ec.items() if cumple(c, N)]
    split = (lambda c: c >= .05 * N) if R3_5 else (lambda c: cumple(c, N))
    nisl = 0
    for e in regs:
        ie = idx[eco[idx] == e]
        grupos = []  # (clave, propios)
        # R3.2 islas (masa de tierra ≠ la principal) que califican, dentro del régimen
        pcount = collections.Counter(part[ie])
        isl = [p for p, c in pcount.items() if p != main and split(c)]
        nisl += len(isl)
        for p in isl: grupos.append((f'eco:{e}|isla:{p}', ie[part[ie] == p]))
        rest = ie[~np.isin(part[ie], isl)]
        rest_main = rest[part[rest] == main] if isl else rest
        # R3.1 unidades de vegetación (ecorregión dominante = e) sobre la masa principal
        uc = collections.Counter(uv[rest_main])
        uq = [u for u, c in uc.items() if split(c) and (not R3_DOM or uv_dom[u] == e)]
        if len(uq) >= 2:
            for u in uq: grupos.append((f'eco:{e}|uv:{u}', rest_main[uv[rest_main] == u]))
        elif len(rest_main) and (not isl or cumple(len(rest_main), N)):
            grupos.append((f'eco:{e}', rest_main))
        if not grupos: grupos.append((f'eco:{e}', ie))
        # lo que no tiene grupo propio (unidades/islas que no califican) → grupo más cercano del régimen
        cent = [(lat[g].mean(), lon[g].mean()) for _, g in grupos]
        asg = [[g] for _, g in grupos]
        usados = np.concatenate([g for _, g in grupos])
        sobra = np.setdiff1d(ie, usados)
        if len(sobra):
            d = np.stack([hav(lat[sobra], lon[sobra], a, o) for a, o in cent])
            for k in range(len(grupos)): asg[k].append(sobra[d.argmin(0) == k])
        for (key, own), extra in zip(grupos, asg):
            unidades.append((key, en[e], np.concatenate(extra), own))
    islas = list(range(nisl))
    # R4 centroide (sobre los focos propios de la unidad; los arrastrados no mueven el centroide)
    zonas = []
    for key, reg, ii, own in unidades:
        cla, clo = lat[own].mean(), lon[own].mean()
        g01 = collections.Counter(zip(np.floor(lat[own] / .1).astype(int), np.floor(lon[own] / .1).astype(int)))
        pt = Point(clo, cla)
        e = int(key.split(':')[1].split('|')[0])
        dentro = eg[e].buffer(.02).contains(pt) and (pgeo[i].buffer(.02).contains(pt) or P == TDF)
        if '|isla:' in key: dentro = dentro and partgeo[(i, int(key.split('isla:')[1]))].buffer(.02).contains(pt)
        if '|uv:' in key: dentro = dentro and ug[int(key.split('uv:')[1])].buffer(.02).contains(pt)
        vacia = g01.get((int(np.floor(cla / .1)), int(np.floor(clo / .1))), 0) == 0
        corr = None
        if not dentro or vacia:
            q = np.percentile(list(g01.values()), 90)
            top = [(a, o) for (a, o), c in g01.items() if c >= q]
            cc = [((a + .5) * .1, (o + .5) * .1) for a, o in top]
            dd = [hav(cla, clo, a, o) for a, o in cc]
            na, no = cc[int(np.argmin(dd))]
            corr = dict(de=[round(cla, 2), round(clo, 2)], motivo=('fuera' if not dentro else 'celda vacía'))
            cla, clo = na, no
        zonas.append(dict(key=key, regimen=reg, lat=round(float(cla), 2), lon=round(float(clo), 2), _ii=ii, correccion=corr,
                          unidad=(un[int(key.split('uv:')[1])] if '|uv:' in key else ('isla' if '|isla:' in key else None))))
    # peso: focos de regímenes sin zona → zona más cercana
    asign = np.full(len(idx), -1)
    pos = {v: k for k, v in enumerate(idx)}
    for z_i, z in enumerate(zonas):
        for v in z['_ii']: asign[pos[v]] = z_i
    sin = np.where(asign < 0)[0]
    if len(sin):
        d = np.stack([hav(lat[idx[sin]], lon[idx[sin]], z['lat'], z['lon']) for z in zonas])
        asign[sin] = d.argmin(0)
    cnt = np.bincount(asign, minlength=len(zonas))
    # control de calidad R7.2: contaminación por fuentes fijas (todos los focos de la provincia → zona más cercana)
    todos = np.where(prov == i)[0]
    dz = np.stack([hav(lat[todos], lon[todos], z['lat'], z['lon']) for z in zonas]); at = dz.argmin(0)
    out = []
    for z_i, z in enumerate(zonas):
        ii = idx[asign == z_i]
        d = hav(lat[ii], lon[ii], z['lat'], z['lon'])
        yr = np.bincount(df.acq_date.str[:4].astype(int).values[ii] - 2012, minlength=13)
        # contaminación: % de TODOS los focos (con fijas) que caerían en la zona y son fijos
        out.append(dict(zid=f"{z['lat']:.2f}_{z['lon']:.2f}", lat=z['lat'], lon=z['lon'], regimen=z['regimen'], unidad=z['unidad'],
                        n_focos=int(cnt[z_i]), peso=round(float(cnt[z_i] / N), 4), r50_km=int(np.median(d)), r90_km=int(np.percentile(d, 90)),
                        anio_top=int(2012 + yr.argmax()), anio_top_pct=int(round(100 * yr.max() / len(ii))),
                        focos_15km=int((hav(lat[idx], lon[idx], z['lat'], z['lon']) < 15).sum()), correccion=z['correccion'],
                        fijas_pct=round(float(100 * fija[todos[at == z_i]].mean()), 1) if (at == z_i).any() else 0.0,
                        pureza=round(float((np.array(en)[eco[ii]] == z['regimen']).mean()), 2)))
    # R4.3 control de fuentes fijas residuales: zona con ≥ 15 % de fijas alrededor existe solo si sus focos limpios son
    # ≥ 10 puntos más estacionales (4 meses pico) que las fijas que la rodean; si no, sus focos van a la zona más cercana
    conc = lambda mm: 100 * np.sort(np.bincount(MES[mm], minlength=13)[1:] / max(len(mm), 1))[-4:].sum()
    caidas = []
    for z_i, z in enumerate(out):
        if z['fijas_pct'] < 15: continue
        tz = todos[at == z_i]; cl, cf = conc(tz[~fija[tz]]), conc(tz[fija[tz]])
        z['estacionalidad'] = dict(limpios=round(cl), fijos=round(cf))
        if cl - cf < 10 and len(out) - len(caidas) > 1: caidas.append(z_i)
    if caidas:
        vivas = [k for k in range(len(out)) if k not in caidas]
        for k in caidas:
            ii = idx[asign == k]
            d = np.stack([hav(lat[ii], lon[ii], out[v]['lat'], out[v]['lon']) for v in vivas]); nn = d.argmin(0)
            for j, v in enumerate(vivas):
                out[v]['n_focos'] += int((nn == j).sum())
            CAIDAS.append(dict(prov=P, **{k2: out[k][k2] for k2 in ('zid', 'regimen', 'unidad', 'peso', 'fijas_pct', 'estacionalidad')}))
        out = [out[v] for v in vivas]
        for z in out: z['peso'] = round(z['n_focos'] / N, 4)
    out.sort(key=lambda z: -z['peso'])
    ZON[P] = out
    INF[P] = dict(n_total=int((prov == i).sum()), n_limpio=N, fijas_pct=round(100 * (1 - N / (prov == i).sum()), 1),
                  islas=len(islas), regimenes={en[e]: round(c / N, 3) for e, c in ec.most_common()},
                  fijas_por_regla={'a': int((fa & (prov == i)).sum()), 'b': int((fb & (prov == i)).sum()), 'c': int((fc & (prov == i)).sum())})

# CABA: sin cambios (R4)
cal = json.load(open(f'{REPO}/worker/src/calibracion_3.0_argentina.json'))['zonas']
ZON['Ciudad Autónoma de Buenos Aires'] = [dict(zid=f"{z['lat']:.2f}_{z['lon']:.2f}", lat=z['lat'], lon=z['lon'], regimen='Pampa', unidad=None,
                                               n_focos=z['n_focos'], peso=z['peso'], nota='el indicador no aplica (sin cambios)') for z in cal['Ciudad Autónoma de Buenos Aires']]
json.dump(dict(version='4.0-borrador', reglas='docs/REGLAS_ZONAS_v4.md (firmadas 17/11/2026)', generado=pd.Timestamp.now().strftime('%Y-%m-%d'),
               insumos=dict(focos='FIRMS VIIRS S-NPP 2012–2024 Argentina + Falkland_Islands', ecorregiones='MAyDS ecoregiones2021',
                            unidades='Oyarzabal et al. 2018 Apéndice 3', pozos=f'SE Capítulo IV – Pozos ({len(xy)} con coordenadas)'),
               zonas=ZON, info=INF, caidas_r43=CAIDAS), open(f'{AQ}/data/zonas_v4' + ('_split5' if R3_5 else '') + (f'_p{PISO}' if PISO != 100 else '') + '.json', 'w'), ensure_ascii=False, indent=1)
tot = sum(len(v) for v in ZON.values())
L = [f'# Zonas v4 — {tot} zonas (v3: 115)\n']
for P in pn:
    if P not in ZON: continue
    v3 = len(cal.get(P, []))
    L.append(f'\n## {P} — v3 {v3} → v4 {len(ZON[P])}')
    if P in INF: L.append(f"{INF[P]['n_total']:,} focos · fijas {INF[P]['fijas_pct']} % (a {INF[P]['fijas_por_regla']['a']}, b {INF[P]['fijas_por_regla']['b']}, c {INF[P]['fijas_por_regla']['c']})\n")
    L.append('| zona | régimen | unidad Oyarzabal | peso | r50/r90 km | año top | focos ≤15 km | corrección |')
    L.append('|---|---|---|---|---|---|---|---|')
    for z in ZON[P]:
        L.append(f"| {z['zid']} | {z['regimen']} | {z.get('unidad') or '—'} | {z['peso']} | {z.get('r50_km','')}/{z.get('r90_km','')} | {z.get('anio_top','')} ({z.get('anio_top_pct','')} %) | {z.get('focos_15km','')} | {(z.get('correccion') or {}).get('motivo','')} |")
open(f'{AQ}/data/zonas_v4' + ('_split5' if R3_5 else '') + (f'_p{PISO}' if PISO != 100 else '') + '_resumen.md', 'w').write('\n'.join(L) + '\n')
print('zonas v4:', tot); print('caídas R4.3:', CAIDAS)
for P in pn:
    if P in ZON: print(f"  {P[:26]:26s} v3 {len(cal.get(P, []))} → v4 {len(ZON[P])}  " + ' · '.join(f"{z['regimen'][:18]}{'/'+z['unidad'][:22] if z.get('unidad') else ''} {z['peso']:.2f}" for z in ZON[P]))
