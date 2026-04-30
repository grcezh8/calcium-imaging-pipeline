BEHAVIORAL VIDEO TIMESTAMPS CSV INSTRUCTIONS
This is the behavioral sync layer. For each session, you create one CSV that logs when each stimulus was presented. You do this manually by watching the behavioral video once.

STEPS:
    1. Open the behavioral video in VLC or QuickTime
    2. Go to View → Show Time to see exact timestamps
    3. For each stimulus event, note the time (in seconds from video start)
    4. Fill in the CSV template below (one per session)

TEMPLATE:
Save as: data/mouse_01/session_day1/timestamps.csv
stimulus_name,onset_seconds,offset_seconds,notes
odor_A,12.4,22.4,first presentation
food_reward,45.1,55.1,mouse approached immediately
novel_object,102.3,162.3,exploration period
odor_A,180.5,190.5,second presentation
odor_B,210.0,220.0,
food_reward,250.3,260.3,

DEFINITIONS:
    - stimulus_name — what the stimulus was (be consistent with spelling across sessions!)
    - onset_seconds — when stimulus started, in seconds from start of behavioral video
    - offset_seconds — when it ended (leave blank if instantaneous)
    - notes — optional, anything worth remembering

CONVERTING SECONDS → CALCIUM FRAMES
Your behavioral video is at 30 fps, calcium at 20 fps. A stimulus at second 12.4 in the behavior video = frame 12.4 × 20 = 248 in calcium. The script 00_prepare_timestamps.py does this conversion automatically.

DATA FOLDER STRUCTURE:
data/
└── mouse_01/
    ├── session_day1/
    │   ├── calcium_day1.avi         ← calcium video
    │   ├── behavior_day1.mp4        ← behavioral video
    │   └── timestamps.csv           ← YOU fill this in
    ├── session_day2/
    │   ├── calcium_day2.avi
    │   ├── behavior_day2.avi        ← avi or mp4, both fine
    │   └── timestamps.csv
    └── session_day3/
        ├── calcium_day3.avi
        ├── behavior_day3.mp4
        └── timestamps.csv
