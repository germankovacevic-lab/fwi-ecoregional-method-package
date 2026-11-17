#!/bin/zsh
# Paso 3 zonas v4.1: ERA5 CDS por punto (mismo método que tools/tdf_4zonas/02_descarga_cds.py, 0 dif. vs backfill),
# 2011-09-30 → 2026-10-30 (mismo corte que gfi_v2_cds). 4 en paralelo; reintenta lo que falte si se vuelve a correr.
OUT=~/.openclaw/data/gfi_v4_cds
PY=$(cd "$(dirname "$0")/../tdf_4zonas" && pwd)/02_descarga_cds.py
python3 -c "
import json; d=json.load(open('$(dirname "$0")/data/zonas_v4_split5_p50.json'))['zonas']
for v in d.values():
  for z in v: print(z['lat'], z['lon'], z['zid'])" | sort -u | while read la lo zid; do
  [ -s $OUT/meteo_$zid.csv ] || echo "$la $lo $zid"
done | xargs -P 4 -L 1 zsh -c 'python3 '"$PY"' $0 $1 America/Argentina/Buenos_Aires '"$OUT"'/meteo_$2.csv 2026-10-30 > '"$OUT"'/log/$2.txt 2>&1 || echo "FALLO $2"'
echo "listo: $(ls $OUT/meteo_*.csv 2>/dev/null | wc -l) series"
