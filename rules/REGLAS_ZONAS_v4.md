# Zonas de fuego v4.1: reglas pre-registradas

**Estado: FIRMADAS por German Kovacevic el 17/11/2026 (en chat: "Perfecto. Avancemos", en respuesta a la consulta explícita de firma).** Desde ahora, estas reglas no cambian después de ver el
desempeño. Cualquier cambio posterior abre una versión nueva (v4.1, …) con la razón por escrito.

## Cambios v4 → v4.1 (17/11/2026, ANTES de cualquier medición de desempeño)

German autorizó cambiar las reglas "las veces que hagan falta para tener un producto serio y confiable". Límite que
se mantiene: **ningún cambio después de ver el desempeño** (R7). Cada cambio surgió de aplicar las reglas y mirar los
mapas y los controles de calidad, no el hindcast.

| # | Regla | Problema al aplicarla | Cambio |
|---|---|---|---|
| 1 | R3.1 | Ecorregiones (MAyDS) y unidades (Oyarzabal) no están anidadas (ej.: Selva de Transición 54 % Chaco Seco / 46 % Yungas). Cruzarlas fabricaba astillas de borde: 151 zonas | Cada unidad pertenece a su **ecorregión dominante por superficie** y solo puede partir esa (→ 108) |
| 2 | R3 | El piso "≥ 100 focos y ≥ 2 %" pensado para rescatar regímenes también partía regímenes (Santa Cruz: 8 zonas en la misma estepa) | **Partir** (unidad o isla) exige **≥ 5 %** del total provincial; el piso solo rescata regímenes (→ 91) |
| 3 | R2 | Con el padrón de pozos, la estepa fueguina queda con 91 focos de vegetación en 13 años (< 100) y perdía su zona, a pesar de ser un régimen climático distinto del bosque | Piso de rescate **≥ 50 focos y ≥ 2 %**. Medido: en el resto del país no agrega ningún régimen. El umbral del GFI sale de la climatología de la zona, no del conteo de focos |
| 4 | R3.2 | Las islas se evaluaban por fuera de su régimen y una islita de Malvinas (75 focos) se escapaba como "régimen" | Las islas parten **dentro** de su régimen, con el mismo ≥ 5 %; lo que no califica va a la zona más cercana del mismo régimen |
| 5 | R4.3 (nueva) | En cuencas petroleras quedan focos industriales que ningún filtro por pozo saca sin borrar fuego real en el norte (probadas 8 variantes de R1(c), `tools/auditoria_zonas/10_variantes_r1c.py`) | Una zona con ≥ 15 % de fuentes fijas alrededor existe solo si sus focos limpios son **≥ 10 puntos más estacionales** (4 meses pico) que esas fijas; si no, sus focos van a la zona más cercana. Cae: Neuquén Monte (43 % vs 41 %) y Santa Cruz mata negra (46 % vs 42 %). Pasan: Chubut estepa (64 vs 44), golfo San Jorge (63 vs 50), estepa fueguina (63 vs 48) |

Resultado v4.1: **90 zonas** (v3: 115). Tierra del Fuego sale con 4 zonas por regla general (estepa, bosque, Isla
Soledad, Gran Malvina), en los mismos lugares que producción. Generador: `tools/auditoria_zonas/07_zonas_v4.py --split5 --piso=50`.

## Para qué sirve una zona

Cada zona es el **lugar donde GeoFuego mide el tiempo meteorológico** (DC para el GFI y FWI para el semáforo) y contra
qué historia lo compara. Por eso tiene que ser **homogénea en clima y en combustible**. Es el mismo criterio de las
áreas de peligro de los sistemas operativos (NFDRS de Estados Unidos, ecozonas de Canadá, calibración regional del
SNMF). La v3 (k-means de 5 zonas por provincia sobre la masa de focos) agrupaba por *cantidad* de fuego, no por
*régimen*. Esta versión corrige eso.

## R0 · Insumos (congelados)

| Insumo | Fuente | Huella |
|---|---|---|
| Focos | NASA FIRMS VIIRS S-NPP 2012–2024, `confidence != l`, `type == 0`; archivo Argentina + archivo `Falkland_Islands` (Islas Malvinas) | `~/.openclaw/data/firms_ar`, `firms_malvinas` |
| Provincias | IGN (`worker/src/provincias_pip.js`) | — |
| Ecorregiones (nivel 1, **oficial**) | Ministerio de Ambiente, capa `areas_protegidas:ecoregiones2021` (Burkart et al. 1999, act. 2021), 18 ecorregiones | sha256 `17998a71d79c6ed3…` |
| Unidades de vegetación (nivel 2, **científico**) | Oyarzabal et al. 2018, *Ecología Austral* 28:40–63, doi 10.25260/EA.18.28.1.0.399, Apéndice 3, 50 unidades | sha256 KML `e8f938ab220abc7b…` |
| Pozos de hidrocarburos | Secretaría de Energía, datos abiertos, "Capítulo IV – Pozos" | huella al bajarlo |
| Meteorología | ERA5 (Copernicus CDS, `reanalysis-era5-single-levels-timeseries`), mismo método del backfill | — |

