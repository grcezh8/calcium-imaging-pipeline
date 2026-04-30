# scripts/02_register_sessions.py
#
# PURPOSE: Match the SAME neurons across different recording sessions.
#
#          After running Minian on each session separately, you have
#          neuron lists for day 1, day 2, day 3 — but they don't know
#          about each other. This script figures out:
#          "Neuron #5 from day 1 is the same cell as neuron #12 from day 2"
#
#          It does this using Minian's built-in spatial registration,
#          which compares the shape and location of each neuron's footprint.
#
# INPUT:  minian/ output folders from each session (from 01_run_minian.py)
# OUTPUT: registered_neurons.csv — the identity table across sessions
#         registered/ folder with aligned xarray datasets
#
# Run: python scripts/02_register_sessions.py --mouse mouse_01

import os
import sys
import argparse
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config

cfg        = load_config()
MINIAN_DIR = cfg['minian_dir']
sys.path.insert(0, MINIAN_DIR)

from minian.utilities import open_minian, save_minian
from minian.cross_registration import (
    group_by_session, calculate_centroids,
    calculate_mapping, resolve_mapping
)

parser = argparse.ArgumentParser()
parser.add_argument('--mouse', required=True, help='Mouse ID, e.g. mouse_01')
args = parser.parse_args()

MOUSE_ID    = args.mouse
DATA_DIR    = cfg['data_dir']
OUTPUT_DIR  = cfg['output_dir']
N_SESSIONS  = cfg['experiment']['sessions_per_mouse']
SESSIONS    = [f'session_day{i+1}' for i in range(N_SESSIONS)]

print(f'=== Cross-session registration: {MOUSE_ID} ===')

# ── Load spatial footprints from each session ─────────────────────────────────
# We only need A (spatial footprints) for registration
# The shape and position of each neuron is what gets compared
print('Loading spatial footprints...')

minian_datasets = {}
for session in SESSIONS:
    minian_dir = os.path.join(OUTPUT_DIR, MOUSE_ID, session, 'minian')
    
    if not os.path.exists(minian_dir):
        print(f'  ⚠️  Minian output not found for {session} — skipping')
        print(f'  Expected at: {minian_dir}')
        print(f'  Run 01_run_minian.py for this session first.')
        continue
    
    ds = open_minian(minian_dir)
    minian_datasets[session] = ds
    n_neurons = ds['A'].sizes['unit_id']
    print(f'  {session}: {n_neurons} neurons')

if len(minian_datasets) < 2:
    raise RuntimeError('Need at least 2 sessions to register. Run Minian on more sessions first.')

# ── Calculate centroids ───────────────────────────────────────────────────────
# A "centroid" is the center-of-mass of each neuron's spatial footprint
# CellReg and Minian both use centroid proximity as the primary matching criterion
print('\nCalculating neuron centroids...')

centroids = {}
for session, ds in minian_datasets.items():
    A = ds['A']
    # calculate_centroids returns [unit_id × (height, width)] coordinates
    centroids[session] = calculate_centroids(A, ds.coords)
    print(f'  {session}: centroids calculated for {len(centroids[session])} neurons')

# ── Calculate cross-session mapping ──────────────────────────────────────────
# For each pair of sessions, find which neurons are the "same"
# based on how close their centroids are and how similar their shapes are
print('\nCalculating cross-session neuron mapping...')

# calculate_mapping compares all sessions against each other
# max_distance: neurons must be within this many pixels to be considered a match
max_distance = 5   # pixels — increase if your scope shifts a lot between sessions

mappings = calculate_mapping(
    centroids,
    max_distance=max_distance
)

# resolve_mapping turns pairwise mappings into a unified identity table
# This is equivalent to CellReg's cell_to_index_map
assignments = resolve_mapping(mappings)

# ── assignments structure ─────────────────────────────────────────────────────
# assignments is a DataFrame where:
#   rows    = global neuron IDs (unique neurons across all sessions)
#   columns = sessions
#   values  = local unit_id in that session (NaN = neuron absent that day)
#
# Example:
#   session_day1  session_day2  session_day3
#   5             3             NaN          ← neuron present in day1, day2, absent day3
#   2             1             4            ← neuron present in ALL sessions
#   NaN           7             6            ← absent in day1

print(f'\nRegistration results:')
print(f'  Total global neurons: {len(assignments)}')

for session in SESSIONS:
    if session in assignments.columns:
        n_found = assignments[session].notna().sum()
        print(f'  {session}: {n_found} neurons matched')

n_all_sessions = assignments.notna().all(axis=1).sum()
print(f'  Neurons present in ALL sessions: {n_all_sessions}')

# ── Save registration output ──────────────────────────────────────────────────
reg_dir = os.path.join(OUTPUT_DIR, MOUSE_ID, 'registered')
os.makedirs(reg_dir, exist_ok=True)

assignments_path = os.path.join(reg_dir, 'registered_neurons.csv')
assignments.to_csv(assignments_path)
print(f'\nSaved registration table: {assignments_path}')

# Also save the combined traces for registered neurons
# This creates one dataset with traces aligned across sessions
print('Saving aligned traces...')

for session in SESSIONS:
    if session not in minian_datasets:
        continue
    
    ds = minian_datasets[session]
    
    # Get global IDs present in this session
    session_assignments = assignments[session].dropna()
    
    # Select and rename traces to use global neuron IDs
    # so downstream analysis can directly compare neuron X across days
    C_session = ds['C'].sel(unit_id=session_assignments.values.astype(int))
    C_session = C_session.assign_coords(
        unit_id=session_assignments.index.values  # use global IDs
    )
    
    save_path = os.path.join(reg_dir, f'{session}_registered_C.zarr')
    C_session.to_zarr(save_path, mode='w')
    print(f'  Saved: {save_path}')

print(f'\n=== Registration complete ===')
print(f'NEXT: Run 03_export_for_caltrig.py to prepare data for the CalTrig GUI')