# Handover: AAE-4004-lab (AAE4203 GNSS Lab 1)

Updated 2026-11-13. Master handover for all projects and sessions: `saul-gitman/MyMCP`, `docs/HANDOVER.md`.

## What you wanted to build
*Inferred from session titles and this repo's README, not a verbatim quote.* Process your own static u-blox ZED-F9P log (30 Oct 2026, `COM6___9600_261030_081848.ubx`, 8.3 min) through the course pipeline UBX → RTKCONV RINEX → GPS L1 CSVs → course `WLSE_spp.py`; produce a 3D plot (with animated GIFs), fill the course Word report template, and submit a GPS-only benchmark CSV.

## State
- Done: raw data CSVs (40,775 rows, 46 UBX message CSVs), position results, 3D plot and two GIFs, filled report `report/GXX_Lab1_Report.docx` (+ `.pdf`) built by `report/build_report.py`, benchmark baseline (1,437 of 1,534 epochs, 93.68 %).
- Open: the "Still missing before submission" checklist at the top of `README.md` (cover, photos, kit and weather details, blank "SPP − RTKPOST" column in Table 2, benchmark rows v2-v4, official benchmark numbers from the leaderboard, AI-use statement, group number).
- Also open: static scatter must show the mean as well as the median; stationary data is 8.3 min, below the 15-20 min the guide asks for (keep the disclosure); pick one name for the baseline ("V0" or "v1").
- Submission: rename `GXX` to the group number (`GROUP=G05 ./run_all.sh`), upload `results/GXX_owndata.csv` and `results/benchmark/GXX_benchmark.csv` to the TA's Google Drive folder.
- The same lab folder is also in the `FYP` repo under `AAE4203_GNSS_Lab1/` (copy, may drift from this one).

## Change log
| Date | Commit | Change |
|---|---|---|
| 10-30 | `db67616` | Lab 1 data, processing and results |
| 10-30 | `a21508d` | Animated 3D GIF of the whole log |
| 10-30 | `4cccaec` | Filled report, figures, benchmark baseline, track GIF |
| 10-30 | `09b59ff`, `ceb89c4`, `c0cbb32`, `5f023f9` | Checklist added to README, reverted, moved to `COVER.md`, moved back (final: README top) |
| 11-13 | handover | This file |

## Sessions
`session_0143oVsJAkHdZm66bSpB3Fny` UBX data processing and 3D visualization (10-30, done; also pushed to FYP) ·
`session_0143oVsJR8VDeDkHVWa2tpSZ` Lab report completion checklist (10-30, done) ·
`session_0143oVsLfP3LsbRg42MxxY8n` CSV submission files (11-06, done).

## Branches
`main` (all work); `claude/pensive-cray-bj65ft` is identical to `main` and safe to delete.
