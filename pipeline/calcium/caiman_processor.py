import logging
from pathlib import Path
from typing import Optional

import numpy as np

import caiman
from caiman.motion_correction import MotionCorrect
from caiman.source_extraction.cnmf import cnmf
from caiman.source_extraction.cnmf import params as caiman_params

from .base import CalciumProcessor, CalciumRecording, CalciumResult

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "calcium" / "cnmfe_default.json"


class CaImAnProcessor(CalciumProcessor):
    """CalciumProcessor implementation backed by CaImAn's CNMF-E pipeline
    (motion correction -> source extraction -> dF/F), for single-photon
    microendoscope/miniscope calcium movies.
    """

    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG,
        motion_correct: bool = True,
        cluster_backend: str = "multiprocessing",
        n_processes: Optional[int] = None,
    ):
        self.config_path = Path(config_path)
        self.motion_correct = motion_correct
        self.cluster_backend = cluster_backend
        self.n_processes = n_processes

    def process(self, recording: CalciumRecording) -> CalciumResult:
        opts = caiman_params.CNMFParams(params_from_file=str(self.config_path))
        opts.change_params({"data": {"fnames": [str(recording.movie_path)]}})
        if recording.frame_rate is not None:
            opts.change_params({"data": {"fr": recording.frame_rate}})
        if recording.params:
            opts.change_params(recording.params)

        c, dview, n_processes = caiman.cluster.setup_cluster(
            backend=self.cluster_backend, n_processes=self.n_processes
        )
        try:
            bord_px = 0
            if self.motion_correct:
                logger.info("Running motion correction...")
                mc = MotionCorrect(opts.data["fnames"], dview=dview, **opts.get_group("motion"))
                mc.motion_correct(save_movie=True)
                fname_mc = mc.fname_tot_els if opts.motion["pw_rigid"] else mc.fname_tot_rig
                if opts.motion["pw_rigid"]:
                    bord_px = np.ceil(
                        np.maximum(np.max(np.abs(mc.x_shifts_els)), np.max(np.abs(mc.y_shifts_els)))
                    ).astype(int)
                else:
                    bord_px = np.ceil(np.max(np.abs(mc.shifts_rig))).astype(int)
                bord_px = 0 if opts.motion["border_nan"] == "copy" else bord_px
                fname_new = caiman.save_memmap(
                    fname_mc, base_name="memmap_", order="C", border_to_0=bord_px
                )
            else:
                fname_new = caiman.save_memmap(
                    opts.data["fnames"], base_name="memmap_", order="C", border_to_0=0, dview=dview
                )

            Yr, dims, T = caiman.load_memmap(fname_new)
            images = Yr.T.reshape((T,) + dims, order="F")

            opts.change_params(params_dict={"dims": dims, "border_pix": bord_px})

            cn_filter, pnr = caiman.summary_images.correlation_pnr(
                images[::1], gSig=opts.init["gSig"][0], swap_dim=False
            )
            logger.info(
                "Correlation/PNR summary computed (min_corr=%s, min_pnr=%s)",
                opts.init["min_corr"],
                opts.init["min_pnr"],
            )

            logger.info("Running CNMF-E source extraction...")
            cnm = cnmf.CNMF(n_processes=n_processes, dview=dview, Ain=None, params=opts)
            cnm.fit(images)

            logger.info("Evaluating components...")
            cnm.estimates.evaluate_components(images, cnm.params, dview=dview)

            logger.info("Computing dF/F...")
            # NOTE: CNMF-E's default (ring-model) background does not populate
            # estimates.b/estimates.f, so detrend_df_f() falls back to a zero
            # baseline and CaImAn logs "Background components not present...
            # results should be interpreted as detrended, not DF/F normalized."
            # The resulting F_dff is a detrended trace, not a true F0-normalized
            # dF/F, under this config. This mirrors why CaImAn's own
            # demo_pipeline_cnmfE.py never calls detrend_df_f() (only the 2p
            # demo_pipeline.py does, where plain CNMF's low-rank background
            # does populate b/f). Getting true ΔF/F out of CNMF-E requires a
            # background config that retains b/f (e.g. a non-patch run or
            # nb_patch > 0) — a further tuning task, not addressed here.
            cnm.estimates.detrend_df_f(quantileMin=8, frames_window=250)
        finally:
            caiman.stop_server(dview=dview)

        idx = np.asarray(cnm.estimates.idx_components)
        n_total = len(cnm.estimates.C)
        n_accepted = len(idx)

        dff = cnm.estimates.F_dff[idx].T.astype(np.float32) if n_accepted else np.zeros((T, 0), dtype=np.float32)
        raw_C = cnm.estimates.C[idx].T.astype(np.float32) if n_accepted else np.zeros((T, 0), dtype=np.float32)

        if n_accepted:
            A_dense = np.asarray(cnm.estimates.A[:, idx].todense())
            spatial_footprints = A_dense.reshape(dims + (n_accepted,), order="F")
            spatial_footprints = np.moveaxis(spatial_footprints, -1, 0).astype(np.float32)
        else:
            spatial_footprints = np.zeros((0,) + dims, dtype=np.float32)

        frame_rate = float(opts.data["fr"])
        timestamps = np.arange(T) / frame_rate

        logger.info("Done: %d/%d components accepted", n_accepted, n_total)

        return CalciumResult(
            dff=dff,
            timestamps=timestamps,
            frame_rate=frame_rate,
            raw_C=raw_C,
            spatial_footprints=spatial_footprints,
            frame_dims=tuple(dims),
            n_components_total=n_total,
            n_components_accepted=n_accepted,
            processor_name="CaImAnProcessor",
            processor_params=opts.to_dict(),
            source_file=str(recording.movie_path),
        )
