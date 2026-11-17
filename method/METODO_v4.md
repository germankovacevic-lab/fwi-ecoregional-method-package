# GeoFuego v4: método integrado de zonas de fuego, Semáforo FWI e Índice GeoFuego (GFI)

**Estado (17/11/2026): evaluado.** Resultado de la evaluación (§7): el **Semáforo FWI pasa a calcularse por
ecorregión** (regla R5c, variante E1) y el **GFI no cambia** (sigue en 3.0 con las zonas y la regla de producción).
Las reglas pre-registradas y su historia de cambios están en `docs/REGLAS_ZONAS_v4.md` (v4.1). Lo marcado **[v4]**
cambia respecto de producción v3; lo marcado **[=]** se mantiene.

---

## 1. Principio

GeoFuego publica dos índices sobre el mismo territorio:

| Índice | Pregunta | Horizonte | Escala pública |
|---|---|---|---|
| **Semáforo FWI** | ¿Qué tan peligroso es hoy el tiempo para el fuego? | día, 24/48/72 h | 5 clases del SNMF (Bajo … Extremo) |
| **Índice GeoFuego (GFI)** | ¿Qué tan riesgosa viene la temporada? | estacional | 3 niveles (BAJO / MEDIO / ALTO) |

Los dos miden tiempo meteorológico, y el tiempo hay que medirlo **donde está el combustible que arde**. Una **zona de
fuego** es ese lugar: un punto de medición meteorológica representativo de un **régimen de fuego** (clima +
vegetación) dentro de una jurisdicción, con su propia historia para comparar. El Semáforo FWI usa las zonas v4.1 (§3)
agrupadas por ecorregión; el GFI conserva las 115 zonas de la versión 3.0.

## 2. Insumos

| Insumo | Fuente | Uso |
|---|---|---|
| Focos de calor | NASA FIRMS VIIRS S-NPP, 2012–2024 (`confidence ≠ l`, `type = 0`); archivo Argentina + archivo `Falkland_Islands` (Islas Malvinas) | ubicar zonas, pesos, verificación |
| Límites provinciales | IGN | jurisdicción de cada foco |
| Ecorregiones | Ministerio de Ambiente, `ecoregiones2021` (Burkart et al. 1999, act. 2021) — **referencia oficial** | regímenes de fuego |
| Unidades de vegetación | Oyarzabal et al. 2018, *Ecología Austral* 28:40–63, doi 10.25260/EA.18.28.1.0.399 | partición de regímenes |
| Pozos de hidrocarburos | Secretaría de Energía, Capítulo IV – Pozos (85.856 con coordenadas) | fuentes fijas |
| Meteorología histórica | ERA5 (Copernicus CDS), por punto, 12:00 locales + lluvia 24 h, 2011-09-30 → 2026-10-30 | historia, umbrales |
| Meteorología en vivo | Open-Meteo (pronóstico + 92 días de pasado) | cálculo diario |
| ENSO | NOAA CPC, ONI trimestral | término ENSO del GFI |

## 3. Zonas de fuego [v4, solo para el Semáforo FWI]

Resumen de las reglas (texto completo y justificación en `REGLAS_ZONAS_v4.md`):

1. **Fuentes fijas fuera.** Un foco no es vegetación si está en la máscara curada, si su celda de 0,02° arde 9 de
   cada 12 meses, o si arde ≥ 6 meses distintos a ≤ 1 km de un pozo oficial. Sale el 2,0 % de los focos del país.
2. **Régimen = ecorregión dentro de la provincia** con ≥ 5 % de sus focos limpios, o ≥ 50 focos y ≥ 2 % (rescate
   de regímenes en provincias con poco fuego).
3. **Partición**: una unidad de vegetación (asignada a su ecorregión dominante) o una isla separada por mar parten
   un régimen solo si reúnen ≥ 5 % de los focos de la provincia. No hay cantidad fija de zonas.
4. **Ubicación**: centroide de los focos limpios; si cae fuera de su zona o en una celda sin fuego, se corre a la
   celda de fuego denso más cercana. **Peso** = fracción de los focos limpios de la provincia.
