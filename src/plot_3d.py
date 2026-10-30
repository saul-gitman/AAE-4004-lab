#!/usr/bin/env python3
"""3D plot of the WLS position solution, plus per-epoch LLH/ENU and static-position CSVs.

Inputs : results/solution_details.csv (WLSE_spp.py), receiver NAV-HPPOSECEF.csv and
         NAV-PVT.csv (from ubx2csv.py; the receiver solution is NOT ground truth).
Outputs: figures/position_3d.png, results/position_enu_llh.csv,
         results/static_position_summary.csv

ENU origin = median WLS position over the static part of the log. The static part
starts at the first epoch after which the receiver's own ground speed (NAV-PVT
gSpeed) stays below 0.1 m/s for the rest of the measurements.

Usage:
  python src/plot_3d.py [--root .]
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator

from rinex2csv import ecef2pos, enu_matrix

SURFACE, TEXT, TEXT2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
TIME_CMAP = LinearSegmentedColormap.from_list('blue_seq', ['#86b6ef', '#3987e5', '#1c5cab', '#0d366b'])
RECEIVER = '#eb6834'
STATIC_SPEED_MM_S = 100


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def static_start(pvt, t_last):
    """First tow after which receiver speed stays below the threshold until t_last."""
    moving = [int(r['iTOW']) / 1000 for r in pvt
              if int(r['iTOW']) / 1000 <= t_last and int(r['gSpeed']) > STATIC_SPEED_MM_S]
    return max(moving) + 1 if moving else -np.inf


def summary_row(name, xyz, ref_xyz, R):
    med = np.median(xyz, axis=0)
    lat, lon, h = ecef2pos(med)
    enu = (xyz - med) @ R.T
    off = R @ (med - ref_xyz)
    return {'solution': name, 'epochs': len(xyz),
            'x_ecef_m': f'{med[0]:.3f}', 'y_ecef_m': f'{med[1]:.3f}', 'z_ecef_m': f'{med[2]:.3f}',
            'lat_deg': f'{np.degrees(lat):.8f}', 'lon_deg': f'{np.degrees(lon):.8f}', 'h_ellipsoid_m': f'{h:.3f}',
            'std_e_m': f'{enu[:, 0].std(ddof=1):.3f}', 'std_n_m': f'{enu[:, 1].std(ddof=1):.3f}',
            'std_u_m': f'{enu[:, 2].std(ddof=1):.3f}',
            'p95_horizontal_m': f'{np.percentile(np.linalg.norm(enu[:, :2], axis=1), 95):.3f}',
            'offset_e_from_wls_m': f'{off[0]:.3f}', 'offset_n_from_wls_m': f'{off[1]:.3f}',
            'offset_u_from_wls_m': f'{off[2]:.3f}'}


def style_axes(ax, lim):
    ax.set_facecolor(SURFACE)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((1, 1, 1, 0))
        axis._axinfo['grid'].update(color=GRID, linewidth=0.6)
        axis.label.set_color(TEXT2)
    ax.tick_params(colors=TEXT2, labelsize=8)
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(MaxNLocator(4, symmetric=True))
    ax.set_xlabel('East (m)', fontsize=9)
    ax.set_ylabel('North (m)', fontsize=9)
    ax.set_zlabel('Up (m)', fontsize=9)
    for setter, (lo, hi) in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), lim):
        setter(lo, hi)
    ax.set_box_aspect([hi - lo for lo, hi in lim])   # metres are metres on every axis
    ax.view_init(elev=24, azim=-58)


def robust_limits(points, pct, step):
    """Symmetric per-axis limits around the origin covering pct % of the points."""
    span = np.maximum(np.ceil(np.percentile(np.abs(points), pct, axis=0) / step) * step, step)
    return [(-v, v) for v in span]


def panel(ax, title, t_min, enu, rcv_enu, lim, norm):
    inside = np.all([(enu[:, i] >= lo) & (enu[:, i] <= hi) for i, (lo, hi) in enumerate(lim)], axis=0)
    rin = np.all([(rcv_enu[:, i] >= lo) & (rcv_enu[:, i] <= hi) for i, (lo, hi) in enumerate(lim)], axis=0)
    ax.computed_zorder = False                      # draw in the order below, star on top
    ax.plot(*np.where(rin, rcv_enu.T, np.nan), color=RECEIVER, lw=1.2, alpha=0.9, zorder=1,
            label='Receiver solution (NAV-HPPOSECEF, not ground truth)')
    sc = ax.scatter(*enu[inside].T, c=t_min[inside], cmap=TIME_CMAP, norm=norm, s=16, zorder=2,
                    edgecolors=SURFACE, linewidths=0.3, depthshade=False, label='WLS SPP epoch (this work)')
    ax.scatter([0], [0], [0], marker='*', s=260, color=TEXT, edgecolors=SURFACE, linewidths=1.2,
               depthshade=False, zorder=3, label='Static position (median of static epochs)')
    style_axes(ax, lim)
    hidden = (~inside).sum()
    note = f'{inside.sum()} epochs shown' + (f', {hidden} outliers beyond the axes (kept in the CSV)' if hidden else '')
    ax.set_title(f'{title}\n{note}', fontsize=10, color=TEXT, pad=0)
    return sc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    a = ap.parse_args()
    root = a.root
    sol = read_csv(root / 'results/solution_details.csv')
    hp = read_csv(root / 'data/csv/ubx_messages/NAV-HPPOSECEF.csv')
    pvt = read_csv(root / 'data/csv/ubx_messages/NAV-PVT.csv')

    tow = np.array([float(r['gps_tow_s']) for r in sol])
    xyz = np.array([[float(r[k]) for k in ('x_ecef_m', 'y_ecef_m', 'z_ecef_m')] for r in sol])
    rcv = {round(int(r['iTOW']) / 1000, 1): np.array([float(r[k]) / 100 for k in ('ecefX', 'ecefY', 'ecefZ')])
           for r in hp if r['invalidEcef'] == '0'}
    t0 = tow[0]
    t_static = static_start(pvt, tow[-1])
    static = tow >= t_static

    ref = np.median(xyz[static], axis=0)
    lat0, lon0, h0 = ecef2pos(ref)
    R = enu_matrix(lat0, lon0)
    enu = (xyz - ref) @ R.T
    rcv_t = np.array(sorted(t for t in rcv if tow[0] - 0.5 <= t <= tow[-1] + 0.5))
    rcv_xyz = np.array([rcv[t] for t in rcv_t])
    rcv_enu = (rcv_xyz - ref) @ R.T

    # Per-epoch table in readable coordinates
    with open(root / 'results/position_enu_llh.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['gps_week', 'gps_tow_s', 'x_ecef_m', 'y_ecef_m', 'z_ecef_m', 'lat_deg', 'lon_deg',
                    'h_ellipsoid_m', 'e_m', 'n_m', 'u_m', 'used_satellites', 'clock_bias_m', 'antenna_state'])
        for r, p, d, s in zip(sol, xyz, enu, static):
            lat, lon, h = ecef2pos(p)
            w.writerow([r['gps_week'], f'{float(r["gps_tow_s"]):.3f}', *[f'{v:.3f}' for v in p],
                        f'{np.degrees(lat):.8f}', f'{np.degrees(lon):.8f}', f'{h:.3f}', *[f'{v:.3f}' for v in d],
                        r['used_measurements'], f'{float(r["clock_bias_m"]):.3f}', 'static' if s else 'moving'])
    rows = [summary_row('WLS SPP, GPS L1 (this work)', xyz[static], ref, R),
            summary_row('Receiver NAV-HPPOSECEF (multi-GNSS; not ground truth)', rcv_xyz[rcv_t >= t_static], ref, R)]
    with open(root / 'results/static_position_summary.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # Figure: full extent + zoom on the solution cluster
    t_min = (tow - t0) / 60
    norm = plt.Normalize(0, t_min.max())
    rcv_static = rcv_t >= t_static
    lim_all = robust_limits(np.vstack([enu, rcv_enu]), 97, 10)
    lim_static = robust_limits(enu[static], 95, 5)

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': TEXT})
    fig = plt.figure(figsize=(15, 8.4), facecolor=SURFACE)
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    ax2 = fig.add_subplot(1, 2, 2, projection='3d')
    sc = panel(ax1, 'Whole log: walk-in + static', t_min, enu, rcv_enu, lim_all, norm)
    panel(ax2, f'Static part only (from {(t_static - t0) / 60:.1f} min)', t_min[static], enu[static],
          rcv_enu[rcv_static], lim_static, norm)

    cax = fig.add_axes([0.35, 0.10, 0.3, 0.016])
    cb = fig.colorbar(sc, cax=cax, orientation='horizontal')
    cb.set_label('Time since first epoch (min)', color=TEXT2, fontsize=9)
    cb.ax.tick_params(colors=TEXT2, labelsize=8)
    cb.outline.set_visible(False)
    ts = (t_static - t0) / 60
    cb.ax.axvline(ts, color=TEXT, lw=1.2)
    cb.ax.text(ts / 2, 1.6, 'antenna moving', ha='center', va='bottom', transform=cb.ax.get_xaxis_transform(),
               fontsize=8, color=TEXT2)
    cb.ax.text((ts + t_min.max()) / 2, 1.6, 'antenna static', ha='center', va='bottom',
               transform=cb.ax.get_xaxis_transform(), fontsize=8, color=TEXT2)

    handles, labels = ax2.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 0.0), labelcolor=TEXT)
    s = rows[0]
    fig.suptitle('AAE4203 GNSS Lab 1: GPS L1 weighted least-squares positions in local ENU', fontsize=13,
                 color=TEXT, y=0.98)
    fig.text(0.5, 0.94,
             f'{len(tow)} of {len(tow) + len(read_csv(root / "results/omitted_epochs.csv"))} epochs solved · '
             f'origin = static median {float(s["lat_deg"]):.6f}°N, {float(s["lon_deg"]):.6f}°E, '
             f'h = {float(s["h_ellipsoid_m"]):.1f} m (ECEF {s["x_ecef_m"]}, {s["y_ecef_m"]}, {s["z_ecef_m"]})',
             ha='center', fontsize=9, color=TEXT2)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.17, wspace=0.05)
    out = root / 'figures/position_3d.png'
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print('Saved:', out)
    print('Static from tow', t_static, '| static epochs', int(static.sum()), '| summary:', s)


if __name__ == '__main__':
    main()
