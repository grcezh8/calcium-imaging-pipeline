# calciumimagingpipeline

HOW TO RUN EVERYTHING:
On your Mac (write code, test configs)
cd calcium-imaging-pipeline
git pull                            # always pull before editing

Edit scripts, update configs/params.yaml
Then push changes:
git add .
git commit -m "describe what you changed"
git push

On the Windows lab computer (run the actual pipeline)
cd calcium-imaging-pipeline
git pull                            # get latest code from Mac

conda activate minian               # activate Minian's environment

Step 0: Validate your timestamp CSVs (fast, run first)
python scripts/00_prepare_timestamps.py

Step 1: Run Minian on each session (slow, ~1-2hrs each)
python scripts/01_run_minian.py --mouse mouse_01 --session session_day1
python scripts/01_run_minian.py --mouse mouse_01 --session session_day2
python scripts/01_run_minian.py --mouse mouse_01 --session session_day3

Step 2: Register neurons across sessions (fast, ~minutes)
python scripts/02_register_sessions.py --mouse mouse_01

Step 3: Export for CalTrig (fast)
python scripts/03_export_for_caltrig.py --mouse mouse_01 --session session_day1
python scripts/03_export_for_caltrig.py --mouse mouse_01 --session session_day2
python scripts/03_export_for_caltrig.py --mouse mouse_01 --session session_day3

Caltrig GUI (on Windows)
cd C:\Users\Lab\Calcium-Transient-Analysis   # wherever you cloned CalTrig
conda activate caltrig                        # CalTrig's own environment
python main.py
In the GUI: File → Open → navigate to outputs/mouse_01/session_day1/caltrig_input/
Verify neuron footprints, detect transients, export results
Repeat for each session

Back in your pipeline repo
conda activate minian

Analyze CalTrig output and generate plots
python scripts/04_analyze_results.py --mouse mouse_01

Push results back to GitHub (CSV files are small — fine to commit)
git add results/
git commit -m "Add results for mouse_01"
git push

COMMON ERRORS
    1. FileNotFoundError: local_config.yaml
        You forgot to create this file
        Create it manually on each machine — it's never on GitHub
    2. FileNotFoundError: calcium_day1.avi
        Filename doesn't match expected pattern
        Check your actual filenames match the pattern in 01_run_minian.py
    3. conda env create fails on Windows
        Needs admin permissions
        Open Anaconda Prompt as Administrator
    4. Minian finds 0 neurons
        neuron_diameter is wrong
        Measure actual neuron size in pixels from a frame in Fiji/ImageJ
    5. open_minian returns empty
        Minian didn't finish saving
        Check that 01_run_minian.py completed without errors
    6. CalTrig can't open the zarr files
        Format mismatch
        Check CalTrig docs for exact expected array names and dimensions
    7. Cross-session registration gives mostly NaN
        Poor spatial alignment
        Check motion correction max shift; may need to pre-align sessions
    8. Git push fails with "file too large"
        You accidentally staged a data file
        Run git rm --cached filename and check your .gitignore
