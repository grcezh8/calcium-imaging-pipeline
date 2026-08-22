# Calcium processing config

`cnmfe_default.json` holds CaImAn's CNMF-E parameter groups (`data`, `motion`, `init`, `preprocess`, `temporal`, `spatial`, `patch`, `merging`, `quality`), seeded from CaImAn's own `demos/general/params_demo_pipeline_cnmfE.json`. It's loaded directly as `params.CNMFParams(params_from_file=...)` — see [caiman_processor.py](../../pipeline/calcium/caiman_processor.py).

**Rig-specific — measure from your own data, don't trust the defaults:**
- `data.fr` — imaging frame rate (Hz). Check your acquisition software.
- `init.gSig` / `init.gSiz` — expected neuron radius / diameter in pixels. Measure an actual cell in a frame (e.g. in Fiji/ImageJ). CaImAn defaults `gSiz` to `2*gSig + 1` if you only set `gSig`.
- `init.min_corr` / `init.min_pnr` — correlation/peak-to-noise thresholds for candidate neuron detection. Start with the defaults, then inspect the correlation/PNR summary images CaImAn prints and adjust.
- `motion.max_shifts` — how far a frame is allowed to shift during motion correction; increase if your prep moves more than that.

This mirrors the same "measure this from your actual images" guidance `oldthings/configs/params.yaml` used for Minian's `neuron_diameter`.

**Safe to leave as-is for a first run:** everything else (`preprocess`, `temporal`, `spatial`, `patch`, `merging`, `quality` groups) — these are algorithm tuning knobs, not physical properties of your rig.

`scripts/run_calcium_caiman.py` exposes `--fr`, `--gSig`, `--gSiz`, `--min-corr`, `--min-pnr` as CLI overrides so you don't have to edit this file per recording.
