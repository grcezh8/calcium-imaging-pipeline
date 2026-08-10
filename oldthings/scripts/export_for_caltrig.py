# scripts/03_export_for_caltrig.py
#
# PURPOSE: CalTrig's GUI expects data in a specific xarray/zarr format.
#          This script takes Minian's output and formats it correctly
#          so CalTrig can open it without errors.
#
# WHAT CALTRIG EXPECTS:
#   A zarr store containing xarray DataArrays with these exact dimensions:
#   - A: spatial footprints [unit_id × height × width]
#   - C: calcium traces     [unit_id × frame]
#   - S: spike estimates    [unit_id × frame]
#   - timestamps attached as coordinate metadata
#
# Run: python scripts/03_export_for_caltrig.py --mouse mouse_01 --session session_day1

import os
import sys
import argparse
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oldthings.utils.config_loader import load_config

cfg = load_config()

parser = argparse.ArgumentParser()
parser.add_argument('--mouse',   required=True)
parser.add_argument('--session', required=True)
args = parser.parse_args()

MOUSE_ID   = args.mouse
SESSION    = args.session
OUTPUT_DIR = cfg['output_dir']
DATA_DIR   = cfg['data_dir']
FRAME_RATE = cfg['minian']['frame_rate']

MINIAN_DIR = cfg['minian_dir']
sys.path.insert(0, MINIAN_DIR)
from minian.utilities import open_minian, save_minian

print(f'=== Exporting for CalTrig: {MOUSE_ID} / {SESSION} ===')

# ── Load Minian output ────────────────────────────────────────────────────────
minian_path = os.path.join(OUTPUT_DIR, MOUSE_ID, SESSION, 'minian')
print(f'Loading Minian output from: {minian_path}')

ds = open_minian(minian_path)

A = ds['A']   # spatial footprints [unit_id × height × width]
C = ds['C']   # calcium traces     [unit_id × frame]
S = ds['S']   # spike estimates    [unit_id × frame]

print(f'  Neurons: {A.sizes["unit_id"]}')
print(f'  Frames:  {C.sizes["frame"]}')

# ── Load timestamps ───────────────────────────────────────────────────────────
ts_path = os.path.join(DATA_DIR, MOUSE_ID, SESSION, 'timestamps_with_frames.csv')

if not os.path.exists(ts_path):
    print(f'⚠️  timestamps_with_frames.csv not found at {ts_path}')
    print('   Run 00_prepare_timestamps.py first.')
    print('   Proceeding without timestamps — you can add them in CalTrig manually.')
    timestamps_df = None
else:
    timestamps_df = pd.read_csv(ts_path)
    print(f'  Loaded {len(timestamps_df)} stimulus events')
    print(f'  Stimuli: {timestamps_df["stimulus_name"].unique()}')

# ── Add time coordinate to traces ─────────────────────────────────────────────
# Convert frame numbers to seconds — CalTrig uses seconds for display
n_frames = C.sizes['frame']
time_seconds = np.arange(n_frames) / FRAME_RATE

# Add 'time' as a coordinate on the frame dimension
C = C.assign_coords(time=('frame', time_seconds))
S = S.assign_coords(time=('frame', time_seconds))

# ── Attach stimulus events as metadata ────────────────────────────────────────
# CalTrig can display stimulus markers on the trace viewer
# We encode stimulus events as attributes on the dataset
if timestamps_df is not None:
    
    # Group events by stimulus name
    # Store as a dict: {'odor_A': [frame1, frame2, ...], 'food': [frame1, ...]}
    stimulus_events = {}
    for stim_name, group in timestamps_df.groupby('stimulus_name'):
        stimulus_events[stim_name] = group['onset_calcium_frame'].tolist()
    
    # Attach as dataset attributes (CalTrig reads these)
    C.attrs['stimulus_events']  = str(stimulus_events)   # stored as string in zarr
    C.attrs['stimulus_names']   = list(stimulus_events.keys())
    C.attrs['frame_rate']       = FRAME_RATE
    C.attrs['mouse_id']         = MOUSE_ID
    C.attrs['session']          = SESSION

# ── Save in CalTrig-compatible format ─────────────────────────────────────────
caltrig_export_dir = os.path.join(OUTPUT_DIR, MOUSE_ID, SESSION, 'caltrig_input')
os.makedirs(caltrig_export_dir, exist_ok=True)

# Save each component as a separate zarr array
# CalTrig expects them at these exact names
A.to_zarr(os.path.join(caltrig_export_dir, 'A.zarr'), mode='w')
C.to_zarr(os.path.join(caltrig_export_dir, 'C.zarr'), mode='w')
S.to_zarr(os.path.join(caltrig_export_dir, 'S.zarr'), mode='w')

# Also save a plain CSV of traces for easy inspection outside CalTrig
C_df = C.to_dataframe(name='dff').reset_index()
C_df.to_csv(os.path.join(caltrig_export_dir, 'traces.csv'), index=False)

print(f'\nExport complete. Files saved to: {caltrig_export_dir}')
print(f'  A.zarr — spatial footprints')
print(f'  C.zarr — calcium traces with time coordinate')
print(f'  S.zarr — spike estimates')
print(f'  traces.csv — plain CSV version for inspection')
print(f'\nNEXT: Open CalTrig GUI and load this folder.')
print(f'  cd {cfg["caltrig_dir"]}')
print(f'  conda activate caltrig   (or minian if you installed CalTrig there)')
print(f'  python main.py')