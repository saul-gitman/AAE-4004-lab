#!/usr/bin/env python3
"""Python port of the course rinex2csv.m (GPS L1 teaching baseline), no MATLAB needed.

RINEX 3 OBS + NAV -> the measurement matrices read by WLSE_spp.py --mode gps:
pseudoranges_meas, satellite_clock_bias, ionospheric_delay, tropospheric_delay,
satellite_positions, group_delay, elevation_deg (rows = satellites, columns =
epochs; satellite_positions has 3 columns per epoch), plus epochs.csv,
satellites.csv and conversion_summary.txt.

The per-epoch logic follows rinex2csv.m line by line; the satellite, ionosphere
and troposphere models are the RTKLIB functions that matRTKLIB wraps
(satposs/eph2pos, ionmodel, tropmodel with 70 % humidity, geodist, satazel).

Klobuchar coefficients: --klobuchar-json, else the NAV header, else the RTKLIB
default set (what rinex2csv.m uses when the NAV header has none).

Usage:
  python src/rinex2csv.py OBS NAV OUT_DIR [--klobuchar-json FILE]
"""
import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path

import numpy as np

CLIGHT = 299792458.0
MU_GPS = 3.9860050e14
OMGE = 7.2921151467e-5
RE_WGS84 = 6378137.0
FE_WGS84 = 1.0 / 298.257223563
REL_HUMI = 0.7
MAXDTOE = 7200.0
ELEV_MASK_DEG = 15.0
SNR_MASK_DBHZ = 15.0
ION_DEFAULT = [0.1118e-07, -0.7451e-08, -0.5961e-07, 0.1192e-06,
               0.1167e+06, -0.2294e+06, -0.1311e+06, 0.1049e+07]
GPS_EPOCH = date(1980, 1, 6)
NAV_LINES = {'G': 8, 'E': 8, 'C': 8, 'J': 8, 'I': 8, 'R': 4, 'S': 4}


def gps_time(y, mo, d, h, mi, s):
    """GPST calendar time -> (GPS week, time of week in s); kept apart for precision."""
    days = (date(y, mo, d) - GPS_EPOCH).days
    return days // 7, (days % 7) * 86400 + h * 3600 + mi * 60 + s


def nav_float(text):
    text = text.strip().replace('D', 'E').replace('d', 'e')
    return float(text) if text else 0.0


# --------------------------------------------------------------------------- RINEX
def read_obs(path):
    """GPS L1 pseudorange and C/N0 per epoch from a RINEX 3 observation file."""
    types, lines = {}, Path(path).read_text(encoding='ascii', errors='replace').splitlines()
    i, last_sys = 0, None
    while i < len(lines):
        line, label = lines[i], lines[i][60:].strip()
        i += 1
        if label == 'SYS / # / OBS TYPES':
            if line[0] != ' ':
                last_sys = line[0]
                types[last_sys] = []
            types[last_sys] += line[7:60].split()
        elif label == 'END OF HEADER':
            break
    if 'G' not in types:
        raise ValueError('No GPS observation types in the OBS header')
    gtypes = types['G']
    # RTKLIB GPS L1 code priority (C > P > Y > W > M > N > S > L)
    code = next((c for c in 'CPYWMNSL' if 'C1' + c in gtypes), None)
    if code is None:
        raise ValueError('No GPS L1 pseudorange type in the OBS header')
    ip, isn = gtypes.index('C1' + code), gtypes.index('S1' + code) if 'S1' + code in gtypes else None

    epochs = []  # (week, tow, {prn: (P, S)})
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.startswith('>'):
            continue
        flag, nsat = int(line[31]), int(line[32:35])
        if flag > 1:            # event records: skip their header lines
            i += nsat
            continue
        week, tow = gps_time(int(line[2:6]), int(line[7:9]), int(line[10:12]),
                             int(line[13:15]), int(line[16:18]), float(line[18:29]))
        meas = {}
        for rec in lines[i:i + nsat]:
            if rec[0] != 'G':
                continue

            def field(k):
                s = rec[3 + 16 * k: 3 + 16 * k + 14].strip()
                return float(s) if s else math.nan
            P = field(ip)
            meas[int(rec[1:3])] = (P if P != 0 else math.nan,
                                   field(isn) if isn is not None else math.nan)
        i += nsat
        epochs.append((week, tow, meas))
    return epochs, 'C1' + code


