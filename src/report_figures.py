#!/usr/bin/env python3
"""Figures and statistics for the lab report (raw-data quality and own-data validation).

Outputs: figures/raw_data_quality.png, figures/static_en_scatter.png,
         figures/enu_timeseries.png, results/report_stats.json
Usage  : python src/report_figures.py
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from plot_3d import SURFACE, TEXT, TEXT2, GRID, RECEIVER, read_csv, static_start
from rinex2csv import ecef2pos, enu_matrix

ROOT = Path(__file__).resolve().parents[1]
GNSS_COLORS = {'G': ('GPS', '#2a78d6'), 'E': ('Galileo', '#eb6834'),
               'C': ('BeiDou', '#1baf7a'), 'R': ('GLONASS', '#eda100')}
WLS = '#2a78d6'


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, lw=0.6)
    ax.tick_params(colors=TEXT2, labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(GRID)
    ax.xaxis.label.set_color(TEXT2)
    ax.yaxis.label.set_color(TEXT2)


def title(ax, text):
    ax.set_title(text, fontsize=10, color=TEXT, loc='left')


def main():
    sol = read_csv(ROOT / 'results/solution_details.csv')
    tow = np.array([float(r['gps_tow_s']) for r in sol])
    xyz = np.array([[float(r[k]) for k in ('x_ecef_m', 'y_ecef_m', 'z_ecef_m')] for r in sol])
    nused = np.array([int(r['used_measurements']) for r in sol])
    pvt = read_csv(ROOT / 'data/csv/ubx_messages/NAV-PVT.csv')
    t_static = static_start(pvt, tow[-1])
    static = tow >= t_static
    t0 = tow[0]
    ref = np.median(xyz[static], axis=0)
    lat0, lon0, _ = ecef2pos(ref)
    R = enu_matrix(lat0, lon0)
    enu = (xyz - ref) @ R.T

    rcv = {round(int(r['iTOW']) / 1000): np.array([float(r[k]) / 100 for k in ('ecefX', 'ecefY', 'ecefZ')])
           for r in read_csv(ROOT / 'data/csv/ubx_messages/NAV-HPPOSECEF.csv') if r['invalidEcef'] == '0'}
    rcv_enu = np.array([(rcv[round(t)] - ref) @ R.T for t in tow])
    diff = enu - rcv_enu

    # ---------------------------------------------------------------- raw data
    raw = read_csv(ROOT / 'data/csv/raw_observations.csv')
    sats = defaultdict(set)          # (sys, tow) -> sats with a valid pseudorange
    cn0 = defaultdict(dict)          # GPS L1 sat -> {tow: C/N0}
    sig_cn0 = defaultdict(list)
    for r in raw:
        if r['pr_valid'] != '1':
            continue
        t = round(float(r['rcv_tow_s']))
        sats[(r['gnss'], t)].add(r['sat'])
        sig_cn0[f"{r['gnss']} {r['signal']}"].append(int(r['cn0_dbhz']))
        if r['gnss'] == 'G' and r['signal'] == 'L1C/A':
            cn0[r['sat']][t] = int(r['cn0_dbhz'])
    epochs = sorted({t for _, t in sats})
    te = (np.array(epochs) - round(t0)) / 60

    navsat = read_csv(ROOT / 'data/csv/ubx_messages/NAV-SAT.csv')
    sky = defaultdict(list)
    letters = {0: 'G', 2: 'E', 3: 'C', 6: 'R'}
    for r in navsat[::10]:                       # every 10 s is enough for a sky track
        if not (tow[0] - 1 <= int(r['iTOW']) / 1000 <= tow[-1] + 1):
            continue
        for i in range(1, int(r['numSvs']) + 1):
            g = letters.get(int(r[f'gnssId_{i:02d}']))
            el = float(r[f'elev_{i:02d}'])
            if g and int(r[f'cno_{i:02d}']) > 0 and el > 0:
                sky[(g, r[f'svId_{i:02d}'])].append((float(r[f'azim_{i:02d}']), el))

    # GPS-only DOP of the satellites the solver used (unweighted, ENU at the static point)
    gin = ROOT / 'data/csv/gps_inputs'
    S = np.loadtxt(gin / 'satellite_positions.csv', delimiter=',')
    ep = np.loadtxt(gin / 'epochs.csv', delimiter=',', skiprows=1)
    hdop, vdop, tdop = [], [], []
    for k in range(len(ep)):
        sp = S[:, 3 * k:3 * k + 3]
        sp = sp[np.isfinite(sp).all(1)]
        if len(sp) < 4:
            continue
        los = (sp - ref) / np.linalg.norm(sp - ref, axis=1)[:, None]
        G = np.column_stack((-(los @ R.T), np.ones(len(sp))))
        Q = np.linalg.inv(G.T @ G)
        hdop.append((ep[k, 1], np.sqrt(Q[0, 0] + Q[1, 1]), np.sqrt(Q[2, 2])))
    hdop = np.array(hdop)
    dop = read_csv(ROOT / 'data/csv/ubx_messages/NAV-DOP.csv')
    rdop = np.array([(int(r['iTOW']) / 1000, float(r['hDOP']), float(r['vDOP'])) for r in dop
                     if tow[0] - 1 <= int(r['iTOW']) / 1000 <= tow[-1] + 1])

    plt.rcParams.update({'font.family': 'DejaVu Sans'})
    fig = plt.figure(figsize=(10, 7.4), facecolor=SURFACE)
    ax1 = fig.add_subplot(2, 2, 1)
    for g, (name, col) in GNSS_COLORS.items():
        ax1.plot(te, [len(sats.get((g, t), ())) for t in epochs], color=col, lw=1.6, label=name)
    ax1.plot((tow - t0) / 60, nused, color=TEXT, lw=1.0, ls=':', label='GPS used by WLS')
    ax1.axvline((t_static - t0) / 60, color=TEXT2, lw=0.8, ls='--')
    ax1.set_xlabel('Time since first epoch (min)')
    ax1.set_ylabel('Satellites')
    ax1.legend(fontsize=7.5, frameon=False, ncol=3, loc='upper left', labelcolor=TEXT)
    ax1.set_ylim(0, 16)
    style(ax1)
    title(ax1, '(a) Satellites with a valid pseudorange')

    ax2 = fig.add_subplot(2, 2, 2)
    order = sorted(cn0, key=lambda s: -np.mean(list(cn0[s].values())))
    shades = plt.get_cmap('Blues')(np.linspace(0.95, 0.4, len(order)))
    ends = []
    for s, col in zip(order, shades):
        tt = np.array(sorted(cn0[s]))
        v = np.array([cn0[s][t] for t in tt], float)
        gaps = np.r_[False, np.diff(tt) > 1]
        v[gaps] = np.nan
        ax2.plot((tt - round(t0)) / 60, v, color=col, lw=1.0)
        ends.append([np.nanmean(v[-60:]), s])
    ends.sort()
    for i in range(1, len(ends)):                 # keep end labels >= 2.4 dB apart
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 2.4)
    for y, s in ends:
        ax2.text((tow[-1] - t0) / 60 + 0.25, y, s, fontsize=7, color=TEXT2, va='center')
    ax2.axhline(15, color=TEXT2, lw=0.8, ls='--')
    ax2.text(0.1, 16, 'baseline mask 15 dB-Hz', fontsize=7, color=TEXT2)
    ax2.set_xlabel('Time since first epoch (min)')
    ax2.set_ylabel('C/N$_0$ (dB-Hz)')
    ax2.set_xlim(0, (tow[-1] - t0) / 60 + 1.2)
    style(ax2)
    title(ax2, '(b) GPS L1 C/A C/N$_0$ per satellite')

    ax3 = fig.add_subplot(2, 2, 3, projection='polar')
    ax3.set_theta_zero_location('N')
    ax3.set_theta_direction(-1)
    for (g, sv), tr in sky.items():
        a = np.radians([p[0] for p in tr])
        e = [90 - p[1] for p in tr]
        ax3.plot(a, e, color=GNSS_COLORS[g][1], lw=1.6)
        ax3.text(a[-1], e[-1], f'{g}{int(sv):02d}', fontsize=6, color=TEXT2)
    ax3.set_ylim(0, 90)
    ax3.set_rlabel_position(160)
    ax3.set_yticks([0, 30, 60, 75])
    ax3.set_yticklabels(['90°', '60°', '30°', '15°'], fontsize=7, color=TEXT2)
    ax3.fill_between(np.linspace(0, 2 * np.pi, 100), 75, 90, color=GRID, alpha=0.6, lw=0)
    ax3.tick_params(colors=TEXT2, labelsize=7)
    ax3.set_facecolor(SURFACE)
    ax3.grid(color=GRID)
    ax3.set_title('(c) Sky plot (receiver az/el, shaded < 15°)', fontsize=10, color=TEXT, loc='left', pad=14)

    ax4 = fig.add_subplot(2, 2, 4)
    ax4.plot((hdop[:, 0] - t0) / 60, hdop[:, 1], color=WLS, lw=1.2, label='HDOP, GPS used by WLS')
    ax4.plot((hdop[:, 0] - t0) / 60, hdop[:, 2], color=WLS, lw=1.2, ls='--', label='VDOP, GPS used by WLS')
    ax4.plot((rdop[:, 0] - t0) / 60, rdop[:, 1], color=RECEIVER, lw=1.2, label='HDOP, receiver (multi-GNSS)')
    ax4.plot((rdop[:, 0] - t0) / 60, rdop[:, 2], color=RECEIVER, lw=1.2, ls='--', label='VDOP, receiver')
    ax4.set_ylim(0, 10.5)
    ax4.set_xlabel('Time since first epoch (min)')
    ax4.set_ylabel('DOP')
    ax4.legend(fontsize=7.5, frameon=False, labelcolor=TEXT, ncol=2, loc='upper right')
    style(ax4)
    title(ax4, '(d) Dilution of precision')
    fig.tight_layout()
    fig.savefig(ROOT / 'figures/raw_data_quality.png', dpi=200, facecolor=SURFACE)
    plt.close(fig)

    # ------------------------------------------------------- static E-N scatter
    st = enu[static]
    mean = st.mean(0)
    about = st - np.median(st, axis=0)
    rad = np.linalg.norm(about[:, :2], axis=1)
    lim = np.ceil(np.percentile(rad, 95) / 5) * 5 + 5
    rs = rcv_enu[static] - np.median(st, axis=0)
    fig, ax = plt.subplots(figsize=(6, 5.4), facecolor=SURFACE)
    vis = (np.abs(about[:, :2]) <= lim).all(1)
    ax.scatter(about[vis, 0], about[vis, 1], s=12, color=WLS, edgecolors=SURFACE, linewidths=0.3,
               label=f'WLS SPP static epochs ({vis.sum()} shown, {(~vis).sum()} beyond axes)')
    ax.scatter(rs[:, 0], rs[:, 1], s=6, color=RECEIVER, label='Receiver NAV-HPPOSECEF')
    for p, ls in ((50, '-'), (95, '--')):
        r = np.percentile(rad, p)
        ax.add_patch(plt.Circle((0, 0), r, fill=False, color=TEXT, lw=0.9, ls=ls))
        ax.text(r * 0.72, r * 0.72, f'P{p} {r:.1f} m', fontsize=8, color=TEXT)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect('equal')
    ax.set_xlabel('East about static median (m)')
    ax.set_ylabel('North about static median (m)')
    ax.legend(fontsize=8, frameon=False, loc='lower left', labelcolor=TEXT)
    style(ax)
    fig.tight_layout()
    fig.savefig(ROOT / 'figures/static_en_scatter.png', dpi=200, facecolor=SURFACE)
    plt.close(fig)

    # --------------------------------------------------- ENU time series vs receiver
    fig, axs = plt.subplots(3, 1, figsize=(10, 6.2), sharex=True, facecolor=SURFACE)
    tm = (tow - t0) / 60
    for i, (ax, lab) in enumerate(zip(axs, ('East', 'North', 'Up'))):
        ax.plot(tm, rcv_enu[:, i], color=RECEIVER, lw=1.2, label='Receiver solution')
        ax.plot(tm, enu[:, i], '.', ms=3, color=WLS, label='WLS SPP (this work)')
        ax.axvspan(0, (t_static - t0) / 60, color=GRID, alpha=0.5, lw=0)
        ax.set_ylim(-60, 60)
        ax.set_ylabel(f'{lab} (m)')
        style(ax)
    axs[0].text(0.2, 48, 'antenna moving', fontsize=8, color=TEXT2)
    axs[0].text((t_static - t0) / 60 + 0.2, 48, 'antenna static', fontsize=8, color=TEXT2)
    axs[0].legend(fontsize=8, frameon=False, ncol=2, loc='lower right', labelcolor=TEXT)
    axs[-1].set_xlabel('Time since first epoch (min); y-axes clipped at ±60 m')
    fig.tight_layout()
    fig.savefig(ROOT / 'figures/enu_timeseries.png', dpi=200, facecolor=SURFACE)
    plt.close(fig)

    # ---------------------------------------------------------------- statistics
    def dstats(d):
        h = np.linalg.norm(d[:, :2], axis=1)
        return {'epochs': int(len(d)), 'mean_enu_m': d.mean(0).round(2).tolist(),
                'std_enu_m': d.std(0, ddof=1).round(2).tolist(),
                'median_enu_m': np.median(d, 0).round(2).tolist(),
                'rms_2d_m': round(float(np.sqrt(np.mean(h ** 2))), 2),
                'rms_3d_m': round(float(np.sqrt(np.mean(np.sum(d ** 2, 1)))), 2),
                'p50_2d_m': round(float(np.percentile(h, 50)), 2),
                'p95_2d_m': round(float(np.percentile(h, 95)), 2)}
    sig = {k: {'obs': len(v), 'median_cn0': float(np.median(v))} for k, v in sorted(sig_cn0.items())}
    stats = {
        'first_epoch_gpst_tow': tow[0], 'last_epoch_gpst_tow': tow[-1], 'static_from_tow': t_static,
        'epochs_obs': 853, 'epochs_solved': int(len(tow)), 'epochs_static': int(static.sum()),
        'static_mean_enu_about_median_m': (mean).round(2).tolist(),
        'static_std_enu_m': st.std(0, ddof=1).round(2).tolist(),
        'static_radius_p50_m': round(float(np.percentile(rad, 50)), 2),
        'static_radius_p95_m': round(float(np.percentile(rad, 95)), 2),
        'static_epochs_beyond_50m_h': int((rad > 50).sum()),
        'spp_minus_receiver_all': dstats(diff), 'spp_minus_receiver_static': dstats(diff[static]),
        'sats_mean_per_constellation': {GNSS_COLORS[g][0]: round(float(np.mean([len(sats.get((g, t), ())) for t in epochs])), 1)
                                        for g in GNSS_COLORS},
        'gps_used_counts': {int(k): int((nused == k).sum()) for k in np.unique(nused)},
        'gps_hdop_median': round(float(np.median(hdop[:, 1])), 2), 'gps_vdop_median': round(float(np.median(hdop[:, 2])), 2),
        'gps_hdop_max': round(float(hdop[:, 1].max()), 1), 'gps_vdop_max': round(float(hdop[:, 2].max()), 1),
        'receiver_hdop_median': round(float(np.median(rdop[:, 1])), 2), 'receiver_vdop_median': round(float(np.median(rdop[:, 2])), 2),
        'gps_l1_cn0_mean_per_sat': {s: round(float(np.mean(list(cn0[s].values()))), 1) for s in order},
        'signal_cn0': sig,
    }
    (ROOT / 'results/report_stats.json').write_text(json.dumps(stats, indent=1) + '\n')
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
