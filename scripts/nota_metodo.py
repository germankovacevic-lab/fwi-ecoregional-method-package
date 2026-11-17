#!/usr/bin/env python3
"""Nota de método del Semáforo FWI por ecorregión, en PDF (ES y EN), generada desde la calibración de producción:
mapa de las ecorregiones oficiales con los puntos de cálculo, procedimiento de calibración, tablas de umbrales y de
pesos provinciales, evaluación, límites y antecedentes. Uso: nota_metodo.py <dir_salida> <DOI>
Requiere matplotlib y Google Chrome (impresión a PDF sin interfaz)."""
import json, os, subprocess, sys, html
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
AQ = os.path.dirname(os.path.abspath(__file__)); G = os.path.join(AQ, '..', '..')
OUT, DOI = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
CAL = json.load(open(f'{G}/worker/src/fwi_ecorregional.json'))
GEO = json.load(open(f'{G}/deploy/argentina/ecorregiones.json'))
E, Z, P, V = CAL['ecorregiones'], CAL['zonas'], CAL['provincias'], CAL['verificacion']
orden = sorted(E, key=lambda k: E[k]['nombre_es'])
PAL = ['#4e79a7', '#a0cbe8', '#f28e2b', '#ffbe7d', '#59a14f', '#8cd17d', '#b6992d', '#f1ce63', '#499894', '#86bcb6',
       '#e15759', '#ff9d9a', '#79706e', '#d37295', '#b07aa1', '#9d7660']
COL = {k: PAL[i] for i, k in enumerate(orden)}

def mapa(lang):
    n = 'nombre_es' if lang == 'es' else 'nombre_en'
    fig = plt.figure(figsize=(10.4, 9.6), dpi=200, facecolor='white'); ax = fig.add_axes([0.0, 0.01, 0.60, 0.98])
    for f in GEO['features']:
        k = f['properties']['clave']; g = f['geometry']; polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        for pl in polys: ax.add_patch(MP(pl[0], closed=True, facecolor=COL[k], edgecolor='white', linewidth=.5, alpha=.9))
    wmax = max(z['peso_eco'] for z in Z.values())
    for z in Z.values():
        ax.scatter(z['lon'], z['lat'], s=14 + 190 * (z['peso_eco'] / wmax) ** .5, facecolor='white', edgecolor='#111', linewidth=.9, alpha=.92, zorder=5)
    ax.set_xlim(-74.5, -52.5); ax.set_ylim(-56, -21); ax.set_aspect(1.25); ax.axis('off')
    hs = [plt.Rectangle((0, 0), 1, 1, color=COL[k]) for k in orden]
    ls = [f"{E[k][n]} ({len(E[k]['zonas'])})" for k in orden]
    hs.append(plt.Line2D([], [], marker='o', linestyle='', markerfacecolor='white', markeredgecolor='#111', markersize=8))
    ls.append('punto de cálculo (tamaño = fuego histórico)' if lang == 'es' else 'computation point (size = historical fire)')
    fig.legend(hs, ls, loc='center left', bbox_to_anchor=(0.585, 0.5), fontsize=11, frameon=False, title=('Ecorregión (puntos)' if lang == 'es' else 'Ecoregion (points)'), title_fontsize=12.5)
    ax.text(-59.2, -53.3, 'Islas Malvinas (Arg.)', fontsize=9, color='#333', ha='center')
    p = f'{OUT}/mapa_ecorregiones_puntos_{lang}.png'; fig.savefig(p, facecolor='white'); plt.close(fig); return p

def num(x, lang, d=1):
    s = f'{x:.{d}f}'; return s if lang == 'en' else s.replace('.', ',')
ORI = {'es': {'propia': 'propios', 'Árido': 'grupo árido', 'Patagonia estepa': 'Estepa Patagónica', 'Chaco Seco': 'Chaco Seco'},
       'en': {'propia': 'own', 'Árido': 'arid group', 'Patagonia estepa': 'Patagonian Steppe', 'Chaco Seco': 'Dry Chaco'}}
