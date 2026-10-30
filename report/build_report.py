#!/usr/bin/env python3
"""Fill the course Word template (PolyU_AAE4203_Lab_report_template.docx) with this
repository's results and figures.

Output: report/GXX_Lab1_Report.docx (convert to PDF with LibreOffice or Word).
Needs  : lxml, pandoc (for the extra equations); run src/report_figures.py and
         src/plot_3d.py first.
Text in [[double brackets]] is a placeholder for the group to fill in; it is
highlighted yellow in the document.
Usage  : python report/build_report.py
"""
import copy
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'course_repo/Lab1/PolyU_AAE4203_Lab_report_template.docx'
OUT = ROOT / 'report/GXX_Lab1_Report.docx'
REPO_URL = 'https://github.com/saul-gitman/AAE-4004-lab'

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'}
W = '{%s}' % NS['w']
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'


def el(tag, **attrs):
    p, t = tag.split(':')
    e = etree.Element('{%s}%s' % (NS[p], t))
    for k, v in attrs.items():
        e.set(W + k, str(v))
    return e


# ------------------------------------------------------------------ run helpers
def make_runs(text, base_rpr=None):
    """'**bold**', '*italic*' and '[[placeholder]]' (yellow) markup -> list of w:r."""
    runs = []
    for part in re.split(r'(\*\*.+?\*\*|\[\[.+?\]\]|(?<!\*)\*[^*]+?\*(?!\*))', text):
        if not part:
            continue
        rpr = copy.deepcopy(base_rpr) if base_rpr is not None else el('w:rPr')
        if part.startswith('**'):
            rpr.append(el('w:b'))
            part = part[2:-2]
        elif part.startswith('[['):
            h = el('w:highlight')
            h.set(W + 'val', 'yellow')
            rpr.append(h)
            part = '[' + part[2:-2] + ']'
        elif part.startswith('*'):
            rpr.append(el('w:i'))
            part = part[1:-1]
        r = el('w:r')
        if len(rpr):
            r.append(rpr)
        for i, chunk in enumerate(part.split('\t')):
            if i:
                r.append(el('w:tab'))
            if chunk:
                t = el('w:t')
                t.text = chunk
                t.set(XML_SPACE, 'preserve')
                r.append(t)
        runs.append(r)
    return runs


def set_text(p, text, keep_rpr=True):
    """Replace a paragraph's runs (not its pPr/bookmarks) with marked-up text."""
    first = p.find('w:r', NS)
    first = first.find('w:rPr', NS) if first is not None else None
    base = copy.deepcopy(first) if (keep_rpr and first is not None) else None
    if base is not None:
        for h in base.findall('w:highlight', NS):
            base.remove(h)
    for child in list(p):
        if child.tag in (W + 'r', W + 'hyperlink') or child.tag.endswith('}oMath'):
            p.remove(child)
    for r in make_runs(text, base):
        p.append(r)
    return p


def ppr_add(p, tag):
    """Insert an empty pPr child in schema order (after pStyle / keepNext)."""
    ppr = p.find('w:pPr', NS)
    if ppr.find(tag, NS) is not None:
        return
    pos = 0
    for i, c in enumerate(ppr):
        if c.tag in (W + 'pStyle', W + 'keepNext', W + 'keepLines'):
            pos = i + 1
    ppr.insert(pos, el(tag))


def clone(proto, text=None):
    p = copy.deepcopy(proto)
    for b in p.findall('.//w:bookmarkStart', NS) + p.findall('.//w:bookmarkEnd', NS):
        b.getparent().remove(b)
    if text is not None:
        set_text(p, text)
    return p


def cell_text(tc, text):
    p = tc.find('w:p', NS)
    for extra in tc.findall('w:p', NS)[1:]:
        tc.remove(extra)
    set_text(p, text)


# --------------------------------------------------------------- figure helper
class Media:
    def __init__(self, unpacked):
        self.dir = unpacked
        self.rels = etree.parse(str(unpacked / 'word/_rels/document.xml.rels'))
        self.n = 0

    def add(self, png):
        self.n += 1
        name = f'report_fig{self.n}.png'
        shutil.copy(png, self.dir / 'word/media' / name)
        rid = f'rIdFig{self.n}'
        rel = etree.SubElement(self.rels.getroot(),
                               '{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')
        rel.set('Id', rid)
        rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image')
        rel.set('Target', f'media/{name}')
        return rid

    def save(self):
        self.rels.write(str(self.dir / 'word/_rels/document.xml.rels'), xml_declaration=True,
                        encoding='UTF-8', standalone=True)


