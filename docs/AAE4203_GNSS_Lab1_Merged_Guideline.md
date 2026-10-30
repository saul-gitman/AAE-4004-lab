# AAE4203 Guidance and Navigation — GNSS Lab 1: Merged Practical Guideline

**Week 9 · Semester 1, 2026/27 · Laboratory session: 30 October 2026**  
**Topic:** GNSS data collection, single-point positioning (SPP), weighted least squares (WLS), and an urban accuracy challenge  
**Instructor:** Dr Weisong Wen, Department of Aeronautical and Aviation Engineering, The Hong Kong Polytechnic University

> **Purpose of this document:** One actionable guideline merging the **30-page Laboratory Tutorial**, the **Week 9 GNSS Laboratory slide deck**, and the practical instructions in the **course GitHub Lab1 repository**. Repeated material is consolidated, and relevant differences between the lecture documents and the runnable repository are explained. This is **AAE4203 GNSS Lab 1 only**. It is an operational guide, not a submission-ready report or a substitute for your group's measurements and analysis.
>
> **Authoritative administrative source:** Blackboard and the teaching team control final deadlines, marking, and submission links.

**Primary sources**

- [Course GitHub — `AAE4203-S12627/Lab1`](https://github.com/weisongwen/AAE4203-S12627/tree/main/Lab1)
- [Laboratory Tutorial PDF](https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/AAE4203_26_27_S1_Lab_Tutorial.pdf) — theory, procedures, assessment, and worked examples.
- [Week 9 Lab Slides PDF](https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/AAE4203_Week9_GNSS_Lab_Slides.pdf) — laboratory sequence, screenshots, examples, and checklist.
- [Course README](https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/Readme.md) · [Running instructions](https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/docs/RUNNING.md) · [Verification notes](https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/docs/VERIFICATION.md)

---

## 1. What the lab is actually asking you to do

You are not merely entering satellite coordinates and performing one least-squares calculation. The full workflow is to **capture measurements**, turn them into usable satellite observations, **solve receiver position at each time epoch**, compare independent solutions, and improve the algorithm on a harder urban dataset.

```text
                         THREE INPUT DATASETS
  1. Group's static UBX log       2. Provided Block X example
  3. Provided UrbanNav benchmark
                 │
                 ▼
   UBX ──RTKCONV──► RINEX .obs + .nav
                 │
                 ├──RTKPOST──► independent SPP / DGNSS comparison
                 │
                 └──rinex2csv / supplied CSV cache
                          │
                          ▼
           pseudoranges + satellite positions
              + clock + atmosphere corrections
                          │
                          ▼
             Python weighted least-squares SPP
                          │
                   ECEF positions per epoch
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
       Own-data validation    Benchmark CSV + leaderboard
       + report analysis      + technique comparisons
```

**Four distinct questions:**

1. Can you **collect and convert** usable GNSS observations?
2. Can your **Python WLS solver reproduce** the supplied example?
3. Does your own static solution **agree with independent solutions and behave consistently**?
4. How accurately can your improved solver position the receiver on an **urban benchmark**?

### 1.1 Three datasets, and why they must not be mixed

| Dataset | Input | Reference status | What it is for | Ranked? |
|---|---|---|---|---|
| **Your own field data** | 15–20 min stationary `.ubx` log near PolyU Block X, converted to OBS/NAV and CSV | **No independent ground truth** | Acquisition, processing, comparison with RTKPOST and receiver solution, static-scatter analysis | No |
| **Provided Block X example (2025)** | `example/` UBX, RINEX, measurement CSVs, receiver solution, reference statistics | Known **receiver-reference** results, not survey-grade truth | Debugging, reproducibility, regression tests after code changes | No |
| **UrbanNav-HK-Deep-Urban-1 benchmark** | `benchmark/urbannav_deep1.obs`, matching `.nav`, optional preconverted `benchmark/gps_csv/` | Independent reference held by the teaching team for scoring | Improve SPP in urban conditions and produce a ranked trajectory | **Yes** |

**Non-negotiable:** The UrbanNav ground-truth trajectory is publicly available elsewhere, but using it for submission, tuning, or checking violates the lab's challenge rules. **Do not use it.** The receiver's `NAV-HPPOSECEF.csv` is also **not** ground truth and must never be submitted in place of a self-computed solution.

### 1.2 Expected outputs from each group

| Required output | Filename / format | Where it goes |
|---|---|---|
| Benchmark trajectory | `GXX_benchmark.csv` (exact five-column ECEF schema) | TA's group Google Drive folder; ranked |
| Self-collected trajectory | `GXX_owndata.csv` (same schema) | Same folder; **not** ranked |
| Lab report | PDF, **maximum 10 pages excluding cover**; code listings maximum **2 pages** | Blackboard |
| Code and data | GitHub repository with raw measurements, scripts, instructions/README and reproducible outputs | Repository link in the report |

Replace `XX` with your two-digit group number (e.g. `G05`). A demonstration file generated from `example/` **cannot** count as your group's own data.

---

## 2. Session plan, equipment, and suggested roles

### 2.1 Lab arrangements

- **3-hour** session, **20 groups**, **10 GNSS receiver kits**, **2 collection batches**.
- Groups **G01–G10** use kits **K01–K10** first, handing each kit to partner groups **G11–G20**.
- Each group collects one static UBX log and submits one set of deliverables.
- Every member must be capable of explaining the whole pipeline, regardless of role split.

| Time from start | Batch 1: G01–G10 | Batch 2: G11–G20 |
|---|---|---|
| Before class | Install tools; run example | Same |
| 0:00–0:20 | Briefing and kit pickup | Briefing |
| 0:20–0:50 | **Collect** static raw data | Test software and reproduce example |
| 0:50–0:55 | Hand kit to partner group | Receive kit |
| 0:55–1:25 | Convert, process, and validate own data | **Collect** static raw data |
| 1:25–2:00 | Recheck example; start benchmark | Return kit; convert and validate own data |
| 2:00–2:40 | Accuracy improvements and uploads | Accuracy improvements and uploads |
| 2:40–3:00 | Final uploads; preliminary ranking | Final uploads; preliminary ranking |

The final ranking uses the files at the deadline, not merely the files present when your batch finishes.

### 2.2 Equipment

- Laptop (preferably charged or connected to mains).
- **u-blox ZED-F9P** GNSS receiver/board and antenna, USB cable.
- u-center for acquiring UBX logs.
- ZED-F9P can receive GPS, Galileo, BeiDou and GLONASS; the **included baseline code is GPS-only**, which is not the same as a hardware limitation.

### 2.3 Suggested division of responsibilities

| Person / role | Main responsibility |
|---|---|
| A — Acquisition | Receiver connection, static antenna, u-center, log backup, location and sky photos |
| B — Data pipeline | RTKCONV, HK SatRef/RTKPOST, RINEX/CSV conversion |
| C — Positioning | Python SPP, example regression, improvements and benchmark |
| D — Analysis and submission | ENU plots/statistics, report, GitHub reproducibility, CSV validation and upload |

For a three-person group, combine the last two roles as appropriate.

---

## 3. Software and the course repository

### 3.1 Recommended tools

| Tool | Purpose | Requirement in practice |
|---|---|---|
| [u-center](https://www.u-blox.com/en/product/u-center) | Connect receiver and record `.ubx` | Required for acquisition |
| [RTKLIB-EX 2.5](https://github.com/rtklibexplorer/RTKLIB) | `RTKCONV`, `RTKPOST`, `RTKPLOT` | Required for conversion/reference processing |
| Python 3.9+ | WLS solver, analysis, output CSVs | Required |
| NumPy | Numerical least squares | Minimum for supplied CLI solver |
| pandas, matplotlib | Data analysis and plots | Useful for report |
| pyubx2 | Convert UBX receiver messages to CSV | Needed for GUI converter |
| MATLAB + `matRTKLIB/` | Run `rinex2csv.m`; inspect/plot RINEX | **Optional for first examples/benchmark** because CSV inputs are supplied; needed to regenerate those CSVs with the provided MATLAB function |
| Google Earth / KML | Visualise position tracks | Optional/useful |

**Source-version distinction:** The lab slides list MATLAB and a Mapping Toolbox under software requirements, but the updated tutorial and repository explicitly explain that the numeric Python example can be run without MATLAB and that the current `rinex2csv.m` itself does not need the Mapping Toolbox. Use MATLAB if you need to regenerate CSV inputs from your own RINEX data using this provided converter.

### 3.2 Main repository structure

```text
AAE4203-S12627/
└── Lab1/
    ├── Readme.md                       # Course overview and requirements
    ├── WLSE_spp.py                     # WLS-SPP Python entry point
    ├── rinex2csv.m                     # RINEX -> satellite measurement CSVs
    ├── pyubx2_csv_converter_gui.py     # UBX -> receiver message CSVs
    ├── spp.conf                        # RTKLIB settings example
    ├── requirements.txt                # Minimum numerical dependencies
    ├── requirements-optional.txt       # Additional tools
    ├── matRTKLIB/                      # MATLAB GNSS toolbox
    ├── example/                        # Block X 2025, 186-epoch example
    ├── benchmark/
    │   ├── urbannav_deep1.obs
    │   ├── urbannav_deep1.nav
    │   └── gps_csv/                   # Preprocessed GPS baseline inputs
    ├── tools/
    │   ├── check_submission.py         # CSV checks
    │   └── verify_package.py           # Package regression checks
    ├── docs/
    │   ├── RUNNING.md
    │   └── VERIFICATION.md
    ├── figures/                         # Figures from course materials
    └── legacy/                          # Older scripts retained for reference
```

### 3.3 Install and run the **existing** example first

From PowerShell/Terminal:

```bash
git clone https://github.com/weisongwen/AAE4203-S12627.git
cd AAE4203-S12627/Lab1
python --version
python -m pip install -r requirements.txt
```

**Example regression test:**

```bash
python WLSE_spp.py --reference example/NAV-HPPOSECEF.csv
python tools/check_submission.py outputs/example/G01_owndata.csv --epoch-file example/epochs.csv
```

Expected historical result:

- **186/186 epochs** solved.
- **2D RMS difference ≈ 37.911 m**, **3D RMS difference ≈ 51.043 m**, both relative to the example's **receiver solution**, not a surveyed truth.
- Outputs at `outputs/example/` include a five-column CSV, `solution_details.csv`, `omitted_epochs.csv` and `summary.json`.
- `G01_owndata.csv` above is only an **example output filename**, not a valid substitute for self-collected data.

**Important mode distinction:** Running the historical provided CSVs and re-running the raw example through the newer `rinex2csv.m` plus `--mode gps` do **not** give the same inputs/results. The refreshed GPS route may solve **113/186** epochs under the baseline masks. It is not supposed to reproduce the historical **186/186** regression.

---

## 4. Step-by-step: collect your own GNSS data

### 4.1 Choose and document the collection site

1. Work in the specified semi-open area **near Block X, PolyU**.
2. Place antenna on a stable surface and select the clearest practical sky view.
3. Keep bodies, laptops and nearby people away from the antenna to avoid obstruction and reflections.
4. Photograph the setup, surroundings, and the sky in **four directions**; record approximate location, start/end times, weather, nearby buildings and other potential NLOS/multipath sources.
5. Keep the **antenna absolutely stationary** for the entire logging period.

### 4.2 Connect receiver in u-center

1. Connect **antenna → ZED-F9P board → USB → laptop**.
2. Start u-center, select the receiver's **COM port**.
3. Set matching baud rate: common choices are **9600** or **115200 bit/s** (use what the unit is actually configured for).
4. Confirm a live stream with satellites, sky plot, **C/N₀**, and a position display.
5. Ensure raw GNSS measurement messages (not merely the screen position) are enabled, especially `UBX-RXM-RAWX`. The tutorial notes `Receiver → Debug Message` for enabling raw messages on a newly connected kit; follow the receiver and u-center version in use.

### 4.3 Record and preserve the UBX file

1. Start **Record** in u-center.
2. Choose a descriptive filename, e.g. `G05_owndata_20261030.ubx`.
3. Record **15–20 minutes** continuously without moving the antenna.
4. Check that the `.ubx` file grows throughout the recording.
5. Stop recording properly and close the file.
6. Back up the raw UBX log to **at least one second location** (two independent copies preferred).
7. Confirm files/photos/times are saved, then hand the complete kit to the partner group or TA.

**What a good raw-data package contains:** `*.ubx`, antenna/site/sky photos, collection log (date/time, environmental notes), equipment details, and a backup copy.

---

## 5. Step-by-step: convert and post-process the data

### 5.1 Convert UBX → RINEX with RTKCONV

**Goal:** Make standard GNSS measurements readable by RTKLIB and the MATLAB converter.

1. Launch `rtklaunch.exe` / **RTKCONV** from RTKLIB.
2. Input = your `.ubx` log.
3. Input format = **u-blox**.
4. Enable RINEX **observation `.obs`** and **navigation `.nav`** outputs (including applicable navigation constellation messages).
5. Convert, then inspect timestamps, number of observations and non-empty files.

| File | What it means |
|---|---|
| `.ubx` | Raw proprietary receiver stream from u-center |
| `.obs` | RINEX satellite measurements (pseudorange, Doppler, carrier phase, signal strength, etc., depending on log) |
| `.nav` | Satellite broadcast navigation data / ephemerides for finding satellite positions and clock corrections |

### 5.2 Create an independent position solution with RTKPOST

RTKPOST produces a comparison trajectory **without using your Python solver**.

**SPP:**

1. Open RTKPOST.
2. Set rover observations = your `.obs`.
3. Set navigation = matching `.nav`.
4. Positioning mode = **Single**.
5. Execute to produce a `.pos` solution.
6. Open **RTKPLOT** and inspect the E–N scatter or map; a stationary antenna should form a compact cluster, possibly drifting under multipath.
7. Optionally use **Tools → Convert to KML** for Google Earth.

**Optional DGNSS / differential processing:**

1. Obtain reference station RINEX observations from [Hong Kong SatRef](https://www.geodetic.gov.hk/), such as station **HKSC** or **HKKT**, covering your measurement period.
2. Inspect the `.obs` header and convert the requested window correctly between **GPS time** and **UTC**.
3. Supply rover `.obs`, base-station `.obs`, and nav `.nav` in RTKPOST.
4. Select **DGPS/DGNSS / Kinematic** as appropriate, and ensure base coordinates are set (e.g. from the base RINEX header).
5. Execute and compare with standalone SPP. The supplied example base data are `example/hksc_2025.obs`.

**Do not equate agreement with accuracy.** RTKPOST and the receiver can also be affected by reflected signals in the same environment.

### 5.3 Convert RINEX → Python measurement CSVs

The current course MATLAB function signature is:

```matlab
rinex2csv(obs_file, nav_file, out_dir)
```

From MATLAB with `Lab1` as the current folder:

```matlab
% Your own field measurements
rinex2csv('mydata/my.obs', 'mydata/my.nav', 'outputs/own_inputs');

% Regenerate benchmark GPS input CSVs (optional: cache is already provided)
rinex2csv('benchmark/urbannav_deep1.obs', ...
          'benchmark/urbannav_deep1.nav', ...
          'outputs/benchmark_inputs');
```

The function currently uses **GPS L1** with a default **15° elevation mask** and **15 dB-Hz signal threshold**, computes broadcast satellite position and clock plus modelled atmospheric corrections, and writes its data to `out_dir` without opening figures.

| CSV input | Contents |
|---|---|
| `pseudoranges_meas.csv` | Measured pseudorange values |
| `satellite_positions.csv` | Satellite ECEF XYZ positions (three adjacent coordinate columns per epoch in the archived input layout) |
| `satellite_clock_bias.csv` | Satellite clock corrections |
| `ionospheric_delay.csv` | Modelled ionospheric delay |
| `tropospheric_delay.csv` | Modelled tropospheric delay |
| `epochs.csv` | Actual GPS week / time-of-week of measurement epochs |
| `group_delay.csv`, `elevation_deg.csv`, `satellites.csv` | Extra conversion outputs (depending on converter mode/version) |
| `conversion_summary.txt` | Conversion summary / missing-data checks |

**Check the actual CSV layout before rewriting code.** The archived example matrices use **one column per epoch**, not one row per epoch; the `satellite_positions.csv` layout uses satellite-coordinate triplets. The final **submission CSV**, however, is **one row per solved epoch**. These are different file formats.

### 5.4 Extract receiver-reference positions from UBX

Install optional dependencies and run the GUI converter:

```bash
python -m pip install -r requirements-optional.txt
python pyubx2_csv_converter_gui.py
```

Choose your UBX input and output directory. The resulting `NAV-HPPOSECEF.csv` contains the receiver's own ECEF position estimate.

**Unit trap:** `iTOW` is **milliseconds** of GPS week; position fields are mostly in **centimetres**, plus high-precision 0.1 mm components. Combine them correctly to obtain ECEF metres, and match timestamps rather than simply matching rows. Without RTK corrections this is **not** ground truth.

---

## 6. Core theory: pseudorange and WLS-SPP

This is the model implemented by the Python solver and taught in the tutorial (pp. 8–11) and slides (SPP recap).

### 6.1 Pseudorange measurement equation

For satellite $i$:

$$
\rho_i = \|\mathbf p_i - \mathbf p\| + c\,\delta t_r - c\,\delta t_i + I_i + T_i + \epsilon_i
$$

Where:

| Symbol | Meaning |
|---|---|
| $\rho_i$ | Measured pseudorange to satellite $i$ (m) |
| $\mathbf p_i=[x_i,y_i,z_i]^T$ | Satellite position (ECEF, m) at signal transmission |
| $\mathbf p=[x,y,z]^T$ | Unknown receiver position (ECEF, m) |
| $c=299\,792\,458$ m/s | Speed of light |
| $\delta t_r$ / $\delta t_i$ | Receiver / satellite clock offsets (s) |
| $I_i$ / $T_i$ | Ionospheric / tropospheric path delays (m) |
| $\epsilon_i$ | Noise, multipath and non-line-of-sight errors (m) |

Set receiver clock bias $b=c\,\delta t_r$ (in **metres**), and apply satellite-clock and atmospheric corrections:

$$
\tilde\rho_i = \rho_i + c\,\delta t_i - I_i - T_i
               = \|\mathbf p_i - \mathbf p\| + b + \epsilon_i.
$$

The sign of the satellite clock correction matters; check units and conventions used in your CSVs.

### 6.2 The four-state GPS-only model

At a measurement epoch, solve:

$$
\mathbf x = [x,\ y,\ z,\ b]^T.
$$

Four independent unknowns require **at least four geometrically valid satellites**, but more satellites allow an overdetermined least-squares fit. Start with an initial guess $\mathbf p_0,b_0$, calculate geometric range and line of sight:

$$
r_{i,0}=\|\mathbf p_i-\mathbf p_0\|,\qquad
\mathbf e_i=\frac{\mathbf p_i-\mathbf p_0}{r_{i,0}}.
$$

Form the misclosure/residual observation and Jacobian row:

$$
y_i=\tilde\rho_i-r_{i,0}-b_0,
\qquad
\mathbf H_i=\begin{bmatrix}-e_{ix}&-e_{iy}&-e_{iz}&1\end{bmatrix}.
$$

Stack $n$ satellites as $\mathbf y\in\mathbb R^n$ and $\mathbf H\in\mathbb R^{n\times4}$. The first-order model is:

$$
\mathbf y\approx \mathbf H\,\Delta\mathbf x+\boldsymbol\epsilon.
$$

### 6.3 Least squares and weighting

**Unweighted LS** uses $\mathbf W=\mathbf I$. **Weighted LS** assigns a confidence to each observation, for example:

$$
w_i=\sin^2(\theta_i),\qquad
\mathbf W=\operatorname{diag}(w_1,\dots,w_n),
$$

where $\theta_i$ is satellite elevation. Low-elevation signals usually have higher atmospheric and multipath risks, so receive smaller weights.

The Gauss–Newton WLS update is:

$$
\widehat{\Delta\mathbf x}
=(\mathbf H^T\mathbf W\mathbf H)^{-1}\mathbf H^T\mathbf W\mathbf y,
\qquad
\mathbf x_{k+1}=\mathbf x_k+\widehat{\Delta\mathbf x}.
$$

**Implementation tip:** In numerical code, prefer `np.linalg.lstsq` or a QR/Cholesky-based solve on the weighted system over explicitly forming a matrix inverse. The mathematical expression above is the derivation, not a recommendation to use `np.linalg.inv`.

Iterate until receiver position correction is small, e.g. $\|\Delta\mathbf p\| < 10^{-3}$ m (tutorial discussion) or $10^{-4}$ m (sample AI prompt), and check for divergence, singular geometry and missing data.

### 6.4 A compact per-epoch algorithm

```text
For each epoch:
  1. Read pseudoranges, satellite ECEF positions, clocks, atmospheric delays,
     satellite IDs and observation times.
  2. Reject invalid/missing inputs; apply chosen elevation/CN0 masks.
  3. Correct pseudoranges for satellite clock, ionosphere and troposphere.
  4. Initialise receiver [x,y,z,clock_bias], typically from a coarse estimate.
  5. Repeat:
       a. Predict satellite geometric ranges.
       b. Build residual vector y and line-of-sight geometry matrix H.
       c. Build observation weights W.
       d. Solve WLS correction, update receiver state.
     until convergence (or fail safely).
  6. Compute residuals, satellite count, DOP and quality flags.
  7. Save valid ECEF result with the original GPS week and time-of-week.
  8. If unsolved, record the reason; do NOT copy the previous epoch's position.
```

### 6.5 Several constellations need several clock biases

GPS, BeiDou, Galileo and GLONASS do not share exactly the same system time. For GPS+BDS+Galileo, a straightforward state is:

$$
\mathbf x=[x,y,z,b_G,b_C,b_E]^T.
$$

Each satellite's Jacobian row has `-line_of_sight` followed by a `1` in its constellation's clock-bias column and `0` in the other clock columns. For $m$ independent constellation clocks, at least **$3+m$** suitable satellites are needed in the unconstrained model.

Practical cautions from the tutorial: **BDS time $\mathrm{BDT}=\mathrm{GPST}-14\,\mathrm s$**; GLONASS signal-frequency handling differs. The suggested first extension is **GPS + BDS + Galileo**.

### 6.6 Residuals, DOP and expected accuracy

If $\mathbf W=\mathbf I$, define the standard geometry matrix:

$$
\mathbf Q=(\mathbf H^T\mathbf H)^{-1},\qquad
\mathrm{GDOP}=\sqrt{\operatorname{tr}(\mathbf Q)}.
$$

Transform the position covariance/geometry into ENU to obtain HDOP and VDOP. If the single-measurement range-error standard deviation is approximately $\sigma_\rho$, then rough position scales are $\sigma_H\approx\mathrm{HDOP}\cdot\sigma_\rho$ and $\sigma_V\approx\mathrm{VDOP}\cdot\sigma_\rho$.

The tutorial's illustrative open-sky single-frequency UERE contributions are:

| Source | Approx. 1σ (m) |
|---|---:|
| Satellite clock after broadcast correction | 1.5 |
| Broadcast ephemeris | 2.0 |
| Ionosphere after Klobuchar | 5.0 |
| Troposphere after modelling | 0.5 |
| Open-sky multipath | 1.0 |
| Receiver noise | 0.3 |
| **Root-sum-square UERE** | **≈ 5.7** |

Example: for HDOP = 1.5 and VDOP = 2.5, rough 1σ errors are **8.6 m horizontal** and **14 m vertical**. Urban reflections/NLOS violate the simple zero-mean assumption and can produce much larger biases.

---

## 7. The tutorial's numeric worked example

The tutorial pp. 9–11 provides a synthetic five-GPS-satellite example to check the equations and units.

### 7.1 Position and receiver clock bias

Initial GPS-only state:

$$
\mathbf x_0=\begin{bmatrix}-2418000.0&5385000.0&2406000.0&0\end{bmatrix}^T\ \mathrm m.
$$

Input data (pseudoranges already adjusted for satellite clocks; $I,T$ listed separately):

| PRN | Az (°) | El (°) | Satellite X (m) | Satellite Y (m) | Satellite Z (m) | Pseudorange (m) | I (m) | T (m) | Weight |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G05 | 35 | 72 | -12279188.8 | 18509172.8 | 14562473.9 | 20431181.26 | 4.85 | 2.42 | 0.9045 |
| G13 | 140 | 48 | -18600547.8 | 18880989.3 | -1720890.7 | 21475775.35 | 5.60 | 3.09 | 0.5523 |
| G15 | 230 | 31 | 4805112.5 | 25690114.1 | -4728903.9 | 22705642.17 | 7.12 | 4.47 | 0.2653 |
| G20 | 310 | 55 | 697304.3 | 21069860.0 | 16155753.3 | 21093838.34 | 5.21 | 2.81 | 0.6710 |
| G29 | 85 | 22 | -25267228.8 | 3267032.6 | 7505148.0 | 23511370.83 | 8.94 | 6.14 | 0.1403 |

At the initial estimate the first satellite range is approximately **20,427,109.78 m**. The initial corrected observation vector is:

$$
\mathbf y_0\approx[4064.21,3742.83,3695.28,4125.01,4455.64]^T\ \mathrm m.
$$

The first weighted least-squares correction:

$$
\widehat{\Delta\mathbf x}_1
\approx[-204.776,852.702,-350.512,4501.456]^T\ \mathrm m.
$$

| Iteration | ΔX (m) | ΔY (m) | ΔZ (m) | Δbias (m) | Position correction norm (m) |
|---|---:|---:|---:|---:|---:|
| 1 | -204.776 | 852.702 | -350.512 | 4501.456 | 944.4011 |
| 2 | 0.002 | -0.010 | 0.012 | -0.017 | 0.0154 |
| 3 | ≈0 | ≈0 | ≈0 | ≈0 | ≈0 |

Converged solution:

$$
\widehat{\mathbf p}
=\begin{bmatrix}-2418204.774\\5385852.693\\2405649.499\end{bmatrix}\ \mathrm m,
\qquad \widehat b=4501.439\ \mathrm m
\quad (\delta t_r\approx15.015\ \mu\mathrm s).
$$

The example yields post-fit residuals approximately **0.87, −0.97, 1.51, −1.04 and 0.36 m**; the simulated true-position comparison is approximately **1.49 m horizontal**, **5.66 m 3D**. Geometry: GDOP **3.42**, HDOP **1.54**, VDOP **2.47**.

**Interpretation:** WLS is solving the four unknowns from more than four noisy pseudoranges. The receiver clock term is an essential unknown, not a measurement you should silently ignore.

### 7.2 Doppler extension: velocity and clock drift

For GPS L1, $f_{L1}=1575.42$ MHz and wavelength $\lambda=c/f_{L1}\approx0.190294$ m. Doppler converts to pseudorange rate:

$$
\dot\rho_i=-\lambda f_{D,i}.
$$

Given satellite velocity $\mathbf v_i$, line-of-sight $\mathbf e_i$, receiver velocity $\mathbf v$, and receiver clock drift $d$ in m/s:

$$
\dot\rho_i=(\mathbf v_i-\mathbf v)^T\mathbf e_i+d+\dot\epsilon_i,
$$

$$
y_i=\dot\rho_i-\mathbf v_i^T\mathbf e_i
=-\mathbf e_i^T\mathbf v+d+\dot\epsilon_i.
$$

This is a **linear WLS** solve using the same geometric Jacobian form as positioning; its state is $[v_x,v_y,v_z,d]^T$.

Illustrative worked-example answer:

- Receiver velocity ECEF: $[-0.624,-0.568,0.552]^T$ m/s.
- Receiver clock drift: **44.972 m/s**, equivalent to roughly **150.0 ns/s**.
- Receiver velocity ENU: **0.802 m/s East, 0.610 m/s North, −0.033 m/s Up**.
- Speed about **1.01 m/s**, heading about **52.7°**.

Doppler velocity is a useful option for time-domain smoothing or dynamic filtering; it is not a substitute for computing position from the measurement data.

---

## 8. Run the Python WLS solver on the three datasets

All commands assume your shell is inside **`AAE4203-S12627/Lab1`**.

### 8.1 Supplied historical example: **verification**, not submission

```bash
python WLSE_spp.py --reference example/NAV-HPPOSECEF.csv
python tools/check_submission.py outputs/example/G01_owndata.csv --epoch-file example/epochs.csv
```

Aim to reproduce the **186/186** historical reference. Keep these comparison statistics separate from benchmark ranking metrics: they are against the receiver reference.

### 8.2 Benchmark: fast GPS-only baseline without MATLAB

```bash
python WLSE_spp.py --mode gps \
  --input-dir benchmark/gps_csv \
  --output-dir outputs/benchmark \
  --submission G05_benchmark.csv

python tools/check_submission.py \
  outputs/benchmark/G05_benchmark.csv \
  --week 2158 \
  --epoch-file benchmark/gps_csv/epochs.csv
```

Replace `G05` with your group. This is a **starting GPS L1 baseline**, not a finished multi-constellation solution.

**Repository verification result:** **1437/1534** benchmark epochs solved, **93.6767% availability**, for the included GPS cache. **This says nothing about benchmark RMSE or leaderboard rank** because the scoring reference is not present.

### 8.3 Your own converted field data

After RTKCONV and `rinex2csv` have produced `outputs/own_inputs/`:

```bash
python WLSE_spp.py --mode gps \
  --input-dir outputs/own_inputs \
  --output-dir outputs/own \
  --submission G05_owndata.csv

python tools/check_submission.py \
  outputs/own/G05_owndata.csv \
  --epoch-file outputs/own_inputs/epochs.csv
```

Check `outputs/own/solution_details.csv`, `omitted_epochs.csv`, and `summary.json` in addition to the five-column output. Record unsolved epochs; do not generate fake coordinates to fill gaps.

### 8.4 Optional: rerun full benchmark RINEX conversion

```matlab
rinex2csv('benchmark/urbannav_deep1.obs', ...
          'benchmark/urbannav_deep1.nav', ...
          'outputs/benchmark_inputs');
```

Then change `--input-dir` to `outputs/benchmark_inputs` in the Python command. The current repository's converter is **GPS-only**. A true GPS+BDS+Galileo extension requires expanding the observation extraction, correction models and WLS clock state; changing the `--mode` flag alone does not make it multi-constellation.

---

## 9. Validate your self-collected data correctly

Because your field experiment has **no independent ground truth**, do not claim you have measured absolute accuracy. The report must test processing consistency and signal quality.

### 9.1 Required comparison 1: independent positions

Compare your Python SPP with:

1. **RTKPOST SPP** from your `.obs/.nav`.
2. **Receiver solution** extracted from `NAV-HPPOSECEF.csv`.
3. **Optional DGNSS/RTK** processing if valid base-station data are available.

Match observations by GPS epoch/timestamp, not by array index. Convert coordinate units to ECEF metres and calculate differences in local East-North-Up (ENU):

$$
\mathbf d_k
=\mathbf R_{\mathrm{ECEF}\to\mathrm{ENU}}(\varphi,\lambda)
(\widehat{\mathbf p}^{(a)}_k-\widehat{\mathbf p}^{(b)}_k).
$$

For each $c\in\{E,N,U\}$, report the mean and sample standard deviation across $K$ aligned epochs:

$$
\bar d_c=\frac{1}{K}\sum_{k=1}^{K}d_{c,k},\qquad
s_c=\sqrt{\frac{1}{K-1}\sum_{k=1}^{K}(d_{c,k}-\bar d_c)^2}.
$$

A small difference means solutions **agree**, not that either is objectively correct.

### 9.2 Required comparison 2: static-solution consistency

For a motionless antenna, evaluate:

- Mean E/N/U position and standard deviation around the mean.
- East–North scatter plot and time-series drift.
- Horizontal radius/error around the mean and its **95th percentile**.
- Number/percentage of epochs with a valid solution.

A drift/cluster that changes over time may reveal multipath or low-quality satellites even though the antenna never moved.

### 9.3 Required comparison 3: GNSS input quality

Provide and discuss:

- Satellites tracked per epoch **and per constellation**.
- Satellite elevation and sky plot.
- **C/N₀ (dB-Hz)** time series / distribution.
- Geometry: DOP, especially HDOP and VDOP.
- Post-fit pseudorange residuals and any unusually bad epochs.

Rule-of-thumb from the tutorial: approximately **>40 dB-Hz** often indicates a stronger direct signal, while **<30 dB-Hz at moderate elevation** can suggest reflections/diffraction/NLOS. These are heuristics, not conclusive classifications.

---

## 10. Improve SPP for the benchmark

Start with a verified baseline. Change **one element at a time**, measure its effect using allowed feedback, and preserve the old version for an ablation study.

| Technique | What to change | Benefit | Risk / check |
|---|---|---|---|
| Multi-constellation | Add BDS and Galileo, using separate receiver clock biases | More visible satellites; better geometry, particularly in urban canyons | Time-system conversions, ephemerides, signal ID/corrections must be correct |
| Elevation weighting | $w_i=\sin^2(\theta_i)$ or more detailed variance model | Down-weights poor low-elevation observations | Low satellites can still help geometry |
| C/N₀ weighting | Weight observations by estimated signal strength/noise variance | Lower influence of weak/possibly reflected signals | C/N₀ is not a perfect NLOS classifier |
| Elevation/C/N₀ masks | e.g. elevation **10–15°**, C/N₀ **25–30 dB-Hz** | Removes some bad signals | Too strict a mask reduces satellites and availability |
| Residual-based exclusion | Identify and reject largest normalised residual; recompute WLS | Mitigates some outliers (RAIM-like) | Risk of discarding useful signals; monitor geometry |
| Atmosphere | Correct satellite clock, ionosphere (Klobuchar) and troposphere (Saastamoinen); consider dual frequency | Removes systematic range bias | Incorrect sign/units or model can make results worse |
| Carrier smoothing | Hatch-type code/carrier combination | Less pseudorange noise | Cycle slips and long-memory bias |
| Doppler/Kalman filtering | Exploit time-series continuity | Smoother dynamic trajectory | Lag and inconsistent assumptions across moving segments |

**Version/ablation table to maintain:**

| Version | Modification | Example check | Benchmark available epochs / % | 2D RMSE | 3D RMSE | P95 | Observation |
|---|---|---|---:|---:|---:|---:|---|
| V0 | Supplied GPS-only WLS | Pass | Record | Record from leaderboard | Record | Record | Baseline |
| V1 | Add C/N₀ weights | Pass | Record | … | … | … | Explain difference |
| V2 | Add residual exclusion | Pass | Record | … | … | … | Explain difference |
| V3 | GPS+BDS+Galileo | Pass | Record | … | … | … | Explain difference |

**Do not invent RMSE values** if you have not yet received scoreboard results. The supplied package can compute a trajectory and coverage, but cannot compute benchmark scoring error without the withheld evaluation reference.

---

## 11. Benchmark CSV, upload, and ranking

### 11.1 Exact output schema

Your output must have **exactly five comma-separated columns**, with this header and order:

```csv
gps_week,gps_tow_s,x_ecef_m,y_ecef_m,z_ecef_m
2158,455346.0,-2418202.586,5385847.524,2405648.799
2158,455347.0,-2418202.174,5385847.238,2405648.952
```

The lines above are **illustrative values**, not an actual benchmark solution.

| Column | Rule |
|---|---|
| `gps_week` | Integer GPS week |
| `gps_tow_s` | GPS time of week, seconds, at least 1 decimal |
| `x_ecef_m` | Estimated receiver X in **WGS-84 ECEF metres**, three decimals |
| `y_ecef_m` | Estimated receiver Y in ECEF metres, three decimals |
| `z_ecef_m` | Estimated receiver Z in ECEF metres, three decimals |

Output **one row per solved epoch** in ascending time order, with no duplicate timestamps, no blank/NaN coordinates, **no latitude/longitude**, and **no extra columns**. Epochs that cannot be solved may be omitted but reduce availability. Preserve observation timestamps (server matches to ~**0.1 s**).

Names: `GXX_benchmark.csv` and `GXX_owndata.csv`.

### 11.2 Validate before upload

```bash
python tools/check_submission.py outputs/benchmark/G05_benchmark.csv \
  --week 2158 --epoch-file benchmark/gps_csv/epochs.csv
```

For own data, use its own `epochs.csv` and omit the fixed benchmark `--week 2158` option. The checker tests format, timestamps, finite coordinates and some plausibility checks. Passing it **does not prove accuracy** and does not guarantee online acceptance.

### 11.3 Upload and leaderboard

- The TA supplies a **Google Drive** link on Blackboard with one subfolder per group.
- Upload **both** CSVs to the correct group subfolder.
- Replacing `GXX_benchmark.csv` with a better legitimate solver output updates the evaluated submission.
- Only the latest file with the correct filename **at the deadline** counts for the final leaderboard.
- Leaderboard platform code: [PolyU-TASLAB/AAE4203_ASN_2026](https://github.com/PolyU-TASLAB/AAE4203_ASN_2026).

### 11.4 Evaluation metrics and eligibility

For each matched epoch, rotate position error relative to held-out benchmark truth into E/N/U:

$$
\mathbf e_k=\mathbf R(\varphi_k,\lambda_k)
(\widehat{\mathbf p}_k-\mathbf p_k^{\mathrm{gt}}).
$$

The teaching team computes:

$$
\mathrm{RMSE}_{2D}=\sqrt{\frac{1}{N}\sum_{k=1}^{N}(e_{E,k}^2+e_{N,k}^2)},
$$

$$
\mathrm{RMSE}_{3D}=\sqrt{\frac{1}{N}\sum_{k=1}^{N}(e_{E,k}^2+e_{N,k}^2+e_{U,k}^2)},
$$

$$
\mathrm{Availability}=100\frac{N}{N_{\mathrm{gt}}}\%,
\qquad P_{95}=\operatorname{percentile}_{95}\!\left(\sqrt{e_E^2+e_N^2}\right).
$$

**Ranking rules:**

1. **Availability must be ≥90%** or the submission is unranked.
2. Smallest **2D RMSE** ranks highest.
3. Ties are broken using **3D RMSE**.
4. The leaderboard also reports 2D 95th-percentile error and availability.
5. Submitted trajectories must be independently reproducible from the observation data using your repository; the teaching team may rerun any group's code.

---

## 12. Required report guideline (not the report itself)

The formal template is [`PolyU_AAE4203_Lab_report_template.docx`](https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/PolyU_AAE4203_Lab_report_template.docx). Limit: **10 pages excluding the cover**, and at most **2 pages of code listings** in the report. Keep complete code in GitHub.

| Section | What you need to include |
|---|---|
| **1. Data collection** | Hardware/software setup, collection site and sky photos, date/time, environment, static antenna procedure |
| **2. Raw data analysis** | Satellites per constellation, C/N₀ plots, elevation/sky plot, DOP and signal-quality discussion |
| **3. SPP algorithm** | Pseudorange measurement model, satellite/atmosphere corrections, linearisation, weighted least-squares and Python algorithm |
| **4. Own-data validation** | Your SPP vs RTKPOST vs receiver reference, time-aligned ENU differences, component-wise mean/std, East–North scatter and static consistency, input checks; explicitly state no true ground truth |
| **5. Benchmark results** | Baseline and each improvement, reasons, ablation table, **final 2D/3D RMSE, P95, availability and rank**, discussion of urban multipath/NLOS |
| **6. AI-use statement** | AI tools, specific tasks, main prompts in an appendix, verification steps, what humans checked/understood |

### 12.1 AI use: permitted, but with conditions

- AI assistants may help write, explain and debug the Python algorithm.
- Verify AI-generated code against the **supplied example dataset** before using it for the benchmark.
- Every group member must be able to explain the algorithm and submitted code.
- State which tools you used, for which tasks, and include key prompts in the report appendix.
- The benchmark trajectory must result from **your own code and provided observations**. Do not submit another group's solution, a receiver solution, a published ground truth, or other precomputed positions.
- Do not send other groups' information or personal data to AI services.

### 12.2 Reproducible GitHub package

At minimum, give the reader enough to rerun both trajectory outputs:

```text
YourLabRepository/
├── README.md                  # requirements, versions, commands
├── data/                      # self-collected UBX, OBS/NAV and relevant inputs
├── src/                       # your solver and conversion/analysis code
├── results/                   # final GXX_owndata and GXX_benchmark CSVs
├── figures/                   # plots used in report
└── methods.md                 # algorithm choices, configuration, validation
```

The structure is a **suggestion**; reproduce the official filenames and outputs. Avoid committing other groups' private information or exposing nonpublic material.

---

## 13. Checklist: do these in order

### Before acquisition

- [ ] Clone `AAE4203-S12627/Lab1`, read the course `Readme.md`, and install dependencies.
- [ ] Run provided `WLSE_spp.py` historical example; reproduce **186 epochs** and the known receiver-reference differences.
- [ ] Know your group code, collection batch, kit and partner group.
- [ ] Have u-center, RTKLIB, and a laptop ready; test COM connection.

### Before leaving the field

- [ ] Antenna kept static for 15–20 minutes near Block X.
- [ ] Valid UBX log recorded, closed, and copied to separate storage.
- [ ] Site/equipment/sky photos saved, and time, weather, environment noted.
- [ ] Receiver kit fully returned or handed over.

### Before the session ends

- [ ] Convert UBX to `.obs`/`.nav` with RTKCONV.
- [ ] Obtain RTKPOST SPP solution; optionally differential comparison.
- [ ] Generate own-data measurement CSVs; extract receiver `NAV-HPPOSECEF` reference.
- [ ] Run your Python own-data solver and compare E/N/U differences.
- [ ] Check static scatter, satellite/C/N₀/elevation quality, residuals and DOP.
- [ ] Start benchmark solver, test first on the example, and record all improvements.
- [ ] Run CSV checker and upload both named CSVs to the appropriate group folder.

### Before final deadline

- [ ] Keep final benchmark availability **≥90%** for ranking.
- [ ] Final uploaded files meet five-column schema, correct timestamps, correct group naming.
- [ ] GitHub code and README reproduce both submitted CSVs.
- [ ] Benchmark ablation and official ranking results recorded without inventing values.
- [ ] PDF report ≤10 pages excluding cover, with full required analysis and AI-use statement.
- [ ] Blackboard submission and group Drive uploads complete before the official deadlines.

---

## 14. Common mistakes and fixes

| Symptom / mistake | Likely cause | What to check |
|---|---|---|
| Python estimates a nonsense position | Wrong ECEF units, incorrect clock sign, bad satellite position or initialisation | ECEF should be millions of metres; satellite pseudorange ~20–25 million m; clock correction sign |
| `NAV-HPPOSECEF` comparison differs hugely | Position in cm vs m, time `iTOW` in ms vs s | Convert fields correctly; align by GPS epoch |
| Too few satellites or unsolved epochs | Too strict elevation/C/N₀ masks, incomplete observation log or missing corrections | `omitted_epochs.csv`, C/N₀, masks, CSV validity |
| Example gives 113/186 rather than 186/186 | Reconverted new GPS-only inputs instead of historical example cache | Use the exact historical command for regression; don't mix modes |
| Cannot load `gt` in MATLAB | `matRTKLIB/` missing/not on path | Keep next to `rinex2csv.m`, test toolbox and MEX compatibility |
| Trying `run('rinex2csv.m')` | Old script syntax vs current function entry point | Call `rinex2csv(obs,nav,out_dir)` |
| RTKPOST has no solution | Incorrect OBS/NAV selection, nonoverlapping station epochs, receiver format or time | Check headers, satellite IDs, time systems and settings |
| Better filtering gives fewer solutions | Aggressive masking rejects too many satellites | Track both **RMSE and availability**; minimum ranked availability is 90% |
| Format checker succeeds but rank is poor | Checker validates format, not ground-truth accuracy | Improve algorithm; examine official leaderboard metrics |
| Latitude/longitude or extra columns in CSV | Wrong export format | Submit **WGS-84 ECEF XYZ metres**, exact header and decimals |
| UrbanNav reference used to optimise results | Disallowed leakage | Use provided observations and official leaderboard; never reference published ground truth |

---

## 15. What the provided code does, and what you must add

| Component | Already provided by course repo? | Your remaining work |
|---|---|---|
| Static UBX recording | Hardware/tutorial only | **Collect a new group log** |
| UBX → OBS/NAV | RTKCONV program and instructions | Convert/check your data |
| OBS/NAV → GPS CSVs | `rinex2csv.m`, plus benchmark GPS cache | Apply to your data and verify outputs |
| GPS L1 WLS SPP | `WLSE_spp.py` | Understand, validate and document; improve as desired |
| Historical example regression | Complete 186-epoch files and receiver reference | Reproduce before code changes |
| Receiver CSV extraction | `pyubx2_csv_converter_gui.py` | Convert and align your data |
| RTKPOST SPP / DGNSS | External RTKLIB utility | Configure and generate independent comparisons |
| Multi-constellation SPP | **Not implemented in supplied baseline** | Add constellation extraction, clock terms, time handling and corrections |
| C/N₀ weighting, outlier rejection, advanced filtering | Suggested techniques, not complete default pipeline | Experiment, explain, retain ablation evidence |
| Own-data validation and plots | Guidance, some archived example figures | **Produce your own plots and comparisons** |
| Benchmark five-column CSV | Solver can generate it | Improve/check/upload valid trajectory |
| Lab report and GitHub handover | Template and requirements | **Write the analysis and demonstrate reproducibility** |

### One-sentence summary

**Collect raw satellite observations → derive satellite-related measurements/corrections → estimate receiver position and clock bias by iterative weighted least squares at every epoch → validate on your own static data → improve the algorithm on UrbanNav → submit reproducible ECEF trajectories and report the evidence.**

---

## 16. Original materials and reference links

| Resource | Link / location |
|---|---|
| Full lab folder | https://github.com/weisongwen/AAE4203-S12627/tree/main/Lab1 |
| Laboratory tutorial | `Lab1/AAE4203_26_27_S1_Lab_Tutorial.pdf` |
| Week 9 slide deck | `Lab1/AAE4203_Week9_GNSS_Lab_Slides.pdf` |
| Script and tests | `Lab1/WLSE_spp.py`, `Lab1/tools/check_submission.py`, `Lab1/tools/verify_package.py` |
| Example files | https://github.com/weisongwen/AAE4203-S12627/tree/main/Lab1/example |
| Benchmark files | https://github.com/weisongwen/AAE4203-S12627/tree/main/Lab1/benchmark |
| Extended running guide | https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/docs/RUNNING.md |
| Verification notes | https://github.com/weisongwen/AAE4203-S12627/blob/main/Lab1/docs/VERIFICATION.md |
| RTKLIB | https://github.com/rtklibexplorer/RTKLIB |
| MatRTKLIB | https://github.com/taroz/MatRTKLIB |
| pyubx2 | https://github.com/semuconsulting/pyubx2 |
| HK SatRef | https://www.geodetic.gov.hk/ |
| Leaderboard source | https://github.com/PolyU-TASLAB/AAE4203_ASN_2026 |

**Cross-references to source PDF figures:** Tutorial pp. 12–16 and slides pp. 15–17: receiver and u-center screenshots; tutorial pp. 16–22 and slides pp. 20–24: RTKCONV/RTKPOST and CSV converter; tutorial pp. 9–11: WLS/Doppler worked example; tutorial pp. 26–28 and slides' Block X example section: historical results; tutorial pp. 28–29 and slides' benchmark section: CSV format/ranking. This Markdown records their instructions and interpretations; decorative screenshots are not embedded.

**Compiled from:** the two uploaded AAE4203 lab PDFs and the course GitHub `Lab1` documentation, checked 30 October 2026.