5. **Control de fuentes residuales**: una zona rodeada de ≥ 15 % de fuentes fijas existe solo si sus focos limpios
   son ≥ 10 puntos más estacionales que esas fuentes.

Resultado: **90 zonas** (v3: 115), entre 2 y 7 por provincia. El Semáforo usa **89 puntos**: la zona de CABA queda
afuera (sin fuego de vegetación). Cada punto lleva su ecorregión, la unidad de vegetación si corresponde y su peso.

## 4. Meteorología de cada punto [=, con los puntos v4]

- **Historia**: serie ERA5 diaria en el centroide (12:00 hora local; humedad relativa de t2m y d2m; viento a 10 m;
  lluvia de las 24 h previas), 2011-09-30 → 2026-10-30. Mismo método del backfill v3 (0 diferencias verificadas).
- **Vivo**: Open-Meteo en el mismo punto, ventana de 92 días para arrastrar los códigos de humedad, con el DC
  inicial tomado de ERA5: el dato del día previo a la ventana si está cargado (tabla `gfi_dc_era5`, territorios `AR` y
  `AR_FWI`) y, si falta, el DC climatológico ERA5 del mes del punto. Medido en 2022–2026
  (`tools/auditoria_zonas/21_siembra_dc.mjs`): con la siembra climatológica la clase de la ecorregión cambia en el
  1,1 % de los ecorregión-días (nunca dos clases) y la de la provincia en el 1,2 % de los provincia-días.
- **Puente vivo → historia**: el vivo no da el mismo número que ERA5, sobre todo en montaña. Por zona se ajusta un
  **mapeo de cuantiles** (vivo → ERA5) sobre el período en que existen los dos; todo umbral se aplica en escala ERA5.
  Las zonas nuevas necesitan su historia Open-Meteo (`tools/fwi_argentina/01_om_historico.mjs`) antes de publicar.
- **Fase 2 (fuera de v4)**: reemplazar el punto por el promedio de las celdas ERA5 de la zona ponderadas por focos.

## 5. Semáforo FWI [v4: por ecorregión]

### 5.1 Cálculo por punto [=]
Sistema canadiense FWI (Van Wagner 1987) con la tabla del largo del día del DMC por latitud (cffdrs), motor único
`worker/src/fwi.js` para historia y vivo. En cada uno de los 89 puntos se calcula el FWI del día y el de las próximas
24/48/72 h, y se lo lleva a su equivalente ERA5 (§4).

### 5.2 Unidad: la ecorregión [v4]
La unidad del Semáforo es la **ecorregión entera** del mapa oficial «Ecorregiones de la Argentina» (Ministerio de
Ambiente y Desarrollo Sostenible, 2021, sobre Burkart et al. 1999), sin cortes en los límites provinciales. Son 16
(quedan afuera Mar Argentino y Antártida).

- **FWI de la ecorregión** = promedio del FWI equivalente ERA5 de sus puntos, ponderado por los focos limpios
  históricos de cada punto.
- **Clases** del SNMF con **umbral de ocurrencia**: Moderado / Alto / Muy alto / Extremo arrancan en los percentiles
  10/25/50/75 del FWI de la ecorregión en sus **días de fuego fuerte** (focos limpios ≥ p90 de los días con foco).
  Calibración de producción con ERA5 2012–2025 (`worker/src/fwi_ecorregional.json`); la evaluación usó 2012–2021.
- **Muestra**: una ecorregión con menos de 300 días fuertes usa los umbrales de su grupo de régimen parecido
  (`cortes_origen` en el JSON): Yungas → Chaco Seco; Puna y Altos Andes → grupo árido; Bosques Patagónicos e Islas
  del Atlántico Sur → Estepa Patagónica.

### 5.3 Provincia = resumen [v4]
Nivel de la provincia = redondeo (medio hacia arriba) del promedio de los niveles de sus ecorregiones, ponderado por
la fracción de los focos limpios de la provincia en cada una. **Se elimina la "peor zona"**: dejaba a las provincias
en «Alto o más» el 63 % de los días. La regla "el peligro no se promedia" se respeta mostrando en el mapa la clase
de **cada ecorregión** además del resumen provincial.

