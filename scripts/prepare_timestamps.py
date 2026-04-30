# scripts/00_prepare_timestamps.py
#
# PURPOSE: Validate your timestamp CSVs and convert behavioral video
#          seconds → calcium imaging frame numbers.
#
# This is a quick sanity check to run before Minian.
# It catches typos in stimulus names, missing files, and timing mismatches
# BEFORE you've spent hours running Minian.
#
# Run: python scripts/00_prepare_timestamps.py
# Run from: repo root directory

import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config

cfg = load_config()

DATA_DIR      = cfg['data_dir']
MOUSE_IDS     = cfg['experiment']['mouse_ids']
SESSIONS      = [f'session_day{i+1}' for i in range(cfg['experiment']['sessions_per_mouse'])]
BEHAVIOR_FPS  = cfg['behavior']['behavior_fps']
CALCIUM_FPS   = cfg['minian']['frame_rate']


def seconds_to_calcium_frames(seconds, behavior_fps, calcium_fps):
    """
    Convert a timestamp in behavioral video seconds to
    the equivalent frame number in the calcium recording.
    
    WHY: Behavioral video runs at 30 fps, calcium at 20 fps.
         They start at the same moment (approximately).
         A stimulus at second 12.4 in behavior video
         = 12.4 × 20 = frame 248 in calcium.
    
    NOTE: This assumes both recordings started at the same time.
          If you have a sync signal, use that instead.
    """
    return np.round(np.array(seconds) * calcium_fps).astype(int)


all_valid = True

for mouse_id in MOUSE_IDS:
    for session in SESSIONS:
        
        session_dir = os.path.join(DATA_DIR, mouse_id, session)
        ts_path     = os.path.join(session_dir, 'timestamps.csv')
        
        # Check the file exists
        if not os.path.exists(ts_path):
            print(f'⚠️  MISSING: {ts_path}')
            all_valid = False
            continue
        
        # Load and validate
        df = pd.read_csv(ts_path)
        
        # Check required columns exist
        required_cols = ['stimulus_name', 'onset_seconds']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            print(f'❌ {ts_path} missing columns: {missing_cols}')
            all_valid = False
            continue
        
        # Check for NaN values in critical columns
        if df['stimulus_name'].isna().any():
            print(f'❌ {ts_path} has blank stimulus_name entries')
            all_valid = False
            continue
        
        if df['onset_seconds'].isna().any():
            print(f'❌ {ts_path} has blank onset_seconds entries')
            all_valid = False
            continue
        
        # Convert to calcium frames
        df['onset_calcium_frame']  = seconds_to_calcium_frames(
            df['onset_seconds'], BEHAVIOR_FPS, CALCIUM_FPS
        )
        
        if 'offset_seconds' in df.columns:
            df['offset_calcium_frame'] = seconds_to_calcium_frames(
                df['offset_seconds'].fillna(df['onset_seconds'] + 1),
                BEHAVIOR_FPS, CALCIUM_FPS
            )
        
        # Save the enriched CSV alongside the original
        out_path = os.path.join(session_dir, 'timestamps_with_frames.csv')
        df.to_csv(out_path, index=False)
        
        # Print summary
        stimulus_counts = df['stimulus_name'].value_counts()
        print(f'✅ {mouse_id}/{session}:')
        for stim, count in stimulus_counts.items():
            first_frame = df[df['stimulus_name'] == stim]['onset_calcium_frame'].iloc[0]
            print(f'   {stim}: {count} presentations | first at calcium frame {first_frame}')

if all_valid:
    print('\n✅ All timestamp files valid. Ready for Minian.')
else:
    print('\n❌ Fix the issues above before running Minian.')