CL = [('Bajo', 'Low', '#2f9e6f'), ('Moderado', 'Moderate', '#3f9be8'), ('Alto', 'High', '#f2c230'), ('Muy alto', 'Very high', '#f07d1a'), ('Extremo', 'Extreme', '#e0322b')]

T = {
 'es': dict(
  titulo='Semáforo FWI por ecorregión', sub='Nota de método: las ecorregiones, los puntos de cálculo y cómo se calibran las clases de peligro',
  autor='Germán Ricardo Kovacevic · ORCID <a href="https://orcid.org/0009-0007-4270-1963">0009-0007-4270-1963</a> · GEOFUEGO (geofuego.com.ar)<br>versión 1.0.0 · calibración ' + CAL['generado'],
  resumen='GEOFUEGO calcula el índice meteorológico de peligro de incendio FWI (sistema canadiense, Van Wagner 1987) <b>por ecorregión</b>. En cada uno de 89 puntos de fuego histórico se calcula el FWI del día; el FWI de cada ecorregión es el promedio de sus puntos, ponderado por el fuego histórico de cada uno; y la clase de peligro (las cinco del Servicio Nacional de Manejo del Fuego, SNMF) sale de umbrales propios de cada ecorregión. La provincia se informa como un <b>resumen</b> de sus ecorregiones. Esta nota describe la geografía usada y el procedimiento de calibración. Está en producción desde el 17/11/2026.',
  h1='1. Las ecorregiones', p1='La unidad es el mapa oficial <b>«Ecorregiones de la Argentina»</b> del Ministerio de Ambiente y Desarrollo Sostenible (2021), que actualiza la clasificación de Burkart et al. (1999). Se obtuvo del servicio de mapas del Ministerio (capa <code>areas_protegidas:ecoregiones2021</code>, geo.ambiente.gob.ar). El mapa tiene 18 ecorregiones; se usan las <b>16</b> con territorio continental o insular donde hay fuego de vegetación (quedan afuera Mar Argentino y Antártida). Cada ecorregión se toma <b>entera</b>: no se corta en los límites provinciales, porque el clima, la vegetación y el régimen de fuego no cambian en ellos. El paquete incluye la capa original tal como la publica el Ministerio (licencia libre Creative Commons, según declara el servicio) y, aparte, un PDF con un mapa por provincia que muestra las ecorregiones, las unidades de vegetación, los focos y dónde quedó cada punto.',
  fig='Figura 1. Las 16 ecorregiones y los 89 puntos de cálculo. Entre paréntesis, la cantidad de puntos de cada ecorregión.',
  h2='2. Los puntos de cálculo', p2='Los puntos son los lugares donde se concentra el fuego de cada provincia según el archivo satelital VIIRS S-NPP (NASA FIRMS) 2012–2024, después de sacar las fuentes fijas (antorchas de gas y petróleo, industria). Los pesos y los umbrales de producción usan los focos de 2012–2025. Dentro de cada provincia hay un punto por cada ecorregión que reúne una parte relevante de su fuego, y una ecorregión se parte en más de un punto cuando una unidad de vegetación (Oyarzabal et al. 2018) o una isla lo justifican. Cada punto pertenece a una ecorregión y tiene un <b>peso</b>: la cantidad de focos históricos que representa. Las reglas completas están en <code>rules/REGLAS_ZONAS_v4.md</code>.',
  h3='3. Cómo se calibra', pasos=[
   '<b>FWI de cada punto.</b> Meteorología ERA5 (Copernicus) a las 12:00 locales y lluvia de las 24 horas previas, 2012–2025. Motor único para la historia y para el cálculo diario.',
   '<b>FWI de la ecorregión.</b> Para cada día, promedio del FWI de sus puntos ponderado por el peso de cada punto.',
   '<b>Días de fuego fuerte.</b> Para cada ecorregión, los días en que la cantidad de focos está en el 10 % más alto de sus días con fuego.',
   '<b>Umbral de ocurrencia</b> (criterio de la guía de análisis del FWI del SNMF). Las clases arrancan en el FWI en que efectivamente ocurrió el fuego fuerte de la ecorregión: Moderado, Alto, Muy alto y Extremo en los percentiles 10, 25, 50 y 75 del FWI de la ecorregión en sus días de fuego fuerte. Por debajo del percentil 10 la clase es Bajo.',
   '<b>Muestra mínima.</b> Una ecorregión con menos de 300 días de fuego fuerte no tiene muestra suficiente y usa los umbrales de un grupo de régimen parecido (columna «Umbrales» de la Tabla 1). La regla quedó escrita antes de calcular.',
   '<b>Provincia = resumen.</b> Nivel de la provincia = promedio de los niveles (0 a 4) de sus ecorregiones, ponderado por la fracción del fuego histórico de la provincia que ocurre en cada una (Tabla 2), redondeado al entero más cercano.',
   '<b>Cálculo diario.</b> El día a día usa Open-Meteo, que no da el mismo número que ERA5, sobre todo en montaña. Antes de promediar, el FWI de cada punto se lleva a su equivalente ERA5 con un mapeo de cuantiles ajustado punto por punto sobre el período en que existen las dos fuentes (2021–2026). El código de sequía (DC) arranca del valor ERA5 real del punto.'],
  t1='Tabla 1. Umbrales por ecorregión: FWI (escala ERA5) en que arranca cada clase.', c1=['Ecorregión', 'Puntos', 'Días fuertes', 'Moderado', 'Alto', 'Muy alto', 'Extremo', 'Umbrales'],
  t2='Tabla 2. Peso de cada ecorregión en el resumen de cada provincia (% del fuego histórico de la provincia; se listan las de 1 % o más).', c2=['Provincia', 'Ecorregiones y peso'],
  h4='4. Verificación', p4='Las reglas se registraron antes de medir. Los umbrales se calibraron con 2012–2021 y se probaron fuera de muestra de enero de 2022 a octubre de 2026, provincia por día, contra los días de fuego fuerte de cada provincia. La medida es el puntaje de Peirce (aciertos menos falsas alarmas) de la alarma «Alto o más»; el intervalo de confianza del 95 % sale de remuestrear meses.',
  c3=['', 'Esquema anterior', 'Por ecorregión', 'Diferencia [IC 95 %]'], pais='País',
  p4b='Con el esquema anterior (umbrales por subregión y provincia igual a su peor zona) la provincia estaba en «Alto o más» el {a0} % de los días; con el ecorregional, el {a1} %. La mayor parte de la mejora (+0,173 en el país) viene de reemplazar la peor zona por el promedio ponderado por fuego; la ecorregión como unidad agrega +0,023 (en el NEA +0,063, significativo). Las tablas completas, y las dos propuestas previas que no pasaron su evaluación, están en <code>method/METODO_v4.md</code> y <code>evaluation/</code>.',
  h5='5. Límites', lim=['El índice es solo meteorológico: no considera carga de combustible, topografía ni el secado de pastizales vivos.', 'Los umbrales son una estimación de GEOFUEGO. El SNMF no publica los suyos. El mapa oficial de peligro es el del SNMF y el Servicio Meteorológico Nacional.', 'Cinco ecorregiones (Yungas, Puna, Altos Andes, Bosques Patagónicos, Islas del Atlántico Sur) usan umbrales prestados por muestra corta: son las clases menos firmes.', 'El resumen provincial es un promedio: una provincia puede quedar en una clase intermedia con una ecorregión en clase alta. Por eso el mapa muestra siempre la clase de cada ecorregión.', 'Las ecorregiones describen la vegetación potencial. Donde domina la quema agrícola describen bien el clima, no el combustible actual.'],
  h6='6. Antecedentes', ant='Ajustar los umbrales del FWI a cada región es práctica establecida, y esta nota no afirma ser la primera en usar unidades ecológicas. Kudláčková et al. (2024) revisan 750 trabajos y proponen clases de FWI para 18 zonas ambientales del mundo. Ellis, Bowman y Williamson (2024) estiman umbrales de inflamabilidad en 772 ecorregiones. En la Argentina, Maturano et al. (2026, preprint) ajustan umbrales para siete regiones ambientales de Córdoba definidas por agrupamiento estadístico. Naim et al. (2026) describen el FWI previo a incendios en seis ecorregiones de Sumatra. Lo propio de este trabajo es usar el mapa oficial nacional de ecorregiones, enteras a través de los límites provinciales; el criterio de ocurrencia del SNMF; el registro de las reglas antes de medir; y la publicación de toda la cadena, incluidas las propuestas que fallaron.',
  h7='Fuentes', cita='Cómo citar'),
 'en': dict(
  titulo='Ecoregion-based FWI fire-danger semaphore', sub='Method note: the ecoregions, the computation points and how the danger classes are calibrated',
  autor='Germán Ricardo Kovacevic · ORCID <a href="https://orcid.org/0009-0007-4270-1963">0009-0007-4270-1963</a> · GEOFUEGO (geofuego.com.ar)<br>version 1.0.0 · calibration ' + CAL['generado'],
  resumen='GEOFUEGO computes the Fire Weather Index (Canadian system, Van Wagner 1987) <b>by ecoregion</b>. The daily FWI is computed at each of 89 historical fire points; the FWI of each ecoregion is the average of its points, weighted by each point\'s historical fire; and the danger class (the five used by Argentina\'s National Fire Management Service, SNMF) comes from thresholds specific to each ecoregion. A province is reported as a <b>summary</b> of its ecoregions. This note describes the geography used and the calibration procedure. Operational since 17 November 2026.',
  h1='1. The ecoregions', p1='The unit is the official map <b>“Ecorregiones de la Argentina”</b> of the Ministry of Environment and Sustainable Development (2021), which updates the classification of Burkart et al. (1999). It was obtained from the Ministry\'s map service (layer <code>areas_protegidas:ecoregiones2021</code>, geo.ambiente.gob.ar). The map has 18 ecoregions; the <b>16</b> with mainland or island territory where vegetation fire occurs are used (Argentine Sea and Antarctica are left out). Each ecoregion is taken <b>whole</b>: it is not cut at provincial borders, because climate, vegetation and fire regime do not change there. The package includes the original layer exactly as served by the Ministry (free Creative Commons licence, as declared by the service) and, separately, a PDF with one map per province showing the ecoregions, the vegetation units, the fire detections and where each point sits.',
  fig='Figure 1. The 16 ecoregions and the 89 computation points. In brackets, the number of points in each ecoregion.',
  h2='2. The computation points', p2='The points are the places where each province\'s fire concentrates according to the VIIRS S-NPP satellite archive (NASA FIRMS) 2012–2024, after removing static sources (gas and oil flares, industry). The production weights and thresholds use detections from 2012–2025. Within each province there is one point for every ecoregion holding a relevant share of its fire, and an ecoregion is split into more than one point when a vegetation unit (Oyarzabal et al. 2018) or an island justifies it. Each point belongs to one ecoregion and has a <b>weight</b>: the number of historical detections it represents. The full rules are in <code>rules/REGLAS_ZONAS_v4.md</code>.',
  h3='3. How it is calibrated', pasos=[
   '<b>FWI at each point.</b> ERA5 meteorology (Copernicus) at 12:00 local time and rainfall of the previous 24 hours, 2012–2025. A single engine for history and for the daily computation.',
   '<b>FWI of the ecoregion.</b> For each day, the average FWI of its points weighted by each point\'s weight.',
   '<b>Strong-fire days.</b> For each ecoregion, the days on which the number of detections is in the top 10 % of its days with fire.',
   '<b>Occurrence threshold</b> (criterion of the SNMF guide for FWI analysis). Classes start at the FWI at which the ecoregion\'s strong fires actually occurred: Moderate, High, Very high and Extreme at the 10th, 25th, 50th and 75th percentiles of the ecoregion\'s FWI on its strong-fire days. Below the 10th percentile the class is Low.',
   '<b>Minimum sample.</b> An ecoregion with fewer than 300 strong-fire days does not have enough sample and uses the thresholds of a group with a similar regime (column “Thresholds” in Table 1). The rule was written down before computing.',
   '<b>Province = summary.</b> Province level = average of the levels (0 to 4) of its ecoregions, weighted by the share of the province\'s historical fire occurring in each (Table 2), rounded to the nearest integer.',
   '<b>Daily computation.</b> The daily run uses Open-Meteo, which does not give the same number as ERA5, especially in mountains. Before averaging, each point\'s FWI is mapped to its ERA5 equivalent by quantile mapping fitted point by point over the period in which both sources exist (2021–2026). The Drought Code starts from the point\'s actual ERA5 value.'],
  t1='Table 1. Thresholds by ecoregion: FWI (ERA5 scale) at which each class starts.', c1=['Ecoregion', 'Points', 'Strong-fire days', 'Moderate', 'High', 'Very high', 'Extreme', 'Thresholds'],
  t2='Table 2. Weight of each ecoregion in each province\'s summary (% of the province\'s historical fire; those at 1 % or more are listed).', c2=['Province', 'Ecoregions and weight'],
  h4='4. Verification', p4='The rules were registered before measuring. Thresholds were calibrated on 2012–2021 and tested out of sample from January 2022 to October 2026, by province-day, against each province\'s strong-fire days. The measure is the Peirce skill score (hit rate minus false-alarm rate) of the “High or above” alarm; the 95 % confidence interval comes from resampling months.',
  c3=['', 'Previous scheme', 'By ecoregion', 'Difference [95 % CI]'], pais='Country',
  p4b='Under the previous scheme (thresholds by sub-region, province equal to its worst zone) a province was at “High or above” on {a0} % of days; under the ecoregional scheme, on {a1} %. Most of the gain (+0.173 nationwide) comes from replacing the worst zone by the fire-weighted average; the ecoregion as a unit adds +0.023 (+0.063 in the NEA, significant). The full tables, and the two earlier proposals that failed their evaluation, are in <code>method/METODO_v4.md</code> and <code>evaluation/</code>.',
  h5='5. Limitations', lim=['The index is weather-only: it does not account for fuel load, topography or the curing of live grasslands.', 'Thresholds are GEOFUEGO\'s own estimate. SNMF does not publish its own. The official danger map is published by SNMF and the National Weather Service (SMN).', 'Five ecoregions (Yungas, Puna, High Andes, Patagonian Forests, South Atlantic Islands) borrow thresholds because of a short sample: their classes are the least firm.', 'The provincial summary is an average: a province can sit in an intermediate class with one ecoregion in a high class. That is why the map always shows the class of each ecoregion.', 'Ecoregions describe potential vegetation. Where agricultural burning dominates they describe climate well, not the current fuel.'],
  h6='6. Related work', ant='Adjusting FWI thresholds to each region is established practice, and this note does not claim to be the first to use ecological units. Kudláčková et al. (2024) review 750 papers and propose FWI classes for 18 global environmental zones. Ellis, Bowman and Williamson (2024) estimate flammability thresholds across 772 ecoregions. In Argentina, Maturano et al. (2026, preprint) fit thresholds for seven environmental regions of Córdoba delineated by clustering. Naim et al. (2026) describe the FWI before wildfires in six ecoregions of Sumatra. What is specific to this work is the use of the official national ecoregion map, whole across provincial borders; the SNMF occurrence criterion; the registration of the rules before measuring; and the publication of the whole chain, including the proposals that failed.',
  h7='Sources', cita='How to cite'),
}
REFS = ['Burkart, R., Bárbaro, N. O., Sánchez, R. O. y Gómez, D. A. (1999). <i>Eco-regiones de la Argentina</i>. Administración de Parques Nacionales, Buenos Aires.',
        'Ministerio de Ambiente y Desarrollo Sostenible (2021). <i>Ecorregiones de la Argentina</i> (capa areas_protegidas:ecoregiones2021). geo.ambiente.gob.ar',
        'Van Wagner, C. E. (1987). <i>Development and Structure of the Canadian Forest Fire Weather Index System</i>. Canadian Forestry Service, Forestry Technical Report 35.',
        'Servicio Nacional de Manejo del Fuego. <i>Mapas de peligro de incendios forestales</i>. smn.gob.ar/sites/default/files/mapasdepeligro.pdf',
        'Oyarzabal, M. et al. (2018). Unidades de vegetación de la Argentina. <i>Ecología Austral</i> 28:40–63. doi:10.25260/EA.18.28.1.0.399',
        'Kudláčková, L. et al. (2024). <i>Environmental Research Letters</i>. doi:10.1088/1748-9326/ad97cf',
        'Ellis, T. M., Bowman, D. M. J. S. y Williamson, G. J. (2024). <i>Ecography</i>. doi:10.1111/ecog.07127',
        'Maturano et al. (2026). Preprint SSRN. doi:10.2139/ssrn.7267699',
        'Naim et al. (2026). <i>E3S Web of Conferences</i>. doi:10.1051/e3sconf/202673602001',
        'Hersbach, H. et al. (2020). ERA5. Copernicus Climate Change Service · NASA FIRMS, VIIRS S-NPP 375 m.']

