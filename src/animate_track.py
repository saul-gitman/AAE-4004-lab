#!/usr/bin/env python3
"""Two-panel GIF of the whole log: rotating 3D ENU view + top-down East-North map,
with a short fading trail and the receiver track. Same frame/origin as plot_3d.py.

Output: figures/position_track.gif
Usage : python src/animate_track.py [--step 4] [--fps 15]
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

from plot_3d import (SURFACE, TEXT, TEXT2, GRID, TIME_CMAP, RECEIVER, read_csv, static_start,
                     robust_limits, style_axes)
from rinex2csv import ecef2pos, enu_matrix

TRAIL_S = 30          # seconds of highlighted recent trail


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--step', type=int, default=4, help='epochs per frame')
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
    t_min = (tow - tow[0]) / 60
    norm = plt.Normalize(0, t_min.max())

    fig = plt.figure(figsize=(11, 5.6), facecolor=SURFACE)
    ax = fig.add_axes([0.0, 0.08, 0.5, 0.8], projection='3d')
    ax.computed_zorder = False
    style_axes(ax, lim)
    m2 = fig.add_axes([0.58, 0.11, 0.38, 0.70])
    m2.set_facecolor(SURFACE)
    m2.grid(color=GRID, lw=0.6)
    m2.set_xlim(*lim[0])
    m2.set_ylim(*lim[1])
    m2.set_aspect('equal')
    m2.tick_params(colors=TEXT2, labelsize=8)
    for s in m2.spines.values():
        s.set_color(GRID)
    m2.set_xlabel('East (m)', color=TEXT2, fontsize=9)
    m2.set_ylabel('North (m)', color=TEXT2, fontsize=9)

    z = np.zeros(0)
    pts3 = ax.scatter(z, z, z, s=9, c=z, cmap=TIME_CMAP, norm=norm, depthshade=False,
                      edgecolors=SURFACE, linewidths=0.2, zorder=2)
    line3, = ax.plot(z, z, z, color=RECEIVER, lw=1.3, zorder=1)
    head3, = ax.plot(z, z, z, 'o', ms=9, color=TEXT, mec=SURFACE, mew=1.2, zorder=3)
    pts2 = m2.scatter([], [], s=9, c=[], cmap=TIME_CMAP, norm=norm, edgecolors=SURFACE, linewidths=0.2,
                      label='WLS SPP epochs (this work)')
    line2, = m2.plot([], [], color=RECEIVER, lw=1.3, label='Receiver solution (not ground truth)')
    trail2, = m2.plot([], [], 'o', ms=4, color=TEXT, alpha=0.75, label=f'Last {TRAIL_S} s')
    head2, = m2.plot([], [], 'o', ms=9, color=TEXT, mec=SURFACE, mew=1.2, label='Current epoch')
    m2.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=7.5, labelcolor=TEXT)
    title = fig.text(0.5, 0.95, '', ha='center', fontsize=12, color=TEXT)
    fig.text(0.5, 0.015, 'Local ENU (m), origin = static median position · epochs beyond the axes not drawn',
             ha='center', fontsize=8, color=TEXT2)

    frames = list(range(0, len(tow), a.step)) + [len(tow) - 1] * a.fps

    def update(k):
        sel = inside[:k + 1]
        p = enu[:k + 1][sel]
        c = t_min[:k + 1][sel]
        pts3._offsets3d = (p[:, 0], p[:, 1], p[:, 2])
        pts3.set_array(c)
        pts2.set_offsets(p[:, :2])
        pts2.set_array(c)
        m = rcv_t <= tow[k]
        r = rcv_enu[m]
        line3.set_data_3d(r[:, 0], r[:, 1], r[:, 2])
        line2.set_data(r[:, 0], r[:, 1])
        recent = (tow > tow[k] - TRAIL_S) & (tow <= tow[k]) & inside
        trail2.set_data(enu[recent, 0], enu[recent, 1])
        h = enu[k] if inside[k] else np.full(3, np.nan)
        head3.set_data_3d(h[:1], h[1:2], h[2:])
        head2.set_data(h[:1], h[1:2])
        state = 'STATIC' if tow[k] >= t_static else 'MOVING'
        title.set_text(f'AAE4203 GNSS Lab 1 · t = {t_min[k]:4.1f} min · epoch {k + 1}/{len(tow)} · antenna {state}')
        ax.view_init(elev=24, azim=-58 + 50 * k / len(tow))
        return pts3, line3, head3, pts2, line2, trail2, head2, title

    out = root / 'figures/position_track.gif'
    FuncAnimation(fig, update, frames=frames, blit=False).save(out, writer=PillowWriter(fps=a.fps), dpi=72)
    print('Saved:', out, f'({len(frames)} frames, {out.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
