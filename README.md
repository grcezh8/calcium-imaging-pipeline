# Multimodal Calcium Imaging & Behavior Pipeline

An open-source, general-purpose pipeline for analyzing calcium imaging data alongside behavioral video. It takes the kinds of data a typical neuroscience lab already collects — a calcium movie and a behavior video — and handles the full path from raw recordings to interpretable neural-behavior relationships, through an interactive UI.

**What this project is not:** an analysis script for one particular experiment. The [DANDI](https://dandiarchive.org) dataset used during development happens to be richly multimodal (widefield imaging, multiple cameras, precomputed pose, task events), which makes it a convenient testbed — but the pipeline must not require any of that. It should work for a lab that has nothing more than a calcium movie and a behavior video.

```
"I have calcium imaging          DEVELOPMENT DATA (DANDI)
 + behavioral video."                    │
        │                                ▼
        ▼                          ┌───────────┐
   YOUR PIPELINE  ◄── validated ──►│  Pipeline │
        │                          └───────────┘
        ▼                                │
  INTERACTIVE UI                         ▼
"What was the animal doing        Does it work?
 when these neurons activated?"
```

The DANDI dataset is development and benchmarking data. It is not the subject of the project.

---

## MVP input model

A lab should be able to hand the pipeline as little as this:

**Required**
1. Calcium imaging movie
2. Behavioral video
3. Synchronization information (timestamps, or a shared clock/frame-rate relationship)

**Optional** — the pipeline adapts to whatever is present, and uses it in place of the equivalent processing step
4. Existing behavioral labels
5. Existing pose estimates
6. Additional sensors (e.g. lever, reward, licking)
7. Multiple cameras (body/face/eye)
8. Electrophysiology

Nothing beyond (1)–(3) should ever be a hard requirement.

---

## Architecture: five layers

### Layer 1 — Calcium imaging

```
raw calcium movie
       │
motion correction
       │
denoising (optional)
       │
ROI / neuron detection
       │
source extraction
       │
calcium traces
       │
     ΔF/F
```

Baseline engine: [CaImAn](https://github.com/flatironinstitute/CaImAn). The goal is not to replace CaImAn — it's to build a better end-to-end experience around the best available tools, with room for newer algorithms to plug in later (Suite2p, custom models, etc).

### Layer 2 — Behavioral video

```
behavior.mp4
     │
pose estimation
     │
body-part trajectories
     │
movement features
```

Baseline engines: SLEAP / DeepLabCut. Longer-term, video-understanding models (e.g. Video-LLaMA) can run alongside pose estimation as an *additional* source of behavioral information — not a replacement for it:

```
                BEHAVIOR VIDEO
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
    pose model                video model
         │                         │
    coordinates             semantic events
         │                         │
         └────────────┬────────────┘
                       ▼
                behavior state
```

### Layer 3 — Synchronization

Arguably the most important layer — it's what makes everything downstream possible. Calcium and video are rarely recorded at the same rate (e.g. calcium at 20 Hz, video at 60 FPS), so the pipeline builds a common time axis and resolves any timestamp/frame index to a shared point in time:

```
0 ─────────────────────────────────────────── 10 sec
Calcium:   |   |   |   |   |   |   |   |   |
Video:     ||||||||||||||||||||||||||||||||||
Behavior:  ──── walking ──── running ──── resting
```

calcium frame ↔ video frame ↔ absolute time, regardless of relative frame rates.

### Layer 4 — Neural ↔ behavior analysis

Once neural activity and behavior share a time axis, a standard set of analyses becomes available automatically:

| Analysis | Question it answers |
|---|---|
| Event-triggered analysis | What happens in neural activity around movement onset? |
| Encoding | Which neurons are associated with running? |
| Decoding | Can neural activity predict behavior? |
| Correlation | Does neural activity correlate with velocity? |
| Dimensionality reduction | Are there distinct neural states associated with different behaviors? |
| Population dynamics | How does the neural population evolve during a behavior? |

All of these surface through the UI, not just as scripts.

### Layer 5 — Modern ML / multimodal models

```
                     DATA
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
  calcium movie                behavior video
        │                            │
    CaImAn/etc.                 SLEAP/etc.
        │                            │
  neural traces                pose/features
        │                            │
        │                     video foundation
        │                          model
        │                            │
        │                     semantic behavior
        │                            │
        └─────────────┬──────────────┘
                       ▼
              MULTIMODAL ANALYSIS
                       ▼
               neural ↔ behavior
```

New models plug into this architecture rather than replacing it wholesale.

---

## Modular design

The most important architectural decision in this project: pipeline stages are interfaces, not a hard-coded chain of specific tools (CaImAn → SLEAP → Video-LLaMA).

```python
class CalciumProcessor:
    def process(self, recording): ...

class BehaviorProcessor:
    def process(self, video): ...

class BehaviorSemanticModel:
    def analyze(self, video): ...

class Synchronizer:
    def synchronize(self, modalities): ...

class NeuralBehaviorAnalyzer:
    def analyze(self, neural, behavior): ...
```

Users choose the implementation per stage:

```
Calcium:            Pose:                Video understanding:
○ CaImAn             ○ SLEAP              ○ None
○ Suite2p             ○ DeepLabCut         ○ Video-LLaMA
○ Custom model         ○ Custom model       ○ Other model
```

This is what makes it a platform rather than "a CaImAn wrapper for one dataset."

---

## The UI

The UI exposes scientific concepts, not tool names — a user should never need to know it's running CaImAn under the hood.

**1. Project setup** — upload calcium movie, behavioral video, and sync info, then `Analyze`.

**2. Processing** — a checklist of pipeline stages completing in order (motion correction → cell detection → calcium extraction → pose estimation → behavioral event detection → multimodal analysis).

**3. Analysis** — synchronized view of video, behavior timeline, and neural activity traces against a shared time axis.

**4. Ask about this experiment** — natural-language queries over the processed experiment, e.g. "Which neurons are most active during running?", "What typically happens before neuron 23 activates?", "Show me the behavioral events associated with this neural state." This is where the AI layer becomes genuinely useful — it sits on top of the structured pipeline output, rather than being the pipeline.

---

## Role of the DANDI dataset

The DANDI dataset (dandiset `001425`) is used purely for development and benchmarking, because it happens to contain many modalities that each exercise a different part of the pipeline:

| Dataset component | What it's used to develop |
|---|---|
| Calcium imaging | Calcium pipeline (Layer 1) |
| Behavioral video | CV pipeline (Layer 2) |
| Existing pose | Validate the pose pipeline against ground truth |
| Eye/face video | Test multi-camera support |
| Task events | Validate synchronization |
| Precomputed ΔF/F | Compare pipeline output against existing processing |

It is a sandbox and test case — not the subject of the project.

---

## Roadmap

**v0.1 — General pipeline**
calcium + behavior video → CaImAn → SLEAP → synchronization → visualization

**v0.2 — Automated analysis**
behavior detection → event-triggered neural analysis → decoding → interactive results

**v0.3 — Better CV**
SLEAP → newer pose/foundation models → better behavioral representations

**v0.4 — Video foundation models**
video → Video-LLaMA / newer video model → semantic behavioral events → neural correlations

**v0.5 — Multimodal ML**
neural representation ↔ behavior representation → joint embedding / transformer → neural-behavior relationships

**v1.0**
A lab hands the pipeline a calcium movie and a behavioral video, and gets back: the neurons, the behaviors, and how they relate.

---

## Current status

This repo is pre-v0.1 and functionality described above is aspirational except where noted:

- [app.py](app.py) — a Streamlit viewer (working prototype) that displays synchronized calcium traces, a live dF/F heatmap, and behavior video frames side by side, with manual behavioral event annotation ([events.py](events.py)).
- [pipeline/calcium/](pipeline/calcium/) — **Layer 1 is implemented.** `CalciumProcessor`/`CalciumRecording`/`CalciumResult` ([base.py](pipeline/calcium/base.py)) define the interface; `CaImAnProcessor` ([caiman_processor.py](pipeline/calcium/caiman_processor.py)) implements it as a full CaImAn CNMF-E pipeline (motion correction → source extraction → ΔF/F) for single-photon miniscope movies. Run it via `scripts/run_calcium_caiman.py` inside a dedicated `caiman` conda env (CaImAn's dependencies are heavy/pinned and deliberately isolated from the lightweight env `app.py` runs in); the result is saved as a portable `.npz` ([io.py](pipeline/calcium/io.py)) that any lightweight env can read with plain `numpy`. Configured via [configs/calcium/cnmfe_default.json](configs/calcium/cnmfe_default.json) — see [configs/calcium/README.md](configs/calcium/README.md) for which parameters are rig-specific. Verify end-to-end with `python scripts/verify_calcium_caiman.py` (also inside the `caiman` env).
  - Dev/test fixture note: the DANDI dataset used elsewhere in this repo is **widefield mesoscale** imaging (its `dFF_B`/`dFF_V` traces are hemodynamic-correction channels), which doesn't match CNMF-E's single-cell 1-photon assumptions and only ships precomputed traces, not a raw movie. Layer 1 is developed/tested instead against CaImAn's own bundled demo movie (`data_endoscope.tif`) — this is deliberate, not an oversight; see the plan history for the reasoning.
  - Known caveat: under CNMF-E's default (ring-model) background config, CaImAn's `detrend_df_f()` has no `b`/`f` background components to normalize against, so the `dff` field is a **detrended trace, not a true F0-normalized ΔF/F** (CaImAn logs this itself: "Background components not present..."). This is why CaImAn's own CNMF-E demo never calls `detrend_df_f()` at all. Getting true ΔF/F out of CNMF-E requires a background config that retains `b`/`f` — a follow-up tuning task, not yet done.
- [sync.py](sync.py) — a first-pass `Synchronizer` that maps experiment time ↔ calcium sample index ↔ video frame. Currently hardcoded to the sample clip's start offset; needs generalizing per the Layer 3 design above. Note that a `CaImAnProcessor` result's `timestamps` are movie-relative (derived from frame count / frame rate), not an absolute experiment clock — reconciling the two is exactly what the generalized synchronizer will need to handle.
- [danditest.py](danditest.py), [extractvideo.py](extractvideo.py) — scratch scripts for pulling a 10-second slice of calcium (ΔF/F) and body-camera video out of the DANDI NWB file into `data/sample/` for local development.
- [oldthings/](oldthings/) — an earlier, narrower approach built around a specific Minian → CalTrig multi-session workflow. Superseded by the architecture above; kept for reference.

Not yet implemented: pose estimation (Layer 2), the general N-modality synchronizer (Layer 3 exists only for the two-modality case), the analysis library (Layer 4), and any model-plugin architecture beyond the calcium stage (Layer 5). A `Suite2pProcessor` (or other `CalciumProcessor` implementation) can be added later against the same interface — nothing else in the pipeline needs to change.

## Getting started

```bash
pip install -r requirements.txt   # TODO: add requirements.txt
python danditest.py               # pulls a sample calcium/behavior slice from DANDI
python extractvideo.py            # extracts the matching video clip
streamlit run app.py              # launch the synchronized viewer
```