def read_nav(path):
    """GPS LNAV ephemerides and Klobuchar header coefficients from RINEX 3 NAV."""
    lines = Path(path).read_text(encoding='ascii', errors='replace').splitlines()
    ion, i = {}, 0
    while i < len(lines):
        line, label = lines[i], lines[i][60:].strip()
        i += 1
        if label == 'IONOSPHERIC CORR' and line[:4] in ('GPSA', 'GPSB'):
            ion[line[:4]] = [nav_float(line[5 + 12 * k: 17 + 12 * k]) for k in range(4)]
        elif label == 'END OF HEADER':
            break
    ion_gps = ion['GPSA'] + ion['GPSB'] if len(ion) == 2 else None

    ephs = {}
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        sys = line[0]
        n = NAV_LINES.get(sys)
        if n is None:
            raise ValueError(f'Unsupported NAV record at line {i + 1}: {line[:3]!r}')
        block = lines[i:i + n]
        i += n
        if sys != 'G':
            continue
        v = [nav_float(block[0][23 + 19 * k: 42 + 19 * k]) for k in range(3)]
        for row in block[1:]:
            row = row.ljust(80)
            v += [nav_float(row[4 + 19 * k: 23 + 19 * k]) for k in range(4)]
        toc_week, toc_tow = gps_time(int(block[0][4:8]), int(block[0][9:11]), int(block[0][12:14]),
                                     int(block[0][15:17]), int(block[0][18:20]), float(block[0][21:23]))
        toes = v[11]
        toe_week = toc_week + round((toc_tow - toes) / 604800)   # adjweek(): toe near toc
        # times are stored as (week, seconds); convert() makes them relative to the data
        eph = dict(prn=int(line[1:3]), toc=(toc_week, toc_tow), f0=v[0], f1=v[1], f2=v[2],
                   iode=v[3], crs=v[4], deln=v[5], M0=v[6], cuc=v[7], e=v[8], cus=v[9],
                   A=v[10] ** 2, toe=(toe_week, toes), toes=toes, cic=v[12], OMG0=v[13], cis=v[14],
                   i0=v[15], crc=v[16], omg=v[17], OMGd=v[18], idot=v[19],
                   svh=int(v[24]), tgd=v[25], iodc=v[26])
        ephs.setdefault(eph['prn'], []).append(eph)
    return ephs, ion_gps


# ------------------------------------------------------------------ RTKLIB models
def seleph(ephs, prn, t):
    best = None
    for eph in ephs.get(prn, []):
        dt = abs(t - eph['toe'])
        if dt <= MAXDTOE and (best is None or dt < abs(t - best['toe'])):
            best = eph
    return best


def eph2clk(t, eph):
    ts = tk = t - eph['toc']
    for _ in range(2):
        tk = ts - (eph['f0'] + eph['f1'] * tk + eph['f2'] * tk * tk)
    return eph['f0'] + eph['f1'] * tk + eph['f2'] * tk * tk


def eph2pos(t, eph):
    """Satellite ECEF position (frame at transmission) and clock incl. relativity (s)."""
    tk = t - eph['toe']
    n = math.sqrt(MU_GPS / eph['A'] ** 3) + eph['deln']
    M = eph['M0'] + n * tk
    E, Ek = M, 0.0
    for _ in range(30):
        if abs(E - Ek) <= 1e-13:
            break
        Ek = E
        E -= (E - eph['e'] * math.sin(E) - M) / (1.0 - eph['e'] * math.cos(E))
    sinE, cosE = math.sin(E), math.cos(E)
    u = math.atan2(math.sqrt(1.0 - eph['e'] ** 2) * sinE, cosE - eph['e']) + eph['omg']
    r = eph['A'] * (1.0 - eph['e'] * cosE)
    i = eph['i0'] + eph['idot'] * tk
    sin2u, cos2u = math.sin(2 * u), math.cos(2 * u)
    u += eph['cus'] * sin2u + eph['cuc'] * cos2u
    r += eph['crs'] * sin2u + eph['crc'] * cos2u
    i += eph['cis'] * sin2u + eph['cic'] * cos2u
    x, y, cosi = r * math.cos(u), r * math.sin(u), math.cos(i)
    O = eph['OMG0'] + (eph['OMGd'] - OMGE) * tk - OMGE * eph['toes']
    sinO, cosO = math.sin(O), math.cos(O)
    rs = np.array([x * cosO - y * cosi * sinO, x * sinO + y * cosi * cosO, y * math.sin(i)])
    tc = t - eph['toc']
    dts = eph['f0'] + eph['f1'] * tc + eph['f2'] * tc * tc
    dts -= 2.0 * math.sqrt(MU_GPS * eph['A']) * eph['e'] * sinE / CLIGHT ** 2
    return rs, dts