def figure_par(proto_caption, media, png, width_in):
    w_px, h_px = Image.open(png).size
    cx = int(width_in * 914400)
    cy = int(cx * h_px / w_px)
    rid = media.add(png)
    n = 1000 + media.n
    xml = f'''<w:p xmlns:w="{NS['w']}" xmlns:wp="{NS['wp']}" xmlns:a="{NS['a']}" xmlns:pic="{NS['pic']}" xmlns:r="{NS['r']}">
<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr>
<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>
<wp:docPr id="{n}" name="Figure {n}"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="{png.name}"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
    return etree.fromstring(xml)


def caption(proto, label, text):
    p = clone(proto)
    runs = p.findall('w:r', NS)
    runs[0].find('w:t', NS).text = f'{label}: '
    for r in runs[1:]:
        p.remove(r)
    for r in make_runs(text):
        p.append(r)
    p.find('w:pPr/w:ind', NS).set(W + 'left', '600')
    p.find('w:pPr/w:ind', NS).set(W + 'right', '600')
    return p


def omml_equations(md_file):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'eq.docx'
        subprocess.run(['pandoc', str(md_file), '-o', str(out)], check=True)
        xml = zipfile.ZipFile(out).read('word/document.xml')
    doc = etree.fromstring(xml)
    order = {'dPr': ['begChr', 'sepChr', 'endChr', 'grow', 'shp', 'ctrlPr'], 'mcPr': ['count', 'mcJc']}
    for name, seq in order.items():          # pandoc writes these children out of schema order
        for node in doc.iter('{%s}%s' % (NS['m'], name)):
            kids = sorted(node, key=lambda k: seq.index(etree.QName(k).localname))
            for k in kids:
                node.append(k)
    return doc.findall('.//m:oMath', NS)


def equation_par(proto, omath, number):
    p = copy.deepcopy(proto)
    old = p.find('m:oMath', NS)
    old.addprevious(copy.deepcopy(omath))
    p.remove(old)
    p.find('w:pPr/w:ind', NS).set(W + 'left', '700')
    for t in p.findall('.//w:t', NS):
        if re.fullmatch(r'\s*,?\s*\(\d\)', t.text or ''):
            t.text = t.text.replace(re.search(r'\d', t.text).group(), str(number))
    return p


# --------------------------------------------------------------------- content
def load_stats():
    s = json.loads((ROOT / 'results/report_stats.json').read_text())
    bench = json.loads((ROOT / 'results/benchmark/summary.json').read_text())
    klob = json.loads((ROOT / 'data/csv/klobuchar_from_ubx.json').read_text())
    return s, bench, klob


def fmt3(v):
    return ' / '.join(f'{x:.2f}' for x in v)


CODE = '''def gps_solution(sp, pr, clk, ion, trp, tgd, seed):
    """One GPS clock, weighted LS, Sagnac correction."""
    x = np.r_[seed.copy(), 0.0]            # [x, y, z, b], b in metres
    corrected = pr + clk - ion - trp - tgd
    for _ in range(30):
        delta = sp - x[:3]
        ranges = np.linalg.norm(delta, axis=1)
        H = np.column_stack((-delta / ranges[:, None],
                             np.ones(len(sp))))
        sagnac = OMGE / C * (sp[:, 0]*x[1] - sp[:, 1]*x[0])
        if np.linalg.norm(x[:3]) > 6e6:     # elevation weights
            lat, lon, _ = ecef_to_lla(*x[:3])
            phi, lam = np.radians([lat, lon])
            up = np.array([np.cos(phi)*np.cos(lam),
                           np.cos(phi)*np.sin(lam), np.sin(phi)])
            sine = delta @ up / ranges
            weights = np.maximum(sine, 0.05)**2
        else:                               # first iterations from Earth centre
            weights = np.ones(len(sp))
        scale = np.sqrt(weights)
        dx, _, rank, _ = np.linalg.lstsq(
            H * scale[:, None],
            (corrected - ranges - sagnac - x[3]) * scale, rcond=None)
        if rank < 4:
            raise ValueError('Insufficient geometry')
        x += dx
        if np.linalg.norm(dx) < 1e-4:
            if 6.30e6 < np.linalg.norm(x[:3]) < 6.42e6:
                return x[:3], x[3]
            break
    raise ValueError('GPS WLS did not converge to a surface position')'''


def build():
    s, bench, klob = load_stats()
    a_all, a_st = s['spp_minus_receiver_all'], s['spp_minus_receiver_static']
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(TEMPLATE) as z:
        z.extractall(tmp)
    for f in tmp.rglob('*'):
        if f.is_symlink():
            f.unlink()
    doc = etree.parse(str(tmp / 'word/document.xml'))
    body = doc.getroot().find('w:body', NS)
    E = list(body)
    media = Media(tmp)
    eqs = omml_equations(ROOT / 'report/equations.md')

    P_BODY, P_PLAIN, P_BULLET, P_H1 = E[21], E[62], E[28], E[33]
    P_CAP, P_LISTCAP, P_EQ1, P_EQ2, P_REF = E[38], E[65], E[56], E[58], E[94]
    T_SITE, T_LOG, T_CODE, T_VAL, T_ABL = E[37], E[43], E[63], E[75], E[80]
    P_APPX = E[98]

    def body_p(text):
        return clone(P_BODY, text)

    def plain_p(text):
        p = clone(P_PLAIN, text)
        p.find('w:pPr/w:spacing', NS).set(W + 'before', '160')
        return p

    def sub_h(text):
        p = plain_p(f'**{text}**')
        ppr_add(p, 'w:keepNext')
        return p

    def bullet(text):
        return clone(P_BULLET, text)

    def h1(text):
        return clone(P_H1, text)

    # ---------------------------------------------------------------- cover
    set_text(E[10], 'Group:\t[[Group XX]]')
    set_text(E[11], 'Members:\t[[Name (Leader); Name; Name; Name]]')
    set_text(E[12], 'Member IDs:\t[[ID; ID; ID; ID]]')
    st_h, st_p95 = s['static_radius_p50_m'], s['static_radius_p95_m']
    set_text(E[21], (
        'We logged 14.2 min of 1 Hz raw multi-GNSS measurements with a u-blox ZED-F9P receiver near Block X, PolyU, '
        'on 30 October 2026. The antenna moved for the first 5.9 min (two laps of a loop of about 50 m) and was '
        'static for 8.3 min. GPS L1 pseudoranges were corrected for broadcast satellite orbit and clock, group delay, '
        'Klobuchar ionosphere (coefficients decoded from the logged subframes) and Saastamoinen troposphere, using a '
        'Python port of the course rinex2csv.m that we verified against the MATLAB output. Position and clock bias '
        'were then estimated per epoch by elevation-weighted iterative least squares. '
        f'{s["epochs_solved"]} of {s["epochs_obs"]} epochs (98.2 %) were solved with 4–7 GPS satellites (median '
        f'HDOP {s["gps_hdop_median"]}). The static position is 22.305585° N, 114.179976° E, h = 18.2 m; its '
        f'horizontal scatter has a median radius of {st_h} m and a 95th percentile of {st_p95:.0f} m, and it agrees '
        'with the receiver’s multi-GNSS solution to 1.1 m horizontally and 6.2 m vertically. The largest errors '
        'come from weak, newly acquired signals. On the UrbanNav benchmark the GPS-only baseline solved '
        f'{bench["coverage_percent"]:.2f} % of epochs ([[2D RMSE, rank and improvements: fill in]]).'))

    for e in (E[17], E[18], E[19], E[23]):   # empty cover spacers: keep the cover on one page
        body.remove(e)
    # Rebuild everything between the cover and sectPr.
    start = 26          # empty paragraph before the first section
    sect = E[-1]
    for e in E[start + 1:-1]:
        body.remove(e)
    new = []
    add = new.append

    # ------------------------------------------------------- 1 Data collection
    add(h1('Data Collection'))
    add(body_p(
        'A u-blox ZED-F9P receiver board ([[kit Kxx]]) with [[antenna model]] was connected by USB to a laptop '
        'running u-center [[version]] (port COM6). The receiver output 46 UBX message types and NMEA sentences at '
        '1 Hz. The ones used here are UBX-RXM-RAWX (code, carrier phase, Doppler and C/N₀ per signal), RXM-SFRBX '
        '(broadcast navigation subframes), NAV-HPPOSECEF and NAV-PVT (the receiver’s own solution and speed), '
        'NAV-SAT (azimuth and elevation) and NAV-DOP. The antenna was placed [[mounting: tripod / ground / bench]] in '
        'the semi-open area near Block X; surroundings: [[buildings, trees and sky view in four directions; weather]].'))
    add(body_p(
        'Logging started at 08:12:47 UTC (08:13:05 GPST). The receiver’s ground speed (NAV-PVT) had a median of '
        '1.0 m/s until 08:18:56 GPST, and both our solution and the receiver’s solution trace the same loop of '
        'about 51 m × 53 m twice (311 m in 5.9 min, Fig. 3). From 08:18:57 GPST (time of week 461 937 s) the '
        'speed stayed below 0.1 m/s, so the static part lasts 8.3 min (501 epochs), shorter than the 15–20 min the '
        'lab asks for. Tracking ended at 08:27:16 GPST: the file continues to 08:31:00, but its last 223 RXM-RAWX '
        'messages contain no measurements, so the RINEX file holds 853 epochs. The site and log are summarised in '
        'Table 1.'))
    site = copy.deepcopy(T_SITE)
    add(site)
    add(caption(P_CAP, 'Figure 1', '[[Insert site photo and the four sky photos]]. Data collection environment near Block X.'))
    cap1 = clone(P_CAP)
    for r in cap1.findall('w:r', NS):
        cap1.remove(r)
    cap1.append(make_runs('**Table 1: **')[0])
    for r in make_runs('Data collection summary.'):
        cap1.append(r)
    ppr_add(cap1, 'w:keepNext')
    add(cap1)
    t1 = copy.deepcopy(T_LOG)
    rows = t1.findall('w:tr', NS)
    proto_row = rows[1]
    for r in rows[1:]:
        t1.remove(r)
    for field, value in [
            ('Location', 'Near Block X, PolyU; static point 22.305585° N, 114.179976° E, h = 18.2 m (WGS-84)'),
            ('Date / time', '30 Oct 2026, 08:13:05–08:27:16 GPST (08:12:47–08:26:58 UTC)'),
            ('Duration', '14.2 min at 1 Hz (853 epochs): 5.9 min moving + 8.3 min static'),
            ('Receiver', 'u-blox ZED-F9P ([[kit Kxx]]), [[antenna]]'),
            ('Software', 'u-center [[version]]; RTKCONV-EX 2.5.1; Python 3.13'),
            ('Signals', 'GPS L1 C/A, L2C; Galileo E1, E5b; BeiDou B1I, B2I; GLONASS L1, L2'),
            ('Raw file', 'COM6___9600_261030_081848.ubx (11.6 MB), data/raw/ in GitHub'),
            ('Weather', '[[weather, temperature]]')]:
        row = copy.deepcopy(proto_row)
        c = row.findall('w:tc', NS)
        cell_text(c[0], field)
        cell_text(c[1], value)
        c[0].find('w:tcPr/w:tcW', NS).set(W + 'w', '1700')
        c[1].find('w:tcPr/w:tcW', NS).set(W + 'w', '7300')
        c[1].find('w:p/w:pPr/w:jc', NS).set(W + 'val', 'left')
        t1.append(row)
    last = t1.findall('w:tr', NS)[-1]
    for tc in last.findall('w:tc', NS):
        bd = tc.find('w:tcPr/w:tcBorders', NS)
        bottom = bd.find('w:bottom', NS)
        bottom.set(W + 'val', 'single')
        bottom.set(W + 'sz', '4')
        bottom.set(W + 'color', '000000')
    grid = t1.find('w:tblGrid', NS).findall('w:gridCol', NS)
    grid[0].set(W + 'w', '1700')
    grid[1].set(W + 'w', '7300')
    add(t1)

    # ----------------------------------------------------- 2 Raw data analysis
    add(h1('Raw Data Analysis'))
    m = s['sats_mean_per_constellation']
    sig = s['signal_cn0']
    add(body_p(
        f'RXM-RAWX holds 40 775 signal measurements. On average {m["GPS"]} GPS, {m["Galileo"]} Galileo, '
        f'{m["BeiDou"]} BeiDou and {m["GLONASS"]} GLONASS satellites had a valid pseudorange per epoch (Fig. 2a). '
        'Only 7 GPS satellites (G02, G04, G08, G09, G16, G27, G31) had a broadcast ephemeris in the log; G03, G26 and '
        'G28 were tracked but no ephemeris was decoded in the 14 min. The GPS-only solver therefore used 4 (148 '
        'epochs), 5 (404), 6 (279) or 7 (7) satellites.'))
    add(body_p(
        f'Median C/N₀ was {sig["G L1C/A"]["median_cn0"]:.0f} dB-Hz for GPS L1 C/A, '
        f'{sig["G L2CL"]["median_cn0"]:.0f} for L2C, {sig["E E1C"]["median_cn0"]:.0f}/{sig["E E5bQ"]["median_cn0"]:.0f} '
        f'for Galileo E1/E5b, {sig["C B1I D1"]["median_cn0"]:.0f}/{sig["C B2I D1"]["median_cn0"]:.0f} for BeiDou B1I/B2I '
        f'and {sig["R L1OF"]["median_cn0"]:.0f}/{sig["R L2OF"]["median_cn0"]:.0f} dB-Hz for GLONASS L1/L2. For GPS L1 '
        '(Fig. 2b), the two highest satellites G27 (73–79°) and G08 (56–63°) were steady at about 47 dB-Hz once static. '
        'G04, at 59° elevation, averaged only 37 dB-Hz and repeatedly dropped to about 20 dB-Hz and lost lock. A weak '
        'signal from a high satellite suggests that something near the antenna blocked or diffracted it '
        '[[check against the site photos]]. Following the tutorial’s rule of thumb (> 40 dB-Hz strong, '
        '< 30 dB-Hz at moderate elevation suspicious), G02, G03, G26 and G28 (25–29 dB-Hz mean) were weak. While '
        'walking, all signals fluctuated strongly because of body blockage and changing multipath.'))
    add(body_p(
        'The sky plot (Fig. 2c) shows satellites in all directions. The GPS satellites used were G27 (73–79°), '
        'G04 (59°), G08 (56–63°), G16 (41–45°), G09 (31–35°), G31 (29–32°) and G02 (15–16°, at the mask). '
        f'With these satellites the GPS-only HDOP had a median of {s["gps_hdop_median"]} (max {s["gps_hdop_max"]}) '
        f'and VDOP {s["gps_vdop_median"]} (max {s["gps_vdop_max"]}), against {s["receiver_hdop_median"]} and '
        f'{s["receiver_vdop_median"]} for the receiver’s multi-GNSS solution (Fig. 2d). The DOP spikes occur when '
        'only 4 GPS satellites remain. With the tutorial’s user range error of 5.7 m, the median GPS-only '
        'geometry gives roughly 8 m horizontal and 15 m vertical 1σ error.'))
    add(figure_par(P_CAP, media, ROOT / 'figures/raw_data_quality.png', 6.4))
    add(caption(P_CAP, 'Figure 2', 'Raw data quality: (a) satellites with a valid pseudorange per constellation and '
                'GPS satellites used by the solver; (b) GPS L1 C/A C/N₀; (c) sky plot from NAV-SAT; (d) GPS-only '
                'DOP of the satellites used versus the receiver’s multi-GNSS DOP. Dashed line in (a): start of '
                'the static part.'))

    # --------------------------------------------------------------- 3 SPP
    add(h1('SPP Algorithm (Least Squares)'))
    add(body_p(
        'Each epoch is solved independently from GPS L1 C/A pseudoranges with the course solver WLSE_spp.py in its '
        'gps mode [1, 2]. The measurement model is'))
    eq1 = copy.deepcopy(P_EQ1)
    add(eq1)
    add(plain_p(
        'where x is the receiver ECEF position, sᵢ the satellite position at signal transmission, cΔt = b '
        'the receiver clock bias in metres and εᵢ the remaining noise, multipath and NLOS error. The '
        'satellite position and clock come from the broadcast ephemeris (RTKLIB eph2pos [6]), evaluated at the '
        'transmission time tᵣ − ρᵢ/c − δtˢᵢ, with the relativistic clock term. '
        'Each pseudorange is then corrected and modelled as'))
    add(equation_par(P_EQ1, eqs[0], 3))
    add(plain_p(
        'with the satellite clock δtˢᵢ, the group delay Tᴳᴰ from the ephemeris, the '
        'Klobuchar ionosphere Iᵢ [4] and the Saastamoinen troposphere Tᵢ (standard atmosphere, 70 % humidity) '
        '[5]. The last term of the range is the Earth-rotation (Sagnac) correction. RTKCONV wrote no ionosphere '
        'coefficients to the NAV file, so we decoded them from the logged RXM-SFRBX subframe 4 page 18 (three '
        'identical copies, from G08, G27 and G31): '
        f'α = ({", ".join(f"{v:.3e}" for v in klob["alpha"])}), '
        f'β = ({", ".join(f"{v:.0f}" for v in klob["beta"])}). '
        'Linearising (3) about the current estimate gives the design-matrix row and misclosure'))
    add(equation_par(P_EQ1, eqs[1], 4))
    add(plain_p('and the weighted least-squares update'))
    add(copy.deepcopy(P_EQ2))
    add(plain_p('with elevation weights'))
    add(equation_par(P_EQ1, eqs[2], 5))
    add(plain_p(
        'Iteration starts from the previous epoch’s solution (from the Earth’s centre for the first epoch) and '
        'stops when ‖δ‖ < 10⁻⁴ m (at most 30 iterations); a solution is accepted only if its '
        'distance from the Earth’s centre is 6300–6420 km. Satellites are used if healthy, with elevation ≥ 15° '
        'and C/N₀ ≥ 15 dB-Hz; epochs with fewer than four are omitted, never filled.'))
    add(plain_p(
        'The course converter rinex2csv.m needs MATLAB, so we ported it line by line to Python (src/rinex2csv.py). On '
        'the UrbanNav benchmark it converts the same 1437 of 1534 epochs as the MATLAB-generated benchmark/gps_csv, '
        'with an identical missing-data pattern and identical pseudoranges and group delays. On all epochs that do '
        'not use G02, satellite positions agree to 2×10⁻⁷ m and clocks, ionosphere and troposphere to '
        '10⁻⁹ m. For G02 the benchmark NAV holds two valid ephemerides and the two codes pick different ones '
        '(≤ 0.29 m clock, ≤ 1 m orbit difference). Our own NAV file has one ephemeris per satellite, so this '
        'cannot occur there.'))

    # -------------------------------------------------------- 4 Code listing
    add(h1('Code Listing'))
    add(plain_p(f'Listing 1 is the per-epoch solver used (unchanged from the course). Full code, data and a '
                f'one-command rebuild (run_all.sh) are at {REPO_URL}.'))
    tc = copy.deepcopy(T_CODE)
    cell = tc.find('.//w:tc', NS)
    paras = cell.findall('w:p', NS)
    proto = paras[1]
    rpr = None
    for r in proto.findall('w:r', NS):
        if r.find('w:rPr/w:b', NS) is None:
            rpr = copy.deepcopy(r.find('w:rPr', NS))
            break
    for sz in rpr.findall('w:sz', NS) + rpr.findall('w:szCs', NS):
        sz.set(W + 'val', '17')
    for p in paras:
        cell.remove(p)
    for line in CODE.split('\n'):
        p = copy.deepcopy(proto)
        for r in p.findall('w:r', NS):
            p.remove(r)
        r = el('w:r')
        r.append(copy.deepcopy(rpr))
        t = el('w:t')
        t.text = line
        t.set(XML_SPACE, 'preserve')
        r.append(t)
        p.append(r)
        p.find('w:pPr/w:spacing', NS).set(W + 'line', '220')
        cell.append(p)
    add(tc)
    lc = clone(P_LISTCAP)
    lc.findall('w:r', NS)[1].find('w:t', NS).text = 'Per-epoch weighted least-squares solver (WLSE_spp.py, gps_solution).'
    add(lc)

    # -------------------------------------------------- 5 Own-data validation
    add(h1('Own-Data Validation'))
    add(body_p(
        'There is no ground truth for our own data, so this section tests agreement and consistency, not accuracy. '
        'Solutions are matched by GPS time of week, and differences are rotated into East/North/Up at the static '
        'position.'))
    add(sub_h('Comparison with independent solutions'))
    add(body_p(
        f'Table 2 compares our solution with the receiver’s own solution (NAV-HPPOSECEF, multi-GNSS, cm-to-m units '
        f'converted) over all {a_all["epochs"]} solved epochs and over the {a_st["epochs"]} static epochs. The median '
        f'differences are below 0.8 m horizontally ({fmt3(a_all["median_enu_m"])} m E/N/U), and half of the epochs '
        f'agree within {a_all["p50_2d_m"]:.1f} m horizontally. The means, standard deviations and RMS values are '
        f'much larger ({a_all["rms_2d_m"]:.1f} m 2D RMS) because they are dominated by a few tens of outlier epochs. '
        'Fig. 3 shows both solutions following the two walking laps. While static, the receiver solution stays within '
        'about 1 m horizontally, but ours jumps by 10–40 m whenever the set of GPS satellites changes (for example at '
        '9.5, 10–10.8 and 13.3 min), as expected for GPS-only single-frequency SPP with 5–6 satellites. '
        '[[RTKPOST: process data/rinex/*.obs and *.nav in Single mode and fill the RTKPOST column.]]'))
    add(figure_par(P_CAP, media, ROOT / 'figures/enu_timeseries.png', 6.3))
    add(caption(P_CAP, 'Figure 3', 'East, North and Up of our WLS solution and of the receiver solution against '
                'time, relative to the static position (axes clipped at ±60 m; shaded: antenna moving).'))
    cap2 = clone(E[73])
    ppr_add(cap2, 'w:keepNext')
    for r in cap2.findall('w:r', NS):
        cap2.remove(r)
    cap2.append(make_runs('**Table 2: **')[0])
    for r in make_runs('Differences between solutions for our own data (WLS SPP minus reference), in metres.'):
        cap2.append(r)
    add(cap2)
    t2 = copy.deepcopy(T_VAL)
    grid = t2.find('w:tblGrid', NS)
    grid.append(copy.deepcopy(grid.findall('w:gridCol', NS)[-1]))
    for g, wdt in zip(grid.findall('w:gridCol', NS), (2500, 2300, 2300, 2300)):
        g.set(W + 'w', str(wdt))
    rows = t2.findall('w:tr', NS)
    vals = [('Statistic', 'SPP − RTKPOST', 'SPP − receiver (all)', 'SPP − receiver (static)'),
            ('Mean E / N / U (m)', '[[–]]', fmt3(a_all['mean_enu_m']), fmt3(a_st['mean_enu_m'])),
            ('Std E / N / U (m)', '[[–]]', fmt3(a_all['std_enu_m']), fmt3(a_st['std_enu_m'])),
            ('2D RMS difference (m)', '[[–]]', f'{a_all["rms_2d_m"]:.2f}', f'{a_st["rms_2d_m"]:.2f}'),
            ('Epochs compared', '[[–]]', str(a_all['epochs']), str(a_st['epochs']))]
    extra = [('Median E / N / U (m)', '[[–]]', fmt3(a_all['median_enu_m']), fmt3(a_st['median_enu_m'])),
             ('2D P50 / P95 (m)', '[[–]]', f'{a_all["p50_2d_m"]:.2f} / {a_all["p95_2d_m"]:.2f}',
              f'{a_st["p50_2d_m"]:.2f} / {a_st["p95_2d_m"]:.2f}')]
    for r in rows:
        r.append(copy.deepcopy(r.findall('w:tc', NS)[-1]))
    for k, extra_row in enumerate(extra):          # insert before 'Epochs compared'
        nr = copy.deepcopy(rows[2])
        rows[-1].addprevious(nr)
        vals.insert(4 + k, extra_row)
    for r, v in zip(t2.findall('w:tr', NS), vals):
        for tcell, txt in zip(r.findall('w:tc', NS), v):
            cell_text(tcell, txt)
        for tcell, wdt in zip(r.findall('w:tc', NS), (2500, 2300, 2300, 2300)):
            tcell.find('w:tcPr/w:tcW', NS).set(W + 'w', str(wdt))
        for sz in r.findall('.//w:sz', NS):
            sz.set(W + 'val', '21')
    add(t2)
    add(sub_h('Static-solution consistency'))
    add(body_p(
        f'{a_st["epochs"]} of the 501 static epochs were solved (99.4 %; 838/853 = 98.2 % overall). Fig. 4 shows the '
        f'static East–North scatter about its median. The median horizontal radius is {st_h} m and the 95th '
        f'percentile {st_p95:.1f} m, but {s["static_epochs_beyond_50m_h"]} static epochs lie more than 50 m away. '
        f'Because of them, the standard deviations are {fmt3(s["static_std_enu_m"])} m (E/N/U) and the mean is '
        f'offset from the median by {fmt3(s["static_mean_enu_about_median_m"])} m. The scatter has a clear structure: '
        'points line up along a few directions and form clusters that persist for tens of seconds. These are '
        'geometry and satellite-set changes, not random noise. For comparison, the receiver’s own static solution '
        'has standard deviations of 0.36 / 0.25 / 2.04 m and its median lies 0.5 m E, 1.0 m N and 6.2 m U from ours.'))
    add(figure_par(P_CAP, media, ROOT / 'figures/static_en_scatter.png', 4.2))
    add(caption(P_CAP, 'Figure 4', 'East–North scatter of the static WLS solution about its median, with the '
                'receiver solution; circles: 50th and 95th percentile horizontal radius.'))
    add(sub_h('Input checks'))
    add(body_p(
        'Post-fit residuals locate the outliers. In the worst epochs (residuals up to 620 m) G04 or G31 has just '
        'been re-acquired: C/N₀ 19–25 dB-Hz, lock time 0 ms and RXM-RAWX pseudorange standard deviation '
        '10–41 m, against 0.08–0.32 m for the other satellites. The baseline’s 15 dB-Hz mask accepts these '
        'measurements, and with only 5–6 satellites one bad pseudorange moves the solution by tens to hundreds of '
        'metres. A C/N₀ mask of 25–30 dB-Hz, a lock-time or pseudorange-std check, or residual-based exclusion '
        'should remove most of them. These are the first improvements to test.'))

    # ------------------------------------------------------- 6 Benchmark
    add(h1('Benchmark Results'))
    add(body_p(
        'The GPS-only baseline (course cache benchmark/gps_csv, WLSE_spp.py --mode gps) solved '
        f'{bench["solved_epochs"]} of {bench["input_epochs"]} epochs ({bench["coverage_percent"]:.2f} %), above the '
        '90 % ranking threshold. The omitted epochs have fewer than four usable GPS satellites after the 15° '
        'elevation mask. GXX_benchmark.csv passes check_submission.py. The scoring reference is withheld, so RMSE '
        'values come only from the leaderboard (Table 3). [[Add each improvement you test, one at a time, and '
        'check it on the example dataset first.]]'))
    cap3 = clone(E[79])
    ppr_add(cap3, 'w:keepNext')
    for r in cap3.findall('w:r', NS):
        cap3.remove(r)
    cap3.append(make_runs('**Table 3: **')[0])
    for r in make_runs('Ablation on the benchmark dataset.'):
        cap3.append(r)
    add(cap3)
    t3 = copy.deepcopy(T_ABL)
    rows = t3.findall('w:tr', NS)
    ablation = [('v1', 'GPS-only baseline', '[[leaderboard]]', '[[leaderboard]]', f'{bench["coverage_percent"]:.2f}'),
                ('v2', 'C/N₀ mask 25–30 dB-Hz', '[[–]]', '[[–]]', '[[–]]'),
                ('v3', '+ residual-based exclusion', '[[–]]', '[[–]]', '[[–]]'),
                ('v4', '+ BeiDou and Galileo', '[[–]]', '[[–]]', '[[–]]')]
    for r, v in zip(rows[1:], ablation):
        for tcell, txt in zip(r.findall('w:tc', NS), v):
            cell_text(tcell, txt)
    add(t3)
    add(body_p(
        '[[Final 2D RMSE … m, 3D RMSE … m, 2D P95 … m, availability … %, leaderboard rank …]]. UrbanNav-HK-Deep-'
        'Urban-1 [3] is recorded in a dense street canyon in Hong Kong. Tall buildings block most of the sky, so few '
        'satellites remain and the geometry is poor (high DOP). Many of the signals received are reflected '
        '(multipath) or arrive only by reflection (NLOS), which adds positive range biases of tens of metres. Our '
        'own data shows the same mechanisms on a smaller scale: weak, newly acquired signals and satellite-set '
        'changes cause most of the error, and adding constellations improves the geometry (multi-GNSS HDOP 0.57 vs '
        'GPS-only 1.46).'))

    # ---------------------------------------------------------- 7 AI use
    add(h1('AI-Use Statement'))
    add(body_p(
        'We used Claude Code (Anthropic) through claude.ai/code for: porting rinex2csv.m to Python; writing the '
        'UBX-to-CSV conversion, the Klobuchar decoding and the plotting scripts; running the course solver and '
        'computing the statistics; and drafting the text of this report. We verified its output in four ways. '
        '(i) The Python converter was compared value by value with the course’s MATLAB benchmark CSVs (Section 3). '
        '(ii) The subframe decoding was checked by reproducing the ephemeris parameters RTKCONV wrote to the NAV '
        'file. (iii) The course checker was run on both CSVs, and the benchmark baseline reproduces the documented '
        '1437/1534 epochs. (iv) The own-data solution was compared with the receiver’s independent solution. '
        '[[State what each member checked and confirm that you understand the code.]] Key prompts are listed in '
        'Appendix B.'))

    # ------------------------------------------- 8 Repository / submission
    add(h1('Repository and Submission'))
    for t in [f'GitHub repository: {REPO_URL}. It contains the raw UBX log, the RINEX files, all CSVs, the scripts, '
              'the figures and a copy of the course Lab1 folder.',
              '“GROUP=GXX ./run_all.sh” rebuilds GXX_owndata.csv, GXX_benchmark.csv, the figures and the '
              'statistics from the raw files; a rerun gives byte-identical CSVs.',
              'Both CSVs pass tools/check_submission.py (own data 838 rows, 98.24 %; benchmark 1437 rows, 93.68 %). '
              '[[Rename GXX to your group number and upload to the TA’s Google Drive folder.]]']:
        add(bullet(t))

    # ---------------------------------------------------------- References
    add(h1('References'))
    refs = [E[94], E[95], E[96]]
    for r in refs:
        add(clone(r))
    for t in ['J. A. Klobuchar, “Ionospheric time-delay algorithm for single-frequency GPS users,” IEEE '
              'Trans. Aerosp. Electron. Syst., vol. AES-23, no. 3, pp. 325–331, 1987.',
              'J. Saastamoinen, “Atmospheric correction for the troposphere and stratosphere in radio ranging of '
              'satellites,” in The Use of Artificial Satellites for Geodesy, Geophys. Monogr. 15, AGU, 1972.',
              'T. Takasu, RTKLIB: An Open Source Program Package for GNSS Positioning, v2.4.3, 2013; '
              'rtklibexplorer RTKLIB-EX 2.5.1.',
              'u-blox, ZED-F9P Interface Description (UBX-RXM-RAWX, RXM-SFRBX, NAV-HPPOSECEF).',
              'W. Wen, AAE4203 Lab 1 course repository, https://github.com/weisongwen/AAE4203-S12627 (commit ab9f0cd).']:
        add(clone(P_REF, t))

    # ---------------------------------------------------------- Appendices
    pa = clone(P_APPX, 'A Supplementary Figure')
    ppr_add(pa, 'w:pageBreakBefore')
    add(pa)
    add(figure_par(P_CAP, media, ROOT / 'figures/position_3d.png', 6.6))
    add(caption(P_CAP, 'Figure A1', 'WLS positions in 3D local ENU: the whole log (left) and the static part '
                '(right); colour = time, orange = receiver solution, star = static position. An animation of the '
                'whole log is in figures/position_track.gif in the repository.'))
    add(clone(P_APPX, 'B Key AI Prompts'))
    for t in ['“The ubx is the raw data; obs and nav were converted with RTKCONV … use the GitHub repo as file '
              'storage; put the raw data, processed data and the course repo; I want the CSV of the raw data, the '
              'CSV of the position result and a 3D plot of the result.” Verified: converter vs MATLAB benchmark '
              'CSVs, checker, receiver comparison.',
              '“Make it a GIF for the whole movement.” Verified: frames inspected against the static plot.',
              '“This is the report template; fill as much as you can.” Verified: every number in this '
              'report was regenerated from results/report_stats.json and summary.json by report/build_report.py; '
              '[[members re-read every section]].']:
        add(bullet(t))

    for e in new:
        sect.addprevious(e)
    doc.write(str(tmp / 'word/document.xml'), xml_declaration=True, encoding='UTF-8', standalone=True)
    media.save()
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(tmp.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    print('Saved:', OUT)


if __name__ == '__main__':
    build()
