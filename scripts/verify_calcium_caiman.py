#!/usr/bin/env python
"""
End-to-end smoke test for pipeline.calcium.CaImAnProcessor, run against
CaImAn's own bundled 1-photon microendoscope demo movie (data_endoscope.tif).

Must be run inside the `caiman` conda env:

    conda activate caiman
    python scripts/verify_calcium_caiman.py

Exits non-zero on any assertion failure.
"""

import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import caiman
from caiman.utils.utils import download_demo

from pipeline.calcium import CalciumRecording, load_calcium_result, save_calcium_result
from pipeline.calcium.caiman_processor import DEFAULT_CONFIG, CaImAnProcessor

OUTPUT_NPZ = os.path.join("data", "sample", "calcium_caiman_endoscope.npz")
OUTPUT_HEATMAP = os.path.join("data", "sample", "calcium_caiman_endoscope_heatmap.png")


def locate_demo_movie() -> str:
    candidate = os.path.join(caiman.paths.caiman_datadir(), "example_movies", "data_endoscope.tif")
    if os.path.isfile(candidate):
        return candidate
    print(f"data_endoscope.tif not found at {candidate}, downloading...")
    return download_demo("data_endoscope.tif")


def main():
    logging.basicConfig(level=logging.INFO, format="[%(filename)s:%(funcName)s():%(lineno)s] %(message)s")

    movie_path = locate_demo_movie()
    print(f"Using demo movie: {movie_path}")

    recording = CalciumRecording(movie_path=movie_path)
    processor = CaImAnProcessor(config_path=DEFAULT_CONFIG)

    start = time.time()
    result = processor.process(recording)
    elapsed = time.time() - start

    n_samples = result.dff.shape[0]

    assert result.n_components_accepted > 0, "expected at least one accepted component"
    assert result.dff.shape == (n_samples, result.n_components_accepted), (
        f"dff shape {result.dff.shape} does not match "
        f"(n_samples={n_samples}, n_components_accepted={result.n_components_accepted})"
    )
    assert np.isfinite(result.dff).all(), "dff contains non-finite values"
    assert len(result.timestamps) == n_samples, "timestamps length mismatch"
    assert np.all(np.diff(result.timestamps) > 0), "timestamps are not monotonically increasing"

    save_calcium_result(result, OUTPUT_NPZ)
    reloaded = load_calcium_result(OUTPUT_NPZ)
    assert np.allclose(reloaded.dff, result.dff), "round-trip mismatch on dff"
    assert np.allclose(reloaded.timestamps, result.timestamps), "round-trip mismatch on timestamps"

    os.makedirs(os.path.dirname(OUTPUT_HEATMAP), exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(
        result.dff.T,
        aspect="auto",
        extent=(float(result.timestamps[0]), float(result.timestamps[-1]), 0.0, result.dff.shape[1]),
        origin="lower",
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ROI")
    ax.set_title("CaImAn CNMF-E dF/F — data_endoscope.tif")
    fig.tight_layout()
    fig.savefig(OUTPUT_HEATMAP, dpi=150)
    plt.close(fig)

    print(
        f"\n=== verify_calcium_caiman: PASSED ===\n"
        f"Components: {result.n_components_accepted}/{result.n_components_total} accepted\n"
        f"dff shape: {result.dff.shape}\n"
        f"frame_rate: {result.frame_rate} Hz\n"
        f"elapsed: {elapsed:.1f}s\n"
        f"npz: {OUTPUT_NPZ}\n"
        f"heatmap: {OUTPUT_HEATMAP}\n"
    )


if __name__ == "__main__":
    main()