def satposs(t_rx, prn, pr, ephs):
    """RTKLIB satposs(): position at signal transmission, clock in metres."""
    eph = seleph(ephs, prn, t_rx)
    if eph is None or not math.isfinite(pr):
        return None
    t = t_rx - pr / CLIGHT
    t -= eph2clk(t, eph)
    rs, dts = eph2pos(t, eph)
    return rs, dts * CLIGHT, eph['svh'], eph['tgd'] * CLIGHT


def ecef2pos(r):
    e2 = FE_WGS84 * (2.0 - FE_WGS84)
    r2 = r[0] ** 2 + r[1] ** 2
    z, zk, v = r[2], 0.0, RE_WGS84
    while abs(z - zk) >= 1e-4:
        zk = z
        sinp = z / math.sqrt(r2 + z * z)
        v = RE_WGS84 / math.sqrt(1.0 - e2 * sinp * sinp)
        z = r[2] + v * e2 * sinp
    lat = math.atan(z / math.sqrt(r2)) if r2 > 1e-12 else math.copysign(math.pi / 2, r[2])
    lon = math.atan2(r[1], r[0]) if r2 > 1e-12 else 0.0
    return lat, lon, math.sqrt(r2 + z * z) - v


def enu_matrix(lat, lon):
    sp, cp, sl, cl = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    return np.array([[-sl, cl, 0.0], [-sp * cl, -sp * sl, cp], [cp * cl, cp * sl, sp]])


def ionmodel(tow, pos, az, el, ion):
    if pos[2] < -1e3 or el <= 0:
        return 0.0
    psi = 0.0137 / (el / math.pi + 0.11) - 0.022
    phi = min(max(pos[0] / math.pi + psi * math.cos(az), -0.416), 0.416)
    lam = pos[1] / math.pi + psi * math.sin(az) / math.cos(phi * math.pi)
    phi += 0.064 * math.cos((lam - 1.617) * math.pi)
    tt = 43200.0 * lam + tow
    tt -= math.floor(tt / 86400.0) * 86400.0
    f = 1.0 + 16.0 * (0.53 - el / math.pi) ** 3
    amp = max(ion[0] + phi * (ion[1] + phi * (ion[2] + phi * ion[3])), 0.0)
    per = max(ion[4] + phi * (ion[5] + phi * (ion[6] + phi * ion[7])), 72000.0)
    x = 2.0 * math.pi * (tt - 50400.0) / per
    return CLIGHT * f * (5e-9 + amp * (1.0 + x * x * (-0.5 + x * x / 24.0)) if abs(x) < 1.57 else 5e-9)


def tropmodel(pos, el, humi=REL_HUMI):
    if pos[2] < -100.0 or pos[2] > 1e4 or el <= 0:
        return 0.0
    hgt = max(pos[2], 0.0)
    pres = 1013.25 * (1.0 - 2.2557e-5 * hgt) ** 5.2568
    temp = 15.0 - 6.5e-3 * hgt + 273.16
    e = 6.108 * humi * math.exp((17.15 * temp - 4684.0) / (temp - 38.45))
    z = math.pi / 2.0 - el
    trph = 0.0022768 * pres / (1.0 - 0.00266 * math.cos(2.0 * pos[0]) - 0.00028 * hgt / 1e3) / math.cos(z)
    trpw = 0.002277 * (1255.0 / temp + 0.05) * e / math.cos(z)
    return trph + trpw


