#!/usr/bin/env python3
"""Calibración de PRODUCCIÓN del Semáforo FWI por ecorregión (E1, REGLAS_ZONAS_v4 §R5c) → worker/src/fwi_ecorregional.json

Mismas reglas que la evaluación (16_fwi_ecorregional.py), pero ajustadas con TODA la historia disponible 2012–2025
(la evaluación fuera de muestra 2022–2026 es la estimación de desempeño; producción usa todos los datos, como v3).
  · puntos: 90 zonas v4.1; peso = focos limpios 2012–2025 asignados a la zona (más cercana de su provincia)
  · FWI ecorregional = promedio ponderado de los FWI ERA5-equivalentes de sus puntos
  · cortes = p10/p25/p50/p75 del FWI ecorregional en los días fuertes de la ecorregión (≥ p90 de días con foco);
    < 300 días fuertes → grupo R5b → respaldo R5b
  · provincia = redondeo del promedio de niveles de sus ecorregiones ponderado por sus focos limpios 2012–2025
  · vivo: por zona, mapeo de cuantiles Open-Meteo (emulado, ventana 92 d, DC sembrado) → ERA5, 201 puntos, solape
    2021-04 → 2026-10; cola por cociente de p99,5 (igual que producción v3)
"""
import json, os, sys, hashlib, datetime as dt
import numpy as np, pandas as pd
AQ = os.path.dirname(os.path.abspath(__file__)); REPO = f'{AQ}/../..'
src = open(f'{AQ}/15_evaluacion_fwi.py').read()
g = {'__file__': f'{AQ}/15_evaluacion_fwi.py', '__name__': 'x'}
exec(compile(src[:src.index("def evaluar(")], '15', 'exec'), g)
DIAS, PROVS, R5B, FALLBACK, nrm = g['DIAS'], g['PROVS'], g['R5B'], g['FALLBACK'], g['nrm']
lat, lon, prov, fecha, pn, hav, H = g['lat'], g['lon'], g['prov'], g['fecha'], g['pn'], g['hav'], g['H']
eco_n = np.array([nrm(g['g']['en'][e]) for e in g['g']['eco'][g['ok']]])
FIN = pd.Timestamp('2025-12-31'); calm = np.asarray(DIAS <= FIN); fcal = np.asarray(fecha <= FIN)

def conteo(idx):
    return pd.Series(fecha[idx]).value_counts().reindex(DIAS).fillna(0).values

Zj = json.load(open(f'{AQ}/data/zonas_v4_split5_p50.json'))['zonas']
Z = [dict(P=P, zid=z['zid'], lat=z['lat'], lon=z['lon'], eco=nrm(z['regimen']), regimen=z['regimen'], unidad=z.get('unidad'))
     for P, v in Zj.items() for z in v if P in PROVS]
FWI = {z['zid']: pd.read_csv(H(f"~/.openclaw/data/gfi_v4_fwi_worker/fwi_{z['zid']}.csv")).set_index('date')['fwi'].reindex(DIAS.strftime('%Y-%m-%d')).values for z in Z}
W = {}
for P in PROVS:
    zs = [z for z in Z if z['P'] == P]; ii = np.where((prov == pn.index(P)) & fcal)[0]
    a = np.stack([hav(lat[ii], lon[ii], z['lat'], z['lon']) for z in zs]).argmin(0)
    for k, z in enumerate(zs): W[z['zid']] = int((a == k).sum())
ECOS = sorted({z['eco'] for z in Z})
pts = {e: [z['zid'] for z in Z if z['eco'] == e] for e in ECOS}
def media(ids):
    X = np.stack([FWI[i] for i in ids]); w = np.array([W[i] for i in ids], float)[:, None] * ~np.isnan(X)
    return np.where(w.sum(0) > 0, np.nansum(np.nan_to_num(X) * w, 0) / np.maximum(w.sum(0), 1e-9), np.nan)
muestras, nf = {}, {}
for e in ECOS:
    fe = media(pts[e]); c = conteo(np.where((eco_n == e))[0]); cal = c[calm & (c > 0)]
    fd = (c >= np.percentile(cal, 90)) & (c > 0) & calm
    muestras[e] = fe[fd & ~np.isnan(fe)]; nf[e] = int(fd.sum())
def pool(gname): return np.concatenate([muestras[x] for x in ECOS if R5B[x] == gname])
cortes, origen = {}, {}
for e in ECOS:
    if len(muestras[e]) >= 300: v, o = muestras[e], 'propia'
    else:
        gname = R5B[e]; v = pool(gname)
        while len(v) < 300 and gname in FALLBACK: gname = FALLBACK[gname]; v = pool(gname)
        o = gname
    cortes[e] = [round(float(q), 1) for q in np.percentile(v, [10, 25, 50, 75])]; origen[e] = o

QG = np.linspace(0, 100, 201)
zonas = {}
for z in Z:
    v = pd.read_csv(H(f"~/.openclaw/data/gfi_v4_vivo/vivo_{z['zid']}.csv")).dropna(subset=['sem'])
    e5 = pd.read_csv(H(f"~/.openclaw/data/gfi_v4_fwi_worker/fwi_{z['zid']}.csv"))
    m = v.merge(e5[['date', 'fwi']].rename(columns={'fwi': 'era5'}), on='date')
    qv = np.maximum.accumulate(np.round(np.quantile(m['sem'].values, QG / 100), 2))
    qe = np.maximum.accumulate(np.round(np.quantile(m['era5'].values, QG / 100), 2))
    clim = e5[(e5.date >= '2012-01-01') & (e5.date <= '2025-12-31')]
    zonas[z['zid']] = dict(provincia=z['P'], lat=z['lat'], lon=z['lon'], ecorregion=z['eco'], regimen=z['regimen'], unidad=z['unidad'],
                           peso_eco=W[z['zid']], q_vivo=[float(x) for x in qv], q_era5=[float(x) for x in qe],
                           cola=round(float(qe[-2] / qv[-2]) if qv[-2] > 0 else 1.0, 4),
                           solape=[str(m.date.min()), str(m.date.max()), int(len(m))],
                           dc_clim=clim.groupby(clim.date.str.slice(5, 7)).dc.median().round(1).tolist())