## R1 · Fuentes fijas (una sola regla para todo el país)

Un foco **no es fuego de vegetación** si cumple alguna de estas condiciones:
- (a) Está a ≤ `radio_m` de una fuente de la máscara curada `worker/src/fuentes_fijas.json`.
- (b) Su celda de 0,02° tiene focos en **≥ 9 meses distintos dentro de alguna ventana de 12 meses**. Es el criterio nacional vigente.
- (c) Su celda de 0,02° tiene focos en **≥ 6 meses distintos** de la historia **y** está a **≤ 1 km de un pozo de hidrocarburos** del padrón oficial.

La (c) objetiva lo que en Tierra del Fuego se hizo a mano (antorchas de gas del norte de la Isla Grande) y aplica igual
a Vaca Muerta, golfo San Jorge, Malargüe y la cuenca Austral. Se reconstruye la máscara curada con (a)+(c) y queda
como la fuente de verdad de producción.

## R2 · Régimen de fuego = ecorregión dentro de la provincia

Una ecorregión de la provincia es un **régimen con zona propia** si sus focos limpios (después de R1) cumplen:
**≥ 5 % del total provincial**, **o bien ≥ 100 focos y ≥ 2 %**.

El 5 % mide relevancia. El piso de 100 focos y 2 % deja entrar regímenes reales en provincias con poco fuego (la estepa
fueguina, el bosque andino de Río Negro) sin traer restos de 0,1 % de las provincias grandes. Este umbral se fijó
mirando **la cantidad de regímenes que genera** (57 → 69 en todo el país), **no el desempeño**.

## R3 · Partición dentro del régimen

1. **Unidades de vegetación.** Dentro de un régimen, cada unidad de Oyarzabal que por sí sola cumple el umbral de R2
   (sobre el total provincial) tiene zona propia. Las unidades que no lo cumplen se suman a la zona de su régimen.
2. **Territorio insular.** Una isla o grupo de islas separadas por mar del resto de la provincia es una unidad aparte
   si cumple R2 (Isla Soledad y Gran Malvina; la Isla de los Estados no lo cumple).
3. No hay cantidad fija ni máxima de zonas por provincia. La cantidad sale de R2 y R3.

## R4 · Ubicación y peso

- **Centroide**: media de los focos limpios de la zona.
- **Corrección de centroide**: si el centroide cae **fuera** del polígono de su zona, o en una celda de 0,1° sin focos
  limpios, se mueve al centro de la celda de 0,1° con más focos limpios de la zona que esté más cerca del centroide
  original. Evita centroides en lagunas, en el mar o en medio de una media luna.
- **Peso**: fracción de los focos limpios de la provincia que caen en la zona. Los focos de regímenes sin zona propia
  (R2) se asignan a la zona más cercana.
- **CABA**: queda con 1 zona y la nota de "el indicador no aplica", como hoy.

## R5 · Meteorología de la zona

Serie ERA5 en el centroide, con el mismo método que hoy. *Fase 2, evaluada aparte*: agregado de las celdas ERA5 de la
zona ponderadas por focos. No entra en esta versión, para no mezclar dos cambios en una misma evaluación.

## R5b · Subregiones del Semáforo FWI (agregada y FIRMADA por German el 17/11/2026, antes de medir)

La subregión de clases FWI de cada zona es el grupo de ecorregiones de su régimen (tabla en `docs/METODO_v4.md` §5.2):
NEA húmedo · Chaco Seco · Yungas · Árido (Monte, Puna y Andes) · Centro · Patagonia estepa · Patagonia húmeda.
Muestra mínima: ≥ 300 días de fuego fuerte en 2012–2021. Si una subregión no la reúne, se une así, sin mirar
resultados: Yungas → Chaco Seco · Patagonia húmeda → Patagonia estepa · Árido → Chaco Seco · Centro → Chaco Seco.

## R5c · Semáforo FWI por ecorregión (registrada 17/11/2026, ANTES de correrla; pedido de German)

Motivo: la evaluación de v4.1 mostró que la clase de la provincia por "peor zona" depende de cuántas zonas tiene (más
zonas, más alarma). La unidad pasa a ser la **ecorregión entera**, sin cortes por provincia.

- **Puntos**: las 90 zonas v4.1; cada una pertenece a la ecorregión de su régimen.
- **Día fuerte**: focos limpios ≥ p90 de los días con foco (2012–2021).
- **E1 (FWI ecorregional único)**: FWI diario de la ecorregión = promedio del FWI de sus puntos ponderado por los focos
  limpios de cada punto (2012–2021). Umbrales de la ecorregión = p10/p25/p50/p75 de ese FWI en los días fuertes de la
  ecorregión entera. Todas las provincias ven la misma clase para una ecorregión.
- **E2 (umbral ecorregional, FWI local)**: umbrales = p10/p25/p50/p75 del FWI de los puntos de la ecorregión en sus días
  fuertes (el método de producción, con subregión = ecorregión). Cada punto se clasifica con su FWI local; la clase de
  la ecorregión dentro de una provincia es el promedio ponderado por focos de sus puntos en esa provincia.
