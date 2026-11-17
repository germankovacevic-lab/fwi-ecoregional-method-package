# Ecoregion-based Fire Weather Index danger classes for Argentina — method package v1.0.0

DOI: 10.5281/zenodo.24326196 · Mirror: https://github.com/germankovacevic-lab/fwi-ecoregional-method-package (tag `v1.0.0`, identical to the archived package)

Daily fire-weather danger for Argentina computed **by ecoregion**: the Canadian Fire Weather Index (FWI; Van Wagner 1987) is computed at 89 historical fire points, averaged per ecoregion of the official map *Ecorregiones de la Argentina* (Ministry of Environment and Sustainable Development, 2021, after Burkart et al. 1999; 16 ecoregions), and classified into the five danger classes used by Argentina's National Fire Management Service (SNMF: Low, Moderate, High, Very high, Extreme) with thresholds specific to each ecoregion. A province is reported as a **summary** (fire-weighted average of the classes of its ecoregions), not as the unit of computation. This is the method behind the fire-danger semaphore of https://geofuego.com.ar since 17 November 2026.

This package is independent of the GeoFuego Index (GFI) seasonal method package (doi:10.5281/zenodo.24164911), which it does not modify.

## What is here

- `rules/REGLAS_ZONAS_v4.md` — the rules, **registered before each evaluation was run**, with their change history and results (Spanish). `rules/PRE_REGISTRATION.txt` lists the commit hashes and timestamps of the private development repository that back the "registered before measuring" claim.
- `method/METHOD_NOTE_FWI_ecoregional_EN.pdf` and `method/NOTA_METODO_FWI_ecorregional_ES.pdf` — **start here**: a five-page note with the map of the 16 official ecoregions and the 89 computation points, the calibration procedure step by step, the threshold table, the provincial weights and the verification. Generated from the calibration file by `scripts/nota_metodo.py`.
- `method/METODO_v4.md` — the integrated method and all evaluation results, including the two proposals that **failed** and were discarded (Spanish).
- `calibration/fwi_ecorregional.json` — the calibration file the operational product loads: ecoregion thresholds, point weights, provincial weights, per-point quantile mapping from the live source (Open-Meteo) to the ERA5 scale, monthly climatological Drought Code. `sha256` inside.
- `engine/` — `fwi.js` (FWI engine, DMC day-length by latitude as in cffdrs), `fwi_ecorregional.js` (ecoregion and province classification), `clases_snmf.js` (class names and SNMF descriptions), `fwi_payload.js` (public payload v4).
- `scripts/` — the numbered pipeline `01 … 21` (fire points, static-source screening, ERA5 download, FWI, the three evaluations, calibration, effect of the Drought Code seeding) and the Python↔JavaScript parity tests.
- `evaluation/` — outputs of the three evaluations (Markdown + JSON) and the point definitions (`zonas_v4_split5_p50.json`).
- `data/fwi_era5_points/` — daily ERA5-derived FWI components (2012 → 2026-10-30) at the 90 candidate points, as used by the evaluations. `data/era5_meteo_points/` — the ERA5 daily inputs they were computed from (12:00 local temperature, relative humidity, wind, 24-h rain). `data/live_emulated_points/` — the emulated live FWI (Open-Meteo, 92-day window) used to fit the live→ERA5 quantile mapping.
- `baseline_v3/` — the calibration files of the previous operational scheme (sub-regional thresholds, 115 zones), i.e. the baseline of the comparison.
- `method/MAPAS_puntos_por_provincia_v4.1.pdf` — 23 maps, one per province: official ecoregions, Oyarzabal (2018) vegetation units, cleaned VIIRS detections 2012–2024, and where the points sit (new points vs the 115 zones of the previous scheme). This is the visual evidence of how the points were placed against the ecoregions.
- `geo/ecorregiones_MAyDS_2021_original.geojson` — the official ecoregion layer exactly as served by the Ministry of Environment (layer `areas_protegidas:ecoregiones2021`, geo.ambiente.gob.ar; licence declared by the service: Creative Commons, free licence). `geo/ecorregiones_simplificado.geojson` is a display-only simplification of it. Details in `geo/FUENTE_ecorregiones.txt`.
- `fwi_ecoregional_overview.png` — one-page summary.

## Result (out of sample)

Thresholds calibrated on 2012–2021, tested on 2022-01 → 2026-10; unit = province-day; target = strong-fire day of the province; score = Peirce skill score (POD − POFD) of the "High or above" alarm; 95 % CI by bootstrap of months.