Respaldos del vivo (`worker/src/fwi_payload.js`): una ecorregión informa con cuántos puntos se calculó; una provincia
no se publica si las ecorregiones con dato reúnen menos del 50 % de su fuego histórico; el estado no se pisa si
responden menos del 75 % de los puntos.

Control externo que se mantiene: la tabla publicada por Córdoba (6/15/28/46, OHMC/IDECOR).

## 6. Índice GeoFuego (GFI)

### 6.1 Término ENSO [=]
Factor regional por fase ENSO a 3 meses (ONI), medido en la ventana de temporada propia de cada región (NOA directo
y robusto; NEA directo y sugestivo; Centro sin señal medible; Patagonia inversa y sugestiva). Fija el nivel base de
la provincia. No depende de las zonas.

### 6.2 Término de sequía [=]
Sin cambios respecto del GFI 3.0: una zona dispara cuando la media móvil de 30 días de su DC supera su umbral del
mes, y cualquier zona escala la provincia. La regla propuesta para v4 (R6: máximo de percentiles zonales contra un
umbral provincial de tasa común) **no pasó** la evaluación y quedó descartada (§7).

### 6.3 Puerta de temporada y regla nacional [=]
- Puerta de temporada por la climatología mensual de la jurisdicción (ventana 4-3-2-1, r < 1 y mes < 8 %).
- Regla nacional: el país sube un escalón si **≥ 2/3 de las jurisdicciones** escalan por sequía en el mismo mes.

### 6.4 Productos derivados [=]
Pronóstico del mes que viene, hexágonos del GFI y CABA "no aplica": sin cambios.

## 7. Evaluación y resultados

Cada regla se registró en `REGLAS_ZONAS_v4.md` antes de correr su evaluación.

**GFI** (`tools/auditoria_zonas/13_evaluacion_gfi.py` → `data/evaluacion_gfi.md`): diseño 2×2 {zonas v3, zonas v4.1}
× {regla v3, regla R6}, provincia-mes 2012–2024, Peirce dejando un año afuera.

| Variante | Tasa de escalación | Peirce [IC 95 %] | Δ contra producción |
|---|---|---|---|
| A · zonas v3, regla v3 (producción) | 35,5 % | 0,263 [0,189, 0,338] | — |
| B · zonas v4.1, regla v3 | 37,6 % | 0,257 [0,180, 0,328] | −0,006 [−0,025, +0,015] |
| D · zonas v4.1, regla R6 (propuesta) | 15,4 % | 0,137 [0,076, 0,199] | **−0,124 [−0,179, −0,073]** |

La propuesta empeora en forma significativa: **no se adopta**. Las zonas nuevas solas no cambian el resultado.
El GFI queda como está.

**Semáforo FWI, zonas v4.1 con peor zona y subregiones R5b** (`15_evaluacion_fwi.py` → `data/evaluacion_fwi.md`),
fuera de muestra 2022-01 → 2026-10: país 0,314 → 0,316 (sin diferencia), NEA mejora (+0,054), Centro y Patagonia
empeoran (−0,030 y −0,031, significativo). **No pasa.**

**Semáforo FWI por ecorregión, R5c** (`16_fwi_ecorregional.py` → `data/evaluacion_fwi_ecorregional.md`): calibrado
2012–2021, probado 2022-01 → 2026-10, provincia-día, blanco = día de fuego fuerte de la provincia, PSS de «Alto o
más», IC 95 % por bootstrap de meses.

| | Producción v3 | **E1 ecorregional** | Diferencia [IC 95 %] |
|---|---|---|---|
| País | 0,314 · alarma 63 % | **0,510** · alarma 30 % | +0,196 [+0,154, +0,229] |
| Centro | 0,233 | 0,453 | +0,220 [+0,159, +0,273] |
| NOA | 0,421 | 0,586 | +0,165 [+0,027, +0,258] |
| NEA | 0,362 | 0,523 | +0,160 [+0,103, +0,208] |
| Patagonia | 0,276 | 0,491 | +0,215 [+0,157, +0,263] |

