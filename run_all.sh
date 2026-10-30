#!/usr/bin/env bash
# Rebuild every CSV and the figure from the raw UBX + RTKCONV files.
# Usage: GROUP=G05 ./run_all.sh        (needs: pip install numpy matplotlib pyubx2)
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
GROUP=${GROUP:-GXX}
LOG=COM6___9600_261030_081848

# 1. UBX -> per-message CSVs, long-form RAWX observations, broadcast Klobuchar coefficients
$PY src/ubx2csv.py data/raw/$LOG.ubx data/csv

# 2. RINEX OBS/NAV -> GPS L1 measurement matrices (Python port of course rinex2csv.m)
$PY src/rinex2csv.py data/rinex/$LOG.obs data/rinex/$LOG.nav data/csv/gps_inputs \
    --klobuchar-json data/csv/klobuchar_from_ubx.json

# 3. Course WLS solver, unchanged (GPS mode), compared with the receiver solution
(cd course_repo/Lab1 && $PY WLSE_spp.py --mode gps \
    --input-dir ../../data/csv/gps_inputs --output-dir ../../results \
    --submission "${GROUP}_owndata.csv" \
    --reference ../../data/csv/ubx_messages/NAV-HPPOSECEF.csv)

# 4. 3D figure + LLH/ENU table + static position summary
$PY src/plot_3d.py
$PY src/animate_3d.py
