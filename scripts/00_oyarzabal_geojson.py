#!/usr/bin/env python3
"""Oyarzabal et al. 2018, Unidades de vegetación de la Argentina (Ecología Austral 28:40–63,
doi 10.25260/EA.18.28.1.0.399), Apéndice 3 (KML WGS84) → ~/.openclaw/data/oyarzabal2018/unidades_vegetacion.geojson"""
import xml.etree.ElementTree as ET, json, os
from shapely.geometry import Polygon, MultiPolygon, mapping
D = os.path.expanduser('~/.openclaw/data/oyarzabal2018')
K = '{http://www.opengis.net/kml/2.2}'
ring = lambda el: [tuple(map(float, p.split(',')[:2])) for p in el.text.split()]
feats = []
for pm in ET.parse(f'{D}/unidades_vegetacion.kml').getroot().iter(K + 'Placemark'):
    props = {sd.get('name'): sd.text for sd in pm.iter(K + 'SimpleData')}
    polys = []
    for pg in pm.iter(K + 'Polygon'):
        o = pg.find(f'{K}outerBoundaryIs/{K}LinearRing/{K}coordinates')
        h = [ring(x) for x in pg.findall(f'{K}innerBoundaryIs/{K}LinearRing/{K}coordinates')]
        polys.append(Polygon(ring(o), h))
    feats.append({'type': 'Feature', 'properties': props, 'geometry': mapping(MultiPolygon(polys).buffer(0))})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(f'{D}/unidades_vegetacion.geojson', 'w'))
for f in sorted(feats, key=lambda f: int(f['properties']['CODIGO'])):
    p = f['properties']
    print(p.get('CODIGO'), '|', p.get('REGION'), '|', p.get('UNID_FITOG'), '|', p.get('NOMFISONOM'), '|', (p.get('NOMVULGAR') or '')[:45])