- **Muestra**: una ecorregión con < 300 días fuertes usa los umbrales de su grupo R5b; si el grupo tampoco llega, los
  del grupo de respaldo de R5b.
- **Provincia**: nivel = redondeo (medio hacia arriba) del promedio de los niveles de sus ecorregiones, ponderado por la
  fracción de focos limpios de la provincia en cada ecorregión (2012–2021). No hay "peor zona".
- **Evaluación**: la misma de v4.1 (fuera de muestra 2022-01 → 2026-10, provincia-día, blanco = día fuerte de
  provincia, PSS ≥ Alto con IC por bootstrap de meses). Aceptación: ninguna de las 4 regiones empeora en forma
  significativa contra producción. Se informan E1 y E2; ninguna se retoca después de ver el resultado.

**Resultado de R5c (17/11/2026, `tools/auditoria_zonas/data/evaluacion_fwi_ecorregional.md`)**: E1 y E2 pasan. PSS
de «Alto o más» en el país 0,314 → **0,510** con E1 (+0,196 [+0,154, +0,229]) y 0,488 con E2; las cuatro regiones
mejoran en forma significativa. La mayor parte de la mejora (+0,173) viene de reemplazar la peor zona por el promedio
ponderado por fuego; la ecorregión agrega +0,023 (NEA +0,063, significativo). **German adopta E1** para el Semáforo.
La v4.1 del Semáforo con peor zona y subregiones R5b **no pasó** (`evaluacion_fwi.md`: empeoran Centro y Patagonia)
y queda descartada.

## R6 · Escalación neutral a la cantidad de zonas

> **DESCARTADA (17/11/2026).** En la evaluación (`evaluacion_gfi.md`) R6 baja el Peirce del GFI de 0,263 a 0,137
> (Δ −0,124 [−0,179, −0,073]). El GFI no cambia: zonas, regla y calibración 3.0 quedan como en producción. El texto
> de la regla se conserva como registro.


Se mantiene el principio de **no promediar**: cualquier zona puede escalar la provincia.
- Para cada zona y cada día, el **percentil** de la media móvil de 30 días del DC se calcula contra la climatología de
  esa zona en ese mes calendario (todos los días del mes, 2012–2024).
- **Estadístico provincial** S = el **máximo** de esos percentiles entre las zonas.
- La provincia escala un escalón si **S > T_P**. T_P es el umbral propio de cada provincia, elegido para que en
  2012–2024 la provincia escale el **15,4 % de los meses** (fin de mes). Es la tasa que hoy tiene una zona sola, así que
  una provincia de 1 zona se comporta como ahora y una de 6 zonas no escala más que una de 2.
- La zona que dispara es la del máximo, y el producto la nombra como hoy.
- En la verificación dejando un año afuera, T_P se recalcula sin ese año.

## R7 · Evaluación (definida antes de mirar)

Diseño 2×2 para atribuir cada efecto: {zonas v3, zonas v4} × {regla v3, regla R6}. Todo en provincia-mes, 2012–2024,
con focos limpios (R1) para las cuatro variantes.
- **Métricas**: tasa de escalación, precisión (actividad por encima de la mediana de la provincia en ese mes),
  detección (POD) y **Peirce**, con IC 95 % por bootstrap de bloques anuales; verificación dejando un año afuera; caso
  testigo Delta 2020.
- **Criterio de aceptación de v4** (zonas v4 + R6 contra producción v3):
  1. El IC 95 % de la diferencia de Peirce no es enteramente negativo (no empeora de forma significativa).
  2. Ninguna zona v4 tiene banderas de la auditoría (fuente fija ≥ 15 %, centroide sin focos, pureza de ecorregión < 60 %).
- La decisión final es de German, con la tabla 2×2 completa a la vista. Si v4 empeora, no se publica, y se informa igual.

## R8 · Lo que se regenera si se aprueba

GFI 3.x → calibración 4.0 (umbrales DC por zona, `enso v2.zonas`), clases FWI SNMF (`tools/fwi_snmf`), historia
Open-Meteo de las zonas nuevas (`om_diario`), mapeo de cuantiles del vivo, pronóstico del mes que viene, hexágonos,
método ES/EN, minion, tests de paridad, y una **nueva versión en Zenodo** que documente v3 → v4. Producción no se toca
hasta la aprobación.

## Limitaciones declaradas

- Las ecorregiones y las unidades de vegetación describen la vegetación **potencial**. En la Pampa, el Chaco y la zona
  cañera, buena parte del fuego es quema agrícola sobre tierra transformada. Para el clima siguen siendo adecuadas; el
  combustible actual (por ejemplo, con MapBiomas Argentina) queda fuera de esta versión.
- Un punto ERA5 por zona (ver R5).
- El padrón de pozos cubre hidrocarburos. Otras fuentes industriales siguen dependiendo de (a) y (b).

---
Firma: German Kovacevic · Fecha: 17/11/2026 (aprobación en chat, sesión GeoFuego)
