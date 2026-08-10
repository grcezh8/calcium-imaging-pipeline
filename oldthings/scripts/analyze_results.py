# scripts/04_analyze_results.py
#
# PURPOSE: After you've used the CalTrig GUI to verify neurons and
#          detect transients, load CalTrig's output and produce:
#          - Per-neuron response curves for each stimulus
#          - A summary table: which neurons responded to which stimuli
#          - Cross-session comparison: does the response change across days?
#
# This answers the main scientific question:
#   "Which neurons respond to which stimuli, and does that change over time?"
#
# Run: python scripts/04_analyze_results.py --mouse mouse_01

import os
import sys
import argparse
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oldthings.utils.config_loader import load_config

cfg = load_config()

parser = argparse.ArgumentParser()
parser.add_argument('--mouse', required=True)
args = parser.parse_args()

MOUSE_ID    = args.mouse
OUTPUT_DIR  = cfg['output_dir']
RESULTS_DIR = 'results'
FRAME_RATE  = cfg['minian']['frame_rate']
SESSIONS    = [f'session_day{i+1}' for i in range(cfg['experiment']['sessions_per_mouse'])]

# Analysis window (in seconds, converted to frames)
PRE_SEC  = cfg['analysis']['window_pre_seconds']
POST_SEC = cfg['analysis']['window_post_seconds']
PRE_FR   = int(PRE_SEC  * FRAME_RATE)
POST_FR  = int(POST_SEC * FRAME_RATE)

os.makedirs(f'{RESULTS_DIR}/plots/{MOUSE_ID}', exist_ok=True)
os.makedirs(f'{RESULTS_DIR}/tables',            exist_ok=True)


def compute_event_triggered_average(trace, event_frames, pre_fr, post_fr):
    """
    For a single neuron trace, compute the average response
    around each stimulus event.
    
    trace:        1D numpy array [n_frames]
    event_frames: list of frame indices when stimulus occurred
    
    Returns:
        eta:  average response [pre_fr + post_fr] frames
        sem:  standard error  [pre_fr + post_fr] frames
        n:    number of valid events included
    """
    snippets = []
    for ef in event_frames:
        start = ef - pre_fr
        end   = ef + post_fr
        # Skip events too close to recording edges
        if start >= 0 and end <= len(trace):
            snippets.append(trace[start:end])
    
    if len(snippets) == 0:
        return None, None, 0
    
    snippets = np.array(snippets)   # [n_events × window_length]
    eta = np.mean(snippets, axis=0)
    sem = np.std(snippets, axis=0) / np.sqrt(len(snippets))
    
    return eta, sem, len(snippets)


def is_significant_response(eta, pre_fr, zscore_thresh=2.0):
    """
    Test whether a neuron's event-triggered average shows a real response.
    
    Method: compare mean activity in the post-stimulus window
    to the baseline (pre-stimulus) window, in units of baseline std.
    
    Returns True if the response exceeds zscore_thresh standard deviations
    above baseline.
    """
    if eta is None:
        return False
    
    baseline     = eta[:pre_fr]
    post_stim    = eta[pre_fr:]
    baseline_mean = np.mean(baseline)
    baseline_std  = np.std(baseline)
    
    if baseline_std < 1e-6:
        return False
    
    # Peak z-score in the post-stimulus window
    peak_zscore = (np.max(post_stim) - baseline_mean) / baseline_std
    
    return peak_zscore > zscore_thresh


# ── Load registered neuron assignments ────────────────────────────────────────
reg_path = os.path.join(OUTPUT_DIR, MOUSE_ID, 'registered', 'registered_neurons.csv')
if not os.path.exists(reg_path):
    raise FileNotFoundError(
        f'Registration table not found: {reg_path}\n'
        'Run 02_register_sessions.py first.'
    )

assignments = pd.read_csv(reg_path, index_col=0)
global_ids  = assignments.index.values
print(f'Loaded {len(global_ids)} global neurons for {MOUSE_ID}')

# ── Main analysis loop ────────────────────────────────────────────────────────
all_results = []