def receiver_terms(x, sp, tow, ion_coef):
    """matRTKLIB setRcvPos(): range with Sagnac, LOS, elevation, iono, tropo."""
    pos = ecef2pos(x)
    R = enu_matrix(pos[0], pos[1])
    n = len(sp)
    rng, los, el = np.full(n, np.nan), np.full((n, 3), np.nan), np.full(n, np.nan)
    ion, trp = np.full(n, np.nan), np.full(n, np.nan)
    for j in range(n):
        if not np.isfinite(sp[j]).all() or np.linalg.norm(sp[j]) < RE_WGS84:
            continue
        d = sp[j] - x
        r = np.linalg.norm(d)
        los[j] = d / r
        rng[j] = r + OMGE * (sp[j, 0] * x[1] - sp[j, 1] * x[0]) / CLIGHT
        enu = R @ los[j]
        azr = math.atan2(enu[0], enu[1]) % (2 * math.pi)
        elr = math.asin(enu[2])
        el[j] = math.degrees(elr)
        ion[j] = ionmodel(tow, pos, azr, elr, ion_coef)
        trp[j] = tropmodel(pos, elr)
    return rng, los, el, ion, trp


# --------------------------------------------------------------- rinex2csv.m port
def convert(obs_file, nav_file, out_dir, ion_override=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    epochs, l1_code = read_obs(obs_file)
    ephs, ion_header = read_nav(nav_file)
    if ion_override is not None:
        ion_coef, ion_source = list(ion_override), 'user-supplied (--klobuchar-json)'
    elif ion_header is not None and any(ion_header):
        ion_coef, ion_source = ion_header, 'NAV header (GPSA/GPSB)'
    else:
        ion_coef, ion_source = ION_DEFAULT, 'RTKLIB default (NAV header has none)'

    prns = sorted({p for _, _, m in epochs for p in m})
    if len(prns) < 4:
        raise ValueError('Fewer than four GPS satellites in the file.')
    m, n = len(prns), len(epochs)
    P, D, I, T, B, E = (np.full((m, n), np.nan) for _ in range(6))
    S = np.full((m, 3 * n), np.nan)
    success = np.zeros(n, bool)
    week0 = epochs[0][0]          # times below are seconds from the start of this GPS week

    def rel(wt):
        return (wt[0] - week0) * 604800 + wt[1]
    ephs = {p: [dict(e, toe=rel(e['toe']), toc=rel(e['toc'])) for e in v] for p, v in ephs.items()}
    xlast = None

    for k, (week, tow, meas) in enumerate(epochs):
        t = rel((week, tow))
        pr, snr = np.full(m, np.nan), np.full(m, np.nan)
        sp, clk, svh, tgd = np.full((m, 3), np.nan), np.full(m, np.nan), np.full(m, -1), np.zeros(m)
        for j, prn in enumerate(prns):
            if prn not in meas:
                continue
            pr[j], snr[j] = meas[prn]
            res = satposs(t, prn, pr[j], ephs)
            if res is not None:
                sp[j], clk[j], svh[j], tgd[j] = res
        unhealthy = svh != 0
        sp[unhealthy], clk[unhealthy] = np.nan, np.nan
        with np.errstate(invalid='ignore'):
            mask = np.isfinite(pr) & (pr > 1e7) & np.isfinite(clk) & np.isfinite(sp).all(1) & (svh == 0)
        if mask.sum() < 4:
            continue

        # Coarse observation-only solution, also used to recover after failed epochs.
        x = np.zeros(4) if xlast is None else xlast.copy()
        good = True
        for _ in range(15):
            delta = sp[mask] - x[:3]
            rng = np.linalg.norm(delta, axis=1)
            H = np.column_stack((-delta / rng[:, None], np.ones(mask.sum())))
            if np.linalg.matrix_rank(H) < 4:
                good = False
                break
            dx = np.linalg.lstsq(H, pr[mask] + clk[mask] - tgd[mask] - rng - x[3], rcond=None)[0]
            x += dx
            if np.linalg.norm(dx) < 1e-3:
                break
        if not good or not np.isfinite(x).all() or not 6.2e6 <= np.linalg.norm(x[:3]) <= 6.5e6:
            continue

        # Iterate atmospheric corrections at the observation-derived position.
        converged = False
        for _ in range(20):
            rng, los, el, ion, trp = receiver_terms(x[:3], sp, tow, ion_coef)
            with np.errstate(invalid='ignore'):
                use = mask & np.isfinite(ion) & np.isfinite(trp) & (el >= ELEV_MASK_DEG) & (snr >= SNR_MASK_DBHZ)
            if use.sum() < 4:
                break
            H = np.column_stack((-los[use], np.ones(use.sum())))
            if np.linalg.matrix_rank(H) < 4:
                break
            v = pr[use] + clk[use] - ion[use] - trp[use] - tgd[use] - rng[use] - x[3]
            sw = np.sin(np.radians(el[use]))     # sqrt of the sin^2(el) weight
            dx = np.linalg.lstsq(H * sw[:, None], v * sw, rcond=None)[0]   # = lscov(H,v,w)
            x += dx
            if np.linalg.norm(dx) < 1e-3:
                converged = True
                break
        if not converged:
            continue
        xlast = x.copy()
        rng, los, el, ion, trp = receiver_terms(x[:3], sp, tow, ion_coef)
        with np.errstate(invalid='ignore'):
            use = mask & np.isfinite(ion) & np.isfinite(trp) & (el >= ELEV_MASK_DEG) & (snr >= SNR_MASK_DBHZ)
        P[use, k], D[use, k], I[use, k], T[use, k] = pr[use], clk[use], ion[use], trp[use]
        B[use, k], E[use, k] = tgd[use], el[use]
        block = np.full((m, 3), np.nan)
        block[use] = sp[use]
        S[:, 3 * k:3 * k + 3] = block
        success[k] = True
        if (k + 1) % 200 == 0:
            print(f'Converted {k + 1}/{n} epochs')

    for name, arr in [('pseudoranges_meas', P), ('satellite_clock_bias', D),
                      ('ionospheric_delay', I), ('tropospheric_delay', T),
                      ('satellite_positions', S), ('group_delay', B), ('elevation_deg', E)]:
        np.savetxt(out_dir / f'{name}.csv', arr, delimiter=',', fmt='%.15g')
    with (out_dir / 'epochs.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['gps_week', 'gps_tow_s'])
        for week, tow, _ in epochs:
            w.writerow([week, repr(round(tow, 7))])
    with (out_dir / 'satellites.csv').open('w', newline='') as f:
        f.write('satellite_id\n' + ''.join(f'G{p:02d}\n' for p in prns))
    (out_dir / 'conversion_summary.txt').write_text(
        f'GPS L1 ({l1_code}) only; elevation >={ELEV_MASK_DEG:g} deg; SNR >={SNR_MASK_DBHZ:g} dB-Hz.\n'
        f'Input epochs: {n}; converted: {success.sum()}; omitted: {n - success.sum()}.\n'
        'Atmosphere and TGD are separate arrays; satellite clocks are metres.\n'
        'Unsolved epochs remain NaN, never replaced by the previous position.\n'
        f'Klobuchar coefficients: {ion_source}: {ion_coef}\n'
        'Generated by src/rinex2csv.py (Python port of course rinex2csv.m).\n')
    print(f'RINEX conversion complete: {success.sum()}/{n} epochs. Output: {out_dir}')
    return success.sum(), n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('obs_file')
    ap.add_argument('nav_file')
    ap.add_argument('out_dir')
    ap.add_argument('--klobuchar-json', type=Path,
                    help='JSON with "alpha" and "beta" lists (e.g. from ubx2csv.py)')
    a = ap.parse_args()
    ion = None
    if a.klobuchar_json:
        k = json.loads(a.klobuchar_json.read_text())
        ion = list(k['alpha']) + list(k['beta'])
    convert(a.obs_file, a.nav_file, a.out_dir, ion)


if __name__ == '__main__':
    main()
