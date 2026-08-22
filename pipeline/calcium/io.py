import json
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .base import CalciumResult, SCHEMA_VERSION


def save_calcium_result(result: CalciumResult, out_path: Union[str, Path]) -> None:
    payload = {
        "dff": np.asarray(result.dff, dtype=np.float32),
        "timestamps": np.asarray(result.timestamps, dtype=np.float64),
        "frame_rate": np.float64(result.frame_rate),
        "processor": result.processor_name,
        "processor_params": json.dumps(result.processor_params, default=str),
        "source_file": result.source_file,
        "schema_version": result.schema_version,
    }
    if result.raw_C is not None:
        payload["raw_C"] = np.asarray(result.raw_C, dtype=np.float32)
    if result.spatial_footprints is not None:
        payload["spatial_footprints"] = np.asarray(result.spatial_footprints, dtype=np.float32)
    if result.frame_dims is not None:
        payload["frame_dims"] = np.asarray(result.frame_dims, dtype=np.int64)
    if result.n_components_total is not None:
        payload["n_components_total"] = np.int64(result.n_components_total)
    if result.n_components_accepted is not None:
        payload["n_components_accepted"] = np.int64(result.n_components_accepted)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out_path, **payload)


def load_calcium_result(path: Union[str, Path]) -> CalciumResult:
    with np.load(path, allow_pickle=False) as data:
        files = set(data.files)

        dff = data["dff"]
        timestamps = data["timestamps"]

        if "frame_rate" in files:
            frame_rate = float(data["frame_rate"])
        else:
            # legacy artifacts (e.g. data/sample/calcium_100_110.npz) have no
            # explicit frame_rate — fall back to the median timestamp spacing.
            diffs = np.diff(timestamps)
            frame_rate = float(1.0 / np.median(diffs)) if len(diffs) else 0.0

        def _get_array(key: str) -> Optional[np.ndarray]:
            return data[key] if key in files else None

        def _get_str(key: str, default: str = "") -> str:
            return str(data[key]) if key in files else default

        def _get_int(key: str) -> Optional[int]:
            return int(data[key]) if key in files else None

        processor_params_raw = _get_str("processor_params", "{}")
        try:
            processor_params = json.loads(processor_params_raw) if processor_params_raw else {}
        except json.JSONDecodeError:
            processor_params = {}

        frame_dims_arr = _get_array("frame_dims")
        frame_dims = tuple(int(x) for x in frame_dims_arr) if frame_dims_arr is not None else None

        return CalciumResult(
            dff=dff,
            timestamps=timestamps,
            frame_rate=frame_rate,
            raw_C=_get_array("raw_C"),
            spatial_footprints=_get_array("spatial_footprints"),
            frame_dims=frame_dims,
            n_components_total=_get_int("n_components_total"),
            n_components_accepted=_get_int("n_components_accepted"),
            processor_name=_get_str("processor"),
            processor_params=processor_params,
            source_file=_get_str("source_file"),
            schema_version=_get_str("schema_version", "unknown"),
        )