for session in SESSIONS:
    print(f'\nProcessing {session}...')
    
    # Load CalTrig-exported traces for this session
    caltrig_dir = os.path.join(OUTPUT_DIR, MOUSE_ID, session, 'caltrig_input')
    C_path = os.path.join(caltrig_dir, 'C.zarr')
    
    if not os.path.exists(C_path):
        print(f'  Skipping — no CalTrig export found. Run 03_export_for_caltrig.py')
        continue
    
    C_da = xr.open_zarr(C_path)['C']    # DataArray [unit_id × frame]
    
    # Load timestamps
    ts_path = os.path.join(
        cfg['data_dir'], MOUSE_ID, session, 'timestamps_with_frames.csv'
    )
    if not os.path.exists(ts_path):
        print(f'  Skipping — no timestamps found')
        continue
    
    timestamps = pd.read_csv(ts_path)
    stimuli = timestamps['stimulus_name'].unique()
    
    # Get local unit IDs for this session (from registration table)
    if session not in assignments.columns:
        print(f'  Session not in registration table — skipping')
        continue
    
    session_col = assignments[session]
    
    for global_id in global_ids:
        local_id = session_col.loc[global_id]
        
        # NaN means this neuron wasn't detected in this session
        if pd.isna(local_id):
            continue
        
        local_id = int(local_id)
        
        # Get this neuron's trace
        if local_id not in C_da.coords['unit_id'].values:
            continue
        
        trace = C_da.sel(unit_id=local_id).values   # 1D numpy array
        
        for stimulus in stimuli:
            event_frames = timestamps[
                timestamps['stimulus_name'] == stimulus
            ]['onset_calcium_frame'].values
            
            eta, sem, n_events = compute_event_triggered_average(
                trace, event_frames, PRE_FR, POST_FR
            )
            
            if eta is None:
                continue
            
            significant = is_significant_response(
                eta, PRE_FR,
                zscore_thresh=cfg['caltrig']['zscore_threshold']
            )
            
            # Mean response in post-stimulus window
            mean_post = float(np.mean(eta[PRE_FR:]))
            peak_post = float(np.max(eta[PRE_FR:]))
            
            all_results.append({
                'mouse_id':       MOUSE_ID,
                'global_neuron':  global_id,
                'session':        session,
                'stimulus':       stimulus,
                'n_events':       n_events,
                'mean_response':  mean_post,
                'peak_response':  peak_post,
                'significant':    significant,
            })

# ── Save results table ────────────────────────────────────────────────────────
results_df = pd.DataFrame(all_results)
table_path = f'{RESULTS_DIR}/tables/{MOUSE_ID}_results.csv'
results_df.to_csv(table_path, index=False)
print(f'\nSaved results table: {table_path}')
print(results_df.groupby(['stimulus', 'session'])['significant'].sum().to_string())

# ── Plot: Which neurons respond to which stimuli ───────────────────────────────
# Heatmap: rows = neurons, columns = stimuli, color = mean response
stimuli_list  = sorted(results_df['stimulus'].unique())
sessions_list = sorted(results_df['session'].unique())

fig, axes = plt.subplots(1, len(sessions_list),
                          figsize=(5 * len(sessions_list), 8),
                          sharey=True)

if len(sessions_list) == 1:
    axes = [axes]

for ax, session in zip(axes, sessions_list):
    pivot = results_df[results_df['session'] == session].pivot(
        index='global_neuron', columns='stimulus', values='mean_response'
    )
    im = ax.imshow(pivot.values, aspect='auto', cmap='RdBu_r',
                   vmin=-0.5, vmax=0.5)
    ax.set_title(session)
    ax.set_xlabel('Stimulus')
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha='right')

axes[0].set_ylabel('Global Neuron ID')
plt.colorbar(im, ax=axes[-1], label='Mean ΔF/F response')
plt.suptitle(f'{MOUSE_ID} — Neuron × Stimulus Response Matrix')
plt.tight_layout()
plt.savefig(f'{RESULTS_DIR}/plots/{MOUSE_ID}/response_heatmap.png', dpi=150)
plt.close()

# ── Plot: Does response change across days? ────────────────────────────────────
for stimulus in stimuli_list:
    stim_data = results_df[results_df['stimulus'] == stimulus]
    
    session_means = stim_data.groupby('session')['mean_response'].agg(['mean', 'sem'])
    
    plt.figure(figsize=(6, 4))
    plt.errorbar(
        session_means.index,
        session_means['mean'],
        yerr=session_means['sem'],
        marker='o', linewidth=2, capsize=5
    )
    plt.axhline(0, color='gray', linestyle='--', alpha=0.5)
    plt.xlabel('Session')
    plt.ylabel('Mean population response (ΔF/F)')
    plt.title(f'{MOUSE_ID} — {stimulus} response across sessions')
    plt.tight_layout()
    plt.savefig(
        f'{RESULTS_DIR}/plots/{MOUSE_ID}/across_sessions_{stimulus}.png',
        dpi=150
    )
    plt.close()

print(f'\n=== Analysis complete ===')
print(f'Plots saved to: {RESULTS_DIR}/plots/{MOUSE_ID}/')
print(f'Table saved to: {table_path}')