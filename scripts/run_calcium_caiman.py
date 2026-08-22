#!/usr/bin/env python
"""
Run CaImAn's CNMF-E pipeline on a raw calcium movie and save the result in the
pipeline's standard calcium artifact format (pipeline.calcium.io).

Must be run inside the `caiman` conda env:

    conda activate caiman
    python scripts/run_calcium_caiman.py \\
        --input ~/caiman_data/example_movies/data_endoscope.tif \\
        --config configs/calcium/cnmfe_default.json \\
        --fr 10 \\
        --output data/sample/calcium_caiman_endoscope.npz
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.calcium import CalciumRecording, save_calcium_result
from pipeline.calcium.caiman_processor import DEFAULT_CONFIG, CaImAnProcessor


def handle_args():
    parser = argparse.ArgumentParser(description="Run CaImAn CNMF-E on a raw calcium movie")
    parser.add_argument("--input", required=True, help="Path to the raw calcium movie (e.g. .tif/.avi)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="CNMFParams JSON config file")
    parser.add_argument("--output", required=True, help="Output .npz path for the calcium result")
    parser.add_argument("--fr", type=float, default=None, help="Override frame rate (Hz) — measure from your rig")
    parser.add_argument(
        "--gSig", type=int, default=None, help="Override expected neuron radius in pixels (init.gSig)"
    )
    parser.add_argument(
        "--gSiz", type=int, default=None, help="Override expected neuron diameter in pixels (init.gSiz)"
    )
    parser.add_argument("--min-corr", type=float, default=None, help="Override init.min_corr")
    parser.add_argument("--min-pnr", type=float, default=None, help="Override init.min_pnr")
    parser.add_argument(
        "--no-motion-correct", action="store_true", help="Skip motion correction, memory-map the raw movie directly"
    )
    parser.add_argument("--cluster-backend", default="multiprocessing", help="multiprocessing, ipyparallel, or single")
    parser.add_argument("--cluster-nproc", type=int, default=None, help="Override automatic worker count")
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format="[%(filename)s:%(funcName)s():%(lineno)s] %(message)s")
    args = handle_args()

    overrides: dict = {}
    init_overrides = {}
    if args.gSig is not None:
        init_overrides["gSig"] = [args.gSig, args.gSig]
    if args.gSiz is not None:
        init_overrides["gSiz"] = [args.gSiz, args.gSiz]
    if args.min_corr is not None:
        init_overrides["min_corr"] = args.min_corr
    if args.min_pnr is not None:
        init_overrides["min_pnr"] = args.min_pnr
    if init_overrides:
        overrides["init"] = init_overrides

    recording = CalciumRecording(
        movie_path=os.path.expanduser(args.input),
        frame_rate=args.fr,
        params=overrides,
    )

    processor = CaImAnProcessor(
        config_path=args.config,
        motion_correct=not args.no_motion_correct,
        cluster_backend=args.cluster_backend,
        n_processes=args.cluster_nproc,
    )

    start = time.time()
    result = processor.process(recording)
    elapsed = time.time() - start

    save_calcium_result(result, args.output)

    print(
        f"\nDone in {elapsed:.1f}s — "
        f"{result.n_components_accepted}/{result.n_components_total} components accepted, "
        f"dff shape {result.dff.shape}, frame_rate {result.frame_rate} Hz\n"
        f"Saved: {args.output}"
    )


if __name__ == "__main__":
    main()