def nota(lang):
    t = T[lang]; n = 'nombre_es' if lang == 'es' else 'nombre_en'; img = os.path.basename(mapa(lang))
    f1 = ''.join(f"<tr><td><b>{html.escape(E[k][n])}</b></td><td>{len(E[k]['zonas'])}</td><td>{E[k]['dias_fuertes_2012_2025']}</td>" + ''.join(f'<td>{num(c, lang)}</td>' for c in E[k]['cortes']) + f"<td>{ORI[lang][E[k]['cortes_origen']]}</td></tr>" for k in orden)
    f2 = ''.join(f"<tr><td><b>{html.escape(p)}</b></td><td>" + ' · '.join(f"{html.escape(E[k][n])} {round(w * 100)} %" for k, w in sorted(P[p].items(), key=lambda kv: -kv[1]) if w >= 0.01) + '</td></tr>' for p in sorted(P))
    DIF = {'pais': 0.196, 'Centro': 0.220, 'NOA': 0.165, 'NEA': 0.160, 'Patagonia': 0.215}   # diferencias de la evaluación (sobre valores sin redondear), data/evaluacion_fwi_ecorregional.md
    regs = [(t['pais'], V['pss_alto_pais']['produccion_v3'], V['pss_alto_pais']['ecorregional'], [0.154, 0.229], DIF['pais'])] + [(({'Centro': 'Centre'}.get(r, r)) if lang == 'en' else r, V['por_region'][r]['v3'], V['por_region'][r]['ecorregional'], V['por_region'][r]['dif_ic95'], DIF[r]) for r in ['Centro', 'NOA', 'NEA', 'Patagonia']]
    f3 = ''.join(f"<tr><td><b>{r}</b></td><td>{num(a, lang, 3)}</td><td><b>{num(b, lang, 3)}</b></td><td>+{num(d, lang, 3)} [+{num(ic[0], lang, 3)}, +{num(ic[1], lang, 3)}]</td></tr>" for r, a, b, ic, d in regs)
    cl = ''.join(f'<span class="cl" style="background:{c}">{(es if lang == "es" else en)}</span>' for es, en, c in CL)
    th = lambda cs: '<tr>' + ''.join(f'<th>{c}</th>' for c in cs) + '</tr>'
    h = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{t['titulo']}</title><style>
