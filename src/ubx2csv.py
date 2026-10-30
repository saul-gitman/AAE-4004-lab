#!/usr/bin/env python3
"""UBX log -> CSV, without the GUI (same parsing as course pyubx2_csv_converter_gui.py).

Outputs in OUT_DIR:
  ubx_messages/<MSG>.csv   one CSV per UBX message type (NAV-HPPOSECEF.csv is the
                           receiver solution: ecefX/Y/Z in cm, iTOW in ms).
                           Unlike the GUI, variable-length messages keep every
                           repeated-group column (the GUI keeps only the first row's).
  raw_observations.csv     UBX-RXM-RAWX in long form: one row per satellite signal
                           per epoch (pseudorange, carrier phase, Doppler, C/N0 ...).
  klobuchar_from_ubx.json  GPS broadcast ionosphere coefficients decoded from
                           UBX-RXM-SFRBX subframe 4 page 18 (RTKCONV did not write
                           them to the NAV header).

Usage:
  python src/ubx2csv.py UBX OUT_DIR
"""
import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from pyubx2 import UBXReader

GNSS = {0: 'G', 1: 'S', 2: 'E', 3: 'C', 5: 'J', 6: 'R', 7: 'I'}
SIGNALS = {  # (gnssId, sigId) -> signal name, u-blox F9 interface description
    (0, 0): 'L1C/A', (0, 3): 'L2CL', (0, 4): 'L2CM', (0, 6): 'L5I', (0, 7): 'L5Q',
    (1, 0): 'L1C/A',
    (2, 0): 'E1C', (2, 1): 'E1B', (2, 3): 'E5aI', (2, 4): 'E5aQ', (2, 5): 'E5bI', (2, 6): 'E5bQ',
    (3, 0): 'B1I D1', (3, 1): 'B1I D2', (3, 2): 'B2I D1', (3, 3): 'B2I D2', (3, 5): 'B1C', (3, 7): 'B2a',
    (5, 0): 'L1C/A', (5, 1): 'L1S', (5, 4): 'L2CM', (5, 5): 'L2CL', (5, 8): 'L5I', (5, 9): 'L5Q',
    (6, 0): 'L1OF', (6, 2): 'L2OF', (7, 0): 'L5A',
}
RAW_HEADER = ['gps_week', 'rcv_tow_s', 'gpst', 'sat', 'gnss', 'sv_id', 'sig_id', 'signal',
              'glo_freq_id', 'pseudorange_m', 'carrier_phase_cyc', 'doppler_hz', 'cn0_dbhz',
              'locktime_ms', 'pr_std_m', 'cp_std_cyc', 'do_std_hz',
              'pr_valid', 'cp_valid', 'half_cyc', 'sub_half_cyc']


def msg_to_dict(msg):
    """Flatten a UBXMessage the same way as the course GUI converter."""
    if hasattr(msg, 'to_dict'):
        return msg.to_dict()
    return {k: v for k, v in msg.__dict__.items()
            if not k.startswith('_') and k not in {'payload', 'raw'}}


def sat_id(gnss, sv):
    letter = GNSS.get(gnss, '?')
    if letter == 'S':
        sv -= 100          # SBAS PRN 120.. -> S20..
    return f'{letter}{sv:02d}'


def rawx_rows(m):
    week, tow = m['week'], m['rcvTow']
    gpst = (datetime(1980, 1, 6) + timedelta(weeks=week, seconds=tow)).isoformat(timespec='milliseconds')
    for i in range(1, m['numMeas'] + 1):
        g = lambda k: m[f'{k}_{i:02d}']
        gnss, sig = g('gnssId'), g('sigId')
        yield [week, f'{tow:.3f}', gpst, sat_id(gnss, g('svId')), GNSS.get(gnss, '?'), g('svId'),
               sig, SIGNALS.get((gnss, sig), f'sig{sig}'), g('freqId') - 7 if gnss == 6 else '',
               f"{g('prMes'):.3f}", f"{g('cpMes'):.3f}", f"{g('doMes'):.3f}", g('cno'), g('locktime'),
               0.01 * 2 ** g('prStd'), round(0.004 * g('cpStd'), 3), 0.002 * 2 ** g('doStd'),
               g('prValid'), g('cpValid'), g('halfCyc'), g('subHalfCyc')]


def klobuchar(m):
    """GPS LNAV subframe 4 page 18 (SV ID 56) -> (alpha, beta) or None.

    u-blox delivers 30-bit words with data bits already de-inverted; data = word >> 6.
    """
    if m['gnssId'] != 0 or m['numWords'] != 10:
        return None
    d = [(m[f'dwrd_{i:02d}'] & 0x3FFFFFFF) >> 6 for i in range(1, 11)]
    if (d[0] >> 16) != 0x8B or (d[1] >> 2) & 7 != 4 or (d[2] >> 16) & 0x3F != 56:
        return None

    def s8(v):
        return v - 256 if v & 0x80 else v
    alpha = [s8((d[2] >> 8) & 0xFF) * 2 ** -30, s8(d[2] & 0xFF) * 2 ** -27,
             s8((d[3] >> 16) & 0xFF) * 2 ** -24, s8((d[3] >> 8) & 0xFF) * 2 ** -24]
    beta = [s8(d[3] & 0xFF) * 2 ** 11, s8((d[4] >> 16) & 0xFF) * 2 ** 14,
            s8((d[4] >> 8) & 0xFF) * 2 ** 16, s8(d[4] & 0xFF) * 2 ** 16]
    return alpha, beta


def convert(ubx_path, out_dir):
    out_dir = Path(out_dir)
    msg_dir = out_dir / 'ubx_messages'
    msg_dir.mkdir(parents=True, exist_ok=True)
    tables, ion = {}, []
    with open(out_dir / 'raw_observations.csv', 'w', newline='') as raw_fh, open(ubx_path, 'rb') as stream:
        raw_csv = csv.writer(raw_fh)
        raw_csv.writerow(RAW_HEADER)
        for _, parsed in UBXReader(stream, protfilter=2, quitonerror=0):
            if parsed is None:
                continue
            row = msg_to_dict(parsed)
            if not row:
                continue
            tables.setdefault(parsed.identity, []).append(row)
            if parsed.identity == 'RXM-RAWX':
                raw_csv.writerows(rawx_rows(row))
            elif parsed.identity == 'RXM-SFRBX':
                k = klobuchar(row)
                if k:
                    ion.append((row['svId'], *k))

    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r))   # union, first-seen order
        with open(msg_dir / f'{name}.csv', 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    print(f'{len(tables)} UBX message types -> {msg_dir}')

    if ion:
        sv, alpha, beta = ion[-1]
        info = {'source': 'UBX-RXM-SFRBX GPS LNAV subframe 4 page 18',
                'alpha': alpha, 'beta': beta, 'pages_decoded': len(ion),
                'satellites': sorted({f'G{s:02d}' for s, *_ in ion}),
                'all_pages_identical': all(a == alpha and b == beta for _, a, b in ion)}
        (out_dir / 'klobuchar_from_ubx.json').write_text(json.dumps(info, indent=2) + '\n')
        print('Klobuchar alpha', alpha, 'beta', beta)
    else:
        print('No GPS ionosphere page found in RXM-SFRBX')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ubx_file', type=Path)
    ap.add_argument('out_dir', type=Path)
    a = ap.parse_args()
    convert(a.ubx_file, a.out_dir)


if __name__ == '__main__':
    main()
