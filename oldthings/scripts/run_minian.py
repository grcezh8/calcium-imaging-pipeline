# scripts/01_run_minian.py
#
# PURPOSE: Run Minian's full pipeline on ONE session of ONE mouse.
#          This is the heavy computation step — run it on the Windows machine.
#
# WHAT MINIAN DOES:
#   1. Loads the calcium imaging AVI (no conversion needed)
#   2. Motion correction — stabilizes frames so neurons don't drift
#   3. Background removal — separates neuron signal from non-specific fluorescence
#   4. CNMF-E — finds individual neurons (spatial footprints + activity traces)
#   5. Quality control — discards noise components
#   6. Saves everything as .zarr files (xarray format, native CalTrig input)
#
# HOW TO RUN:
#   python scripts/01_run_minian.py --mouse mouse_01 --session session_day1
#
# Run for each session separately. Each takes 30min–2hrs depending on video size.

import os
import sys
import argparse
import numpy as np

# Tell Python where to find Minian and our utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oldthings.utils.config_loader import load_config

cfg        = load_config()
MINIAN_DIR = cfg['minian_dir']
sys.path.insert(0, MINIAN_DIR)    # add Minian to path so we can import it

# Now import Minian
from minian.utilities import TaskAnnotation, get_optimal_chk, load_videos, open_minian, save_minian
from minian.preprocessing import denoise, remove_background
from minian.motion_correction import apply_transform, estimate_motion
from minian.initialization import seeds_init, pnr_refine, ks_refine, initA, initC
from minian.cnmf import compute_trace, get_noise_fft, update_spatial, update_temporal, update_background, compute_AtC
import dask
from dask.distributed import Client, LocalCluster

# ── Argument parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--mouse',   required=True, help='Mouse ID, e.g. mouse_01')
parser.add_argument('--session', required=True, help='Session name, e.g. session_day1')
args = parser.parse_args()

MOUSE_ID   = args.mouse
SESSION    = args.session
DATA_DIR   = cfg['data_dir']
OUTPUT_DIR = cfg['output_dir']

# ── Paths ─────────────────────────────────────────────────────────────────────
session_dir = os.path.join(DATA_DIR, MOUSE_ID, SESSION)
calcium_avi = os.path.join(session_dir, f'calcium_{SESSION.split("_")[-1]}.avi')
minian_output_dir = os.path.join(OUTPUT_DIR, MOUSE_ID, SESSION, 'minian')

os.makedirs(minian_output_dir, exist_ok=True)

print(f'=== Running Minian ===')
print(f'Mouse:   {MOUSE_ID}')
print(f'Session: {SESSION}')
print(f'Input:   {calcium_avi}')
print(f'Output:  {minian_output_dir}')

if not os.path.exists(calcium_avi):
    raise FileNotFoundError(
        f'Calcium video not found: {calcium_avi}\n'
        'Check your data folder structure and local_config.yaml'
    )

# ── Parameters (from params.yaml) ─────────────────────────────────────────────
NEURON_DIAMETER = cfg['minian']['neuron_diameter']
FRAME_RATE      = cfg['minian']['frame_rate']
MAX_SHIFT       = cfg['minian']['max_shift']

# ── Start Dask cluster ────────────────────────────────────────────────────────
# Dask enables parallel processing across your CPU cores.
# Adjust n_workers based on your Windows machine's CPU count.
# Rule of thumb: use (total CPU cores - 2) so the machine stays responsive.
cluster = LocalCluster(
    n_workers=6,        # adjust to your machine — check Task Manager for core count
    threads_per_worker=1,
    memory_limit='8GB'  # per worker — adjust based on total RAM / n_workers
)
client = Client(cluster)
print(f'Dask dashboard: {client.dashboard_link}')

# ── Step 1: Load video ────────────────────────────────────────────────────────
# Minian's load_videos reads AVI directly — no conversion needed
print('\nStep 1: Loading video...')
varr = load_videos(
    session_dir,
    pattern=f'calcium_{SESSION.split("_")[-1]}.avi',
    dtype=np.uint8
)
print(f'Video shape: {varr.sizes}')  # should show frames, height, width

# Save raw for reference
varr = save_minian(varr.rename('varr'), dpath=minian_output_dir, overwrite=True)

# ── Step 2: Motion Correction ─────────────────────────────────────────────────
# Aligns every frame to a reference frame so neurons don't shift around
print('\nStep 2: Motion correction...')

