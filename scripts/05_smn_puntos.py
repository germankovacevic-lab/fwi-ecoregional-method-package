#!/usr/bin/env python3
"""Digitaliza los puntos (estaciones) del mapa diario SMN/SNMF de peligro de incendios y los empareja con el padrón
oficial de estaciones SMN (datos abiertos, ssl.smn.gob.ar/dpd/zipopendata.php?dato=estaciones).
Georreferencia: lon lineal en x, lat Mercator en y, ajustada por ICP contra el padrón."""
import numpy as np, os, json, sys
from PIL import Image
from scipy import ndimage
H = os.path.expanduser
img = np.asarray(Image.open(H('~/.openclaw/data/smn/mapa_2026-11-16/snmf_peligro_2026-11-16.jpg')).convert('RGB')).astype(int)
R, G, B = img[..., 0], img[..., 1], img[..., 2]
# clases: rojo, naranja, amarillo, azul, verde (colores saturados de los marcadores)
cls = {'Extremo': (R > 200) & (G < 60) & (B < 60), 'Muy alto': (R > 220) & (G > 120) & (G < 175) & (B < 50),
       'Alto': (R > 220) & (G > 210) & (B < 60), 'Moderado': (R < 40) & (G < 40) & (B > 200),
       'Bajo': (R < 70) & (G > 120) & (G < 175) & (B < 70)}
pts = []
for k, m in cls.items():
    m[:, 600:] &= False  # leyenda y recuadro antártico a la derecha... se filtra luego por posición
    lab, n = ndimage.label(m)
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if 25 <= len(ys) <= 260 and (xs.max() - xs.min()) < 20 and (ys.max() - ys.min()) < 20:
            pts.append((xs.mean(), ys.mean(), k, len(ys)))
pts = [p for p in pts if p[1] < 1110 and p[1] > 110]
print(len(pts), 'puntos', {k: sum(p[2] == k for p in pts) for k in cls})
# padrón SMN
st = []
for ln in open(H('~/.openclaw/data/smn/estaciones.txt'), encoding='latin1').read().split('\n')[2:]:
    if len(ln) < 100: continue
    nom, prov = ln[:31].strip(), ln[31:69].strip()
    f = ln[69:].split()
    try:
        la = int(f[0]) - np.sign(int(f[0]) or -1) * int(f[1]) / 60 if int(f[0]) else -int(f[1]) / 60
        lo = int(f[2]) - int(f[3]) / 60
    except Exception: continue
    la = -(abs(int(f[0])) + int(f[1]) / 60); lo = -(abs(int(f[2])) + int(f[3]) / 60)
    if prov == 'ANTARTIDA': continue
    st.append((nom, prov, la, lo, f[5] if len(f) > 5 else ''))
S = np.array([[s[3], s[2]] for s in st])
merc = lambda la: np.log(np.tan(np.pi / 4 - np.radians(la) / 2))  # crece hacia el sur
P = np.array([[p[0], p[1]] for p in pts])
# inicial desde graticula: 70W x≈232? usamos 25S y≈200, 55S y≈1102 ; 75W x≈140, 50W x≈605
ax = (689 - 129) / 25; bx = 129 + 75 * ax  # ticks medidos en la imagen: 75W=129 … 50W=689 px
y25, y50 = merc(-25), merc(-50); ay = (918 - 200) / (y50 - y25); by = 200 - ay * y25  # 25S=200 … 50S=918 px
def topix(lo, la): return np.c_[bx + ax * lo, by + ay * merc(la)]
for it in range(0):
    Q = topix(S[:, 0], S[:, 1])
    d = np.linalg.norm(P[:, None] - Q[None], axis=2); j = d.argmin(1); dm = d.min(1)
    ok = dm < np.percentile(dm, 80) + 1
    A = np.c_[S[j[ok], 0], np.ones(ok.sum())]; ax, bx = np.linalg.lstsq(A, P[ok, 0], rcond=None)[0]
    A = np.c_[merc(S[j[ok], 1]), np.ones(ok.sum())]; ay, by = np.linalg.lstsq(A, P[ok, 1], rcond=None)[0]
Q = topix(S[:, 0], S[:, 1]); d = np.linalg.norm(P[:, None] - Q[None], axis=2); j = d.argmin(1); dm = d.min(1)
print('residuo px p50/p90/max', np.percentile(dm, [50, 90]).round(1), dm.max().round(1))
out = []
for p, jj, dd in zip(pts, j, dm):
    s = st[jj]
    out.append(dict(estacion=s[0], provincia=s[1], lat=round(s[2], 3), lon=round(s[3], 3), nro=s[4], clase=p[2], px=[round(p[0]), round(p[1])], residuo_px=round(float(dd), 1)))
dup = {}
for o in out: dup.setdefault(o['estacion'], []).append(o)
print('duplicados', [k for k, v in dup.items() if len(v) > 1])
for o in sorted(out, key=lambda o: -o['residuo_px'])[:8]: print(o)
json.dump(dict(fuente='Mapa SMN/SNMF Peligro de incendios 16-11-2026 (digitalizado) + padrón estaciones SMN', estaciones=out),
          open(H('~/.openclaw/data/smn/mapa_2026-11-16/estaciones_fwi_smn.json'), 'w'), ensure_ascii=False, indent=1)

# puntos sin estación del padrón a < 3 px: se guardan con su lat/lon digitalizada
inv_lon = lambda x: (x - bx) / ax
def inv_lat(y):
    m = (y - by) / ay
    return np.degrees(2 * (np.pi / 4 - np.arctan(np.exp(m))))  # inversa de merc()
D = json.load(open(H('~/.openclaw/data/smn/mapa_2026-11-16/estaciones_fwi_smn.json')))
for o in D['estaciones']:
    if o['residuo_px'] > 3:
        o['lat'], o['lon'] = round(float(inv_lat(o['px'][1])), 2), round(float(inv_lon(o['px'][0])), 2)
        o['estacion'] = 'fuera del padrón SMN'; o['provincia'] = ''; o['nro'] = ''
json.dump(D, open(H('~/.openclaw/data/smn/mapa_2026-11-16/estaciones_fwi_smn.json'), 'w'), ensure_ascii=False, indent=1)
print('en padrón', sum(o['residuo_px'] <= 3 for o in D['estaciones']), 'fuera', sum(o['residuo_px'] > 3 for o in D['estaciones']))
print([(o['lat'], o['lon']) for o in D['estaciones'] if o['residuo_px'] > 3])