NOM = {'selva paranense': 'Selva Paranaense'}
NOM.update({nrm(n): n for n in ['Altos Andes', 'Bosques Patagónicos', 'Campos y Malezales', 'Chaco Húmedo', 'Chaco Seco', 'Delta e Islas del Paraná',
                          'Espinal', 'Estepa Patagónica', 'Esteros del Iberá', 'Islas del Atlántico Sur', 'Monte de Llanuras y Mesetas',
                          'Monte de Sierras y Bolsones', 'Pampa', 'Puna', 'Yungas']})
NOM_EN = {'altos andes': 'High Andes', 'bosques patagonicos': 'Patagonian Forests', 'campos y malezales': 'Campos and Malezales',
          'chaco humedo': 'Humid Chaco', 'chaco seco': 'Dry Chaco', 'delta e islas del parana': 'Paraná Delta and Islands',
          'espinal': 'Espinal', 'estepa patagonica': 'Patagonian Steppe', 'esteros del ibera': 'Iberá Wetlands',
          'islas del atlantico sur': 'South Atlantic Islands', 'monte de llanuras y mesetas': 'Monte of Plains and Plateaus',
          'monte de sierras y bolsones': 'Monte of Sierras and Basins', 'pampa': 'Pampas', 'puna': 'Puna',
          'selva paranense': 'Paranaense Forest', 'yungas': 'Yungas'}
ecorregiones = {e: dict(nombre_es=NOM.get(e, e), nombre_en=NOM_EN.get(e, e), cortes=cortes[e], cortes_origen=origen[e],
                        dias_fuertes_2012_2025=nf[e], zonas=pts[e]) for e in ECOS}
provincias = {}
for P in PROVS:
    c = pd.Series(eco_n[(prov == pn.index(P)) & fcal]).value_counts()
    w = {e: int(v) for e, v in c.items() if e in ECOS}
    provincias[P] = {e: round(v / sum(w.values()), 4) for e, v in sorted(w.items(), key=lambda t: -t[1])}
ev = json.load(open(f'{AQ}/data/evaluacion_fwi_ecorregional.json'))['tabla']
cuerpo = dict(version='2.0-ecorregional', generado=dt.date.today().isoformat(),
    criterio='Semáforo FWI por ecorregión (Ministerio de Ambiente 2021). FWI diario de la ecorregión = promedio de sus puntos ponderado por el fuego histórico; clases del SNMF con umbral de ocurrencia propio de cada ecorregión (p10/25/50/75 del FWI en sus días de fuego fuerte). Provincia = promedio de las clases de sus ecorregiones ponderado por dónde está su fuego.',
    criterio_en='FWI fire-danger traffic light by ecoregion (Argentine Ministry of Environment, 2021). Daily ecoregion FWI = fire-weighted mean of its points; SNMF classes with each ecoregion\'s own occurrence thresholds (10/25/50/75th percentiles of FWI on its strong-fire days). Province = fire-weighted mean of its ecoregions\' classes.',
    historia='ERA5 (Copernicus CDS) 12:00 locales, motor worker/src/fwi.js (DMC por latitud); focos VIIRS S-NPP limpios (R1 v4) 2012–2025',
    escala='Cortes en escala ERA5. El FWI vivo de cada punto (Open-Meteo, ventana 92 días, DC inicial ERA5) se lleva a su equivalente ERA5 por mapeo de cuantiles (q_vivo → q_era5, 201 puntos, solape 2021-04 → 2026-10; por encima del p99,5 se extrapola con `cola`); recién después se promedia por ecorregión.',
    verificacion=dict(metodo='calibrado 2012–2021, evaluado fuera de muestra 2022-01 → 2026-10, provincia-día, PSS de ≥ Alto (tools/auditoria_zonas/16_fwi_ecorregional.py)',
                      pss_alto_pais=dict(produccion_v3=round(ev['País']['v3']['pss_alto'], 3), ecorregional=round(ev['País']['E1']['pss_alto'], 3)),
                      alarma_pais=dict(produccion_v3=round(ev['País']['v3']['alarma'], 3), ecorregional=round(ev['País']['E1']['alarma'], 3)),
                      por_region={r: dict(v3=round(ev[r]['v3']['pss_alto'], 3), ecorregional=round(ev[r]['E1']['pss_alto'], 3), dif_ic95=ev[r]['E1']['dif_ic95']) for r in ('NEA', 'NOA', 'Centro', 'Patagonia')}),
    clases=['bajo', 'moderado', 'alto', 'muy_alto', 'extremo'], ecorregiones=ecorregiones, provincias=provincias, zonas=zonas)
s = json.dumps(cuerpo, ensure_ascii=False, sort_keys=True)
cuerpo['sha256'] = hashlib.sha256(s.encode()).hexdigest()
json.dump(cuerpo, open(f'{REPO}/worker/src/fwi_ecorregional.json', 'w'), ensure_ascii=False, indent=1)
for e in ECOS: print(f"{NOM.get(e, e):30s} {cortes[e]}  {origen[e]:18s} días fuertes {nf[e]:4d}  puntos {len(pts[e])}")
print('provincias', len(provincias), 'zonas', len(zonas))