# Estimate how much each frame needs to be shifted
motion = estimate_motion(varr, dim='frame')
motion = save_minian(motion.rename('motion'), dpath=minian_output_dir, overwrite=True)

# Apply the shifts
varr_mc = apply_transform(varr, motion, fill=0)
varr_mc = save_minian(varr_mc.rename('varr_mc'), dpath=minian_output_dir, overwrite=True)

print(f'Max motion shift: {float(motion.max()):.2f} pixels')
if float(motion.max()) > MAX_SHIFT:
    print(f'⚠️  WARNING: motion exceeded max_shift ({MAX_SHIFT}px) — check video quality')

# ── Step 3: Preprocessing ─────────────────────────────────────────────────────
print('\nStep 3: Preprocessing (denoise + background removal)...')

# Denoise: reduce pixel-level noise while preserving neuron signals
varr_ref = varr_mc.sel(frame=slice(0, 500)).mean('frame')  # reference image
varr_dn  = denoise(varr_mc, method='median', ksize=7)

# Remove background: slow, large-scale fluorescence that isn't neurons
varr_bg  = remove_background(varr_dn, method='tophat', wnd=NEURON_DIAMETER * 3)
varr_bg  = save_minian(varr_bg.rename('varr_bg'), dpath=minian_output_dir, overwrite=True)

# ── Step 4: Find neurons (CNMF-E) ─────────────────────────────────────────────
print('\nStep 4: Finding neurons (CNMF-E)...')

# Seed initialization: find candidate neuron locations
print('  Finding candidate neuron seeds...')
seeds = seeds_init(
    varr_bg,
    wnd_size=NEURON_DIAMETER * 4,
    method='rolling',
    stp_size=NEURON_DIAMETER,
    nchunk=100
)

# Refine seeds by peak-to-noise ratio
print('  Refining by peak-to-noise ratio...')
seeds, pnr, gmm = pnr_refine(varr_bg, seeds, noise_freq=0.06)

# Refine seeds by Kolmogorov-Smirnov test (removes non-calcium-like signals)
print('  Refining by KS test...')
seeds = ks_refine(varr_bg, seeds, sig=0.05)

# Keep only seeds that passed both refinements
seeds_final = seeds[seeds['mask_pnr'] & seeds['mask_ks']].reset_index(drop=True)
print(f'  Seeds remaining after refinement: {len(seeds_final)}')

# Initialize spatial footprints (A) from seeds
print('  Initializing spatial footprints...')
A_init = initA(varr_bg, seeds_final[['height', 'width', 'seeds']], wnd=NEURON_DIAMETER * 2)
A_init = save_minian(A_init.rename('A_init'), dpath=minian_output_dir, overwrite=True)

# Initialize temporal traces (C) from footprints
print('  Initializing temporal traces...')
C_init = initC(varr_bg, A_init)
C_init = save_minian(C_init.rename('C_init'), dpath=minian_output_dir, overwrite=True)

# ── Step 5: CNMF-E optimization ───────────────────────────────────────────────
# Iteratively refine spatial and temporal components
print('\nStep 5: Optimizing components (this is the slowest step)...')

# This loop runs a few iterations of spatial + temporal updates
# More iterations = better results but slower
for iteration in range(2):
    print(f'  Iteration {iteration + 1}/2...')
    
    # Update spatial footprints
    A = update_spatial(
        varr_bg, A_init, C_init,
        sn_spatial=None,
        dl_wnd=NEURON_DIAMETER,
        sparse_penal=0.5
    )
    
    # Update temporal traces
    C, S, B_YA, c0_YA, g, sn_temp = update_temporal(
        varr_bg, A, jac_thres=0.1,
        sparse_penal=1, p=1,
        add_lag=20, noise_freq=0.06
    )
    
    A_init = A
    C_init = C

# ── Step 6: Save final outputs ────────────────────────────────────────────────
print('\nStep 6: Saving results...')

# A = spatial footprints [unit_id × height × width]
# C = calcium traces     [unit_id × frame]
# S = spike estimates    [unit_id × frame]
A = save_minian(A.rename('A'),   dpath=minian_output_dir, overwrite=True)
C = save_minian(C.rename('C'),   dpath=minian_output_dir, overwrite=True)
S = save_minian(S.rename('S'),   dpath=minian_output_dir, overwrite=True)

print(f'\n=== Minian complete ===')
print(f'Neurons found: {A.sizes["unit_id"]}')
print(f'Output saved to: {minian_output_dir}')
print(f'NEXT: Run this script for other sessions, then run 02_register_sessions.py')

client.close()
cluster.close()
