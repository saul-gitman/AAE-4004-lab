#!/usr/bin/env python3
"""Animated GIF of the whole log in 3D ENU: WLS epochs appear in time order, with the
receiver solution trace. Same frame/origin as plot_3d.py.

Output: figures/position_3d.gif
Usage : python src/animate_3d.py [--step 3] [--fps 15]
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

from plot_3d import (SURFACE, TEXT, TEXT2, TIME_CMAP, RECEIVER, read_csv, static_start,
                     robust_limits, style_axes)
from rinex2csv import ecef2pos, enu_matrix


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--step', type=int, default=3, help='epochs per frame')
    ap.add_argument('--fps', type=int, default=15)
    a = ap.parse_args()
    root = a.root
    sol = read_csv(root / 'results/solution_details.csv')
    hp = read_csv(root / 'data/csv/ubx_messages/NAV-HPPOSECEF.csv')
    pvt = read_csv(root / 'data/csv/ubx_messages/NAV-PVT.csv')

    tow = np.array([float(r['gps_tow_s']) for r in sol])
    xyz = np.array([[float(r[k]) for k in ('x_ecef_m', 'y_ecef_m', 'z_ecef_m')] for r in sol])
    t_static = static_start(pvt, tow[-1])
    ref = np.median(xyz[tow >= t_static], axis=0)
    R = enu_matrix(*ecef2pos(ref)[:2])
    enu = (xyz - ref) @ R.T
    rcv = {int(r['iTOW']) / 1000: np.array([float(r[k]) / 100 for k in ('ecefX', 'ecefY', 'ecefZ')])
           for r in hp if r['invalidEcef'] == '0'}
    rcv_t = np.array(sorted(t for t in rcv if tow[0] - 0.5 <= t <= tow[-1] + 0.5))
    rcv_enu = (np.array([rcv[t] for t in rcv_t]) - ref) @ R.T

    lim = robust_limits(np.vstack([enu, rcv_enu]), 97, 10)
    inside = np.all([(enu[:, i] >= lo) & (enu[:, i] <= hi) for i, (lo, hi) in enumerate(lim)], axis=0)
    rin = np.all([(rcv_enu[:, i] >= lo) & (rcv_enu[:, i] <= hi) for i, (lo, hi) in enumerate(lim)], axis=0)
    t_min = (tow - tow[0]) / 60
    norm = plt.Normalize(0, t_min.max())

    fig = plt.figure(figsize=(8, 7), facecolor=SURFACE)
    ax = fig.add_subplot(projection='3d')
    ax.computed_zorder = False
    style_axes(ax, lim)
    trail = ax.scatter(np.zeros(0), np.zeros(0), np.zeros(0), s=10, c=np.zeros(0), cmap=TIME_CMAP, norm=norm, depthshade=False,
                       edgecolors=SURFACE, linewidths=0.2, zorder=2, label='WLS SPP epochs (this work)')
    line, = ax.plot(np.zeros(0), np.zeros(0), np.zeros(0), color=RECEIVER, lw=1.3, zorder=1, label='Receiver solution (not ground truth)')
    head, = ax.plot(np.zeros(0), np.zeros(0), np.zeros(0), 'o', ms=9, color=TEXT, mec=SURFACE, mew=1.2, zorder=3, label='Current epoch')
    ax.legend(loc='upper left', frameon=False, fontsize=8, labelcolor=TEXT)
    title = fig.suptitle('', fontsize=11, color=TEXT, y=0.95)
    fig.text(0.5, 0.02, 'Local ENU (m), origin = static median position · points beyond the axes not shown',
             ha='center', fontsize=8, color=TEXT2)
    fig.subplots_adjust(left=0, right=0.95, top=0.92, bottom=0.04)

    frames = list(range(0, len(tow), a.step)) + [len(tow) - 1] * a.fps   # hold last frame ~1 s

    def update(k):
        sel = inside[:k + 1]
        pts = enu[:k + 1][sel]
        trail._offsets3d = (pts[:, 0], pts[:, 1], pts[:, 2])
        trail.set_array(t_min[:k + 1][sel])
        m = (rcv_t <= tow[k]) & rin
        rp = np.where(m[:, None], rcv_enu, np.nan)
        line.set_data_3d(rp[:, 0], rp[:, 1], rp[:, 2])
        hx = enu[k] if inside[k] else np.full(3, np.nan)
        head.set_data_3d(hx[:1], hx[1:2], hx[2:])
        state = 'static' if tow[k] >= t_static else 'moving'
        title.set_text(f'AAE4203 GNSS Lab 1 · t = {t_min[k]:4.1f} min · epoch {k + 1}/{len(tow)} · antenna {state}')
        ax.view_init(elev=24, azim=-58 + 40 * k / len(tow))   # slow orbit for depth
        return trail, line, head, title

    out = root / 'figures/position_3d.gif'
    FuncAnimation(fig, update, frames=frames, blit=False).save(out, writer=PillowWriter(fps=a.fps), dpi=80)
    print('Saved:', out, f'({len(frames)} frames, {out.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