@page{{size:A4;margin:17mm 16mm 16mm}} body{{font:10.15pt/1.44 -apple-system,'Helvetica Neue',Arial,sans-serif;color:#1a1a1a;margin:0}}
h1{{font-size:21pt;margin:0 0 3px}} .sub{{font-size:12pt;color:#444;margin:0 0 6px}} .aut{{font-size:9pt;color:#666;margin:0 0 12px;padding-bottom:9px;border-bottom:1px solid #ccc;text-align:left}} a{{color:#1a4f8b;text-decoration:none}}
h2{{font-size:12.6pt;margin:12px 0 5px;break-after:avoid}} p{{margin:0 0 7px;text-align:justify}} .res{{background:#f4f6f8;border-left:3px solid #d7301f;padding:9px 12px;margin:0 0 6px}}
table{{border-collapse:collapse;width:100%;font-size:8.8pt;line-height:1.3;margin:4px 0 10px}} th,td{{border-bottom:1px solid #ddd;padding:1.5px 6px;text-align:left;vertical-align:top}} th{{background:#f0f2f4;font-weight:600}}
td:nth-child(n+2){{white-space:normal}} .num td:nth-child(n+2):not(:last-child){{text-align:right}} .num th:nth-child(n+2):not(:last-child){{text-align:right}}
.cap{{font-size:8.8pt;color:#444;margin:2px 0 4px;font-weight:600;break-after:avoid}} figure{{margin:6px 0 4px;text-align:center;break-inside:avoid}} figure img{{height:98mm;width:auto}} figcaption{{font-size:8.8pt;color:#444}}
ol{{margin:0 0 6px;padding-left:19px}} li{{margin:0 0 4px;text-align:justify}} ul{{margin:0 0 6px;padding-left:17px}} code{{font-size:8.8pt;background:#f0f2f4;padding:0 3px;border-radius:3px}}
.cl{{display:inline-block;color:#fff;font-weight:700;font-size:8.6pt;padding:2px 10px;margin-right:4px;border-radius:3px}} .refs li{{font-size:8.3pt;line-height:1.3;text-align:left;margin-bottom:1px}} tr{{break-inside:avoid}}
.pie{{font-size:8.6pt;color:#555;border-top:1px solid #ccc;margin-top:10px;padding-top:6px}}</style></head><body>
<h1>{t['titulo']}</h1><p class="sub">{t['sub']}</p><p class="aut">{t['autor']} · DOI <a href="https://doi.org/{DOI}">{DOI}</a></p>
<p class="res">{t['resumen']}</p><p style="margin:8px 0 2px">{cl}</p>
<h2>{t['h1']}</h2><p>{t['p1']}</p><figure><img src="{img}"><figcaption>{t['fig']}</figcaption></figure>
<h2>{t['h2']}</h2><p>{t['p2']}</p>
<h2>{t['h3']}</h2><ol>{''.join(f'<li>{x}</li>' for x in t['pasos'])}</ol>
<p class="cap">{t['t1']}</p><table class="num">{th(t['c1'])}{f1}</table>
<p class="cap" style="break-before:page">{t['t2']}</p><table>{th(t['c2'])}{f2}</table>
<h2>{t['h4']}</h2><p>{t['p4']}</p><table class="num">{th(t['c3'])}{f3}</table><p>{t['p4b'].format(a0=round(V['alarma_pais']['produccion_v3'] * 100), a1=round(V['alarma_pais']['ecorregional'] * 100))}</p>
<h2>{t['h5']}</h2><ul>{''.join(f'<li>{x}</li>' for x in t['lim'])}</ul>
<h2>{t['h6']}</h2><p>{t['ant']}</p>
<h2>{t['h7']}</h2><ol class="refs">{''.join(f'<li>{r}</li>' for r in REFS)}</ol>
<p class="pie"><b>{t['cita']}:</b> Kovacevic, G. R. (2026). <i>Ecoregion-based Fire Weather Index danger classes for Argentina: pre-registered rules, calibration and out-of-sample evaluation</i> (1.0.0). Zenodo. https://doi.org/{DOI} · CC BY 4.0 · sha256 {CAL['sha256'][:16]}…</p>
</body></html>"""
    hp = f'{OUT}/nota_{lang}.html'; open(hp, 'w').write(h)
    pdf = f"{OUT}/{'NOTA_METODO_FWI_ecorregional_ES' if lang == 'es' else 'METHOD_NOTE_FWI_ecoregional_EN'}.pdf"
    subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf}', 'file://' + os.path.abspath(hp)], check=True, capture_output=True, timeout=120)
    os.remove(hp); return pdf
for lang in ('es', 'en'): print(nota(lang))