| | Previous operational scheme (sub-regional thresholds, province = worst zone) | Ecoregional (this package) | Difference [95 % CI] |
|---|---|---|---|
| Country | 0.314 · alarm on 63 % of days | 0.510 · alarm on 30 % of days | +0.196 [+0.154, +0.229] |
| Centre | 0.233 | 0.453 | +0.220 [+0.159, +0.273] |
| NOA | 0.421 | 0.586 | +0.165 [+0.027, +0.258] |
| NEA | 0.362 | 0.523 | +0.160 [+0.103, +0.208] |
| Patagonia | 0.276 | 0.491 | +0.215 [+0.157, +0.263] |

Honest reading: most of the gain (+0.173 nationwide) comes from **replacing the "worst zone" rule by a fire-weighted average**, and is also obtained with the previous zones and thresholds. The ecoregion as a unit adds +0.023 nationwide (NEA +0.063, significant). Two earlier proposals did not pass and are reported in `method/METODO_v4.md`: a new escalation rule for the GFI drought term (Peirce 0.263 → 0.137) and regime-based zones with the worst-zone rule (worse in Centre and Patagonia).

## Limitations

- Weather-only index: no fuel load, topography or curing of live grasslands. Thresholds are GEOFUEGO's own estimate; SNMF does not publish its own. The official danger map is published by SNMF and the National Weather Service (SMN).
- Five ecoregions (Yungas, Puna, High Andes, Patagonian Forests, South Atlantic Islands) have fewer than 300 strong-fire days and borrow thresholds from a group with a similar regime (`cortes_origen` in the calibration file). Their classes are the least firm.
- The provincial summary is an average: a province can sit in an intermediate class with one ecoregion in a high class. The product always shows the class of each ecoregion.
- Ecoregions describe potential vegetation; where agricultural burning dominates they describe climate well but not the current fuel.

## Related work

Region-specific FWI thresholds are well established; this package does not claim to be the first to use ecological units.
- Kudláčková et al. (2024), *Environ. Res. Lett.*, doi:10.1088/1748-9326/ad97cf — review of 750 papers; FWI danger classes across 18 global environmental zones.
- Ellis, Bowman & Williamson (2024), *Ecography*, doi:10.1111/ecog.07127 — flammability thresholds of a fuel-moisture index across 772 ecoregions worldwide.
- Maturano et al. (2026, preprint), doi:10.2139/ssrn.7267699 — FWI thresholds for seven environmentally homogeneous regions of Córdoba Province (Argentina), delineated by clustering, from regional FWI percentiles.
- Naim et al. (2026), *E3S Web Conf.*, doi:10.1051/e3sconf/202673602001 — FWI patterns before wildfires in six ecoregions of Sumatra; calls for ecoregion-specific thresholds.
- SNMF, *Mapas de peligro de incendios forestales* — states that thresholds are computed statistically for each zone; numbers are not public.

What is specific here: the unit is the **official national ecoregion map**, kept whole across provincial borders; thresholds follow the SNMF occurrence criterion (FWI percentiles on strong-fire days); the rules were registered before measuring; and the whole chain, including the failed proposals, is published and runs operationally.

## Reproduce

1. Fetch raw inputs: NASA FIRMS VIIRS S-NPP archive (Argentina and Falkland_Islands files), ERA5 from the Copernicus CDS, the ecoregion layer (WFS geo.ambiente.gob.ar), Oyarzabal et al. (2018) vegetation units, the Energy Secretariat well registry. Apart from the ecoregion layer (included, free licence), raw inputs are not redistributed.
2. Run `scripts/01_focos.py`, `07_zonas_v4.py --split5 --piso=50`, `11`, `12`/`14`, then `16_fwi_ecorregional.py` (evaluation) and `20_calibracion_fwi_ecorregional.py` (calibration). `data/fwi_era5_points/` lets you skip the ERA5 step.
3. Parity: `python3 scripts/test_fwi_ecorregional_ref.py && node scripts/test_fwi_ecorregional.mjs`.

What can and cannot be re-run from this package alone: the calibration thresholds, the quantile mapping and the parity tests can be recomputed from `data/` once the strong-fire days are available; the strong-fire days and the baseline score need the raw FIRMS archive (not redistributed) and the FWI series of the 115 baseline zones (regenerable with the GFI method package, doi:10.5281/zenodo.24164911). Paths inside the scripts point to the development layout (`~/.openclaw/data/…`, `worker/src/…`); adjust them to this package. The scripts are published as the record of what was run, not as a packaged library.

## License and citation

Code: MIT. Derived data, calibration and documents: CC BY 4.0 (LICENSE-DATA). Third-party material (the official ecoregion layer, ERA5, Open-Meteo, NASA FIRMS) keeps its own terms, listed in LICENSE-DATA. GEOFUEGO is a trademark of the author; the method and code are open. Cite as in `CITATION.cff`.
