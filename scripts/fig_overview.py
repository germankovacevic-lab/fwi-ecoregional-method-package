# Imagen resumen 16:9 (fondo blanco) para el "Default preview" de Zenodo. Uso: fig_overview.py <mapa.png> <salida.png> <DOI>
import sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
mapa, out, doi = sys.argv[1], sys.argv[2], sys.argv[3]
fig = plt.figure(figsize=(16, 9), dpi=120, facecolor='white')
ax = fig.add_axes([0.02, 0.07, 0.40, 0.86]); ax.imshow(plt.imread(mapa)); ax.axis('off')
t = fig.add_axes([0.44, 0.07, 0.54, 0.86]); t.axis('off'); t.set_xlim(0, 1); t.set_ylim(0, 1)
t.text(0, .97, 'Ecoregion-based Fire Weather Index\ndanger classes for Argentina', fontsize=27, fontweight='bold', va='top', color='#111')
t.text(0, .775, 'FWI at 89 historical fire points → averaged over the 16 official ecoregions →\nSNMF danger classes with thresholds specific to each ecoregion.\nThe province is a summary: fire-weighted average of its ecoregions.', fontsize=14.5, va='top', color='#333', linespacing=1.45)
cl = [('Low', '#2f9e6f'), ('Moderate', '#3f9be8'), ('High', '#f2c230'), ('Very high', '#f07d1a'), ('Extreme', '#e0322b')]
for i, (n, c) in enumerate(cl):
    t.add_patch(Rectangle((i * .2, .575), .19, .045, color=c)); t.text(i * .2 + .095, .5975, n, ha='center', va='center', fontsize=12.5, color='white', fontweight='bold')
t.text(0, .52, 'Out-of-sample test, 2022-01 → 2026-10 (calibrated 2012–2021)', fontsize=15.5, fontweight='bold', va='top', color='#111')
t.text(0, .47, 'Peirce skill score of the "High or above" alarm, province-day', fontsize=13, va='top', color='#555')
filas = [('Country', .314, .510), ('Centre', .233, .453), ('NOA', .421, .586), ('NEA', .362, .523), ('Patagonia', .276, .491)]
y0 = .40
for i, (n, a, b) in enumerate(filas):
    y = y0 - i * .058
    t.text(0, y, n, fontsize=14, va='center', color='#111')
    t.add_patch(Rectangle((.17, y - .017), a * .9, .015, color='#b9c0c7')); t.add_patch(Rectangle((.17, y + .001), b * .9, .015, color='#d7301f'))
    t.text(.17 + b * .9 + .012, y, f'{a:.2f} → {b:.2f}', fontsize=13.5, va='center', color='#111')
t.add_patch(Rectangle((.80, .40, ), .02, .014, color='#b9c0c7')); t.text(.827, .407, 'previous scheme', fontsize=11, va='center', color='#555')
t.add_patch(Rectangle((.80, .365), .02, .014, color='#d7301f')); t.text(.827, .372, 'ecoregional', fontsize=11, va='center', color='#555')
t.text(0, .095, 'Alarm active on 30 % of days instead of 63 %. Rules registered before measuring;\nmost of the gain comes from dropping the "worst zone" rule. Weather-only index.', fontsize=13, va='top', color='#333', linespacing=1.45)
fig.text(0.02, 0.025, f'Kovacevic, G. R. (2026) · GEOFUEGO · geofuego.com.ar · doi:{doi}', fontsize=12.5, color='#444')
fig.savefig(out, facecolor='white')