**Pasa** (ninguna región empeora; las cuatro mejoran en forma significativa). Por provincia, ninguna empeora en forma
significativa; Entre Ríos, Santa Fe y Tucumán dan diferencia negativa no significativa.

Lectura honesta: la mayor parte de la mejora (+0,173 en el país) viene de **reemplazar la peor zona por el promedio
ponderado por fuego**, y se obtiene también con las zonas y umbrales de producción. La ecorregión agrega +0,023 en
el país (NEA +0,063, significativo). La variante E2 (umbral ecorregional con FWI local) da 0,488 y no se adopta.

**Paridad del motor**: `test_fwi_ecorregional_ref.py` + `test_fwi_ecorregional.mjs`, 0 niveles distintos entre la
referencia Python y el worker en 320 días (5.112 ecorregión-días, 7.360 provincia-días).

**Pendiente**: control externo contra estaciones SMN (si el SMN publica la serie diaria de FWI).

## 8. Qué cambia de v3 a v4

| Componente | v3 | v4 |
|---|---|---|
| Unidad del Semáforo FWI | 115 zonas en 7 subregiones estadísticas | 16 ecorregiones oficiales, 89 puntos |
| Clase provincial del Semáforo | peor zona | resumen: promedio de las clases de sus ecorregiones, ponderado por fuego |
| Umbrales FWI | por subregión (k-means dentro de cada región) | por ecorregión (con respaldo declarado si la muestra es corta) |
| Mapa | hexágonos por zona | ecorregiones + resumen provincial |
| Fuentes fijas (para definir puntos) | máscara curada + persistencia | + padrón oficial de pozos + control por estacionalidad |
| Malvinas | solo en TDF, a mano | por regla general (islas) |
| Meteorología | punto ERA5 / Open-Meteo | igual |
| GFI (zonas, regla, calibración 3.0) | — | **sin cambios** |

## 9. Limitaciones

- Ecorregiones y unidades describen la vegetación **potencial**. Donde domina la quema agrícola (Pampa, Chaco,
  zona cañera) son buenas para el clima pero no describen el combustible actual (MapBiomas: trabajo futuro).
- Un punto meteorológico por zona; en zonas extensas el punto es una simplificación.
- El resumen provincial es un promedio: una provincia puede quedar en clase intermedia con una ecorregión en clase
  alta. Por eso el mapa muestra siempre la clase de cada ecorregión.
- Cinco ecorregiones (Yungas, Puna, Altos Andes, Bosques Patagónicos, Islas del Atlántico Sur) no tienen muestra
  propia suficiente y usan umbrales prestados; sus clases son las menos firmes.
- El GFI indica riesgo estacional y el Semáforo peligro meteorológico; ninguno predice igniciones. La autoridad de
  alerta es del SMN y el SNMF.
- Umbrales estimados por GeoFuego; el SNMF no publica los suyos.

## 10. Reproducibilidad

`tools/auditoria_zonas/`: `01_focos.py` (focos), `07_zonas_v4.py --split5 --piso=50` (zonas v4.1), `08_mapas_v4.py`,
`09_control_fijas.py`, `10_variantes_r1c.py`, `11_descarga_era5_v4.sh` (ERA5), `12`/`14` (FWI), `13` (evaluación GFI),
`15` (evaluación FWI v4.1), `16` (evaluación ecorregional), `17` (mapa), `18` (historia Open-Meteo), `19` (vivo
emulado), `20_calibracion_fwi_ecorregional.py` (calibración de producción), `21_siembra_dc.mjs` (efecto de la siembra
del DC). Worker: `worker/src/fwi_ecorregional.js` + `.json`, `fwi_payload.js` (payload v4). Tests:
`tools/fwi_snmf/test_payload.mjs`, `test_fwi_diario.mjs`, `test_front.mjs`, `test_capas.mjs`. Insumos externos en
`~/.openclaw/data/` con su huella en `REGLAS_ZONAS_v4.md`. Se publica en Zenodo como nueva versión del método.
