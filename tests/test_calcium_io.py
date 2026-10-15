import numpy as np
import pytest

from pipeline.calcium import CalciumResult, load_calcium_result, save_calcium_result


def _result(n_samples=50, n_cells=4, dims=(8, 10)):
    rng = np.random.default_rng(0)
    return CalciumResult(
        dff=rng.normal(size=(n_samples, n_cells)).astype(np.float32),
        timestamps=np.arange(n_samples) / 10.0,
        frame_rate=10.0,
        raw_C=rng.normal(size=(n_samples, n_cells)).astype(np.float32),
        spatial_footprints=rng.random((n_cells,) + dims).astype(np.float32),
        frame_dims=dims,
        n_components_total=6,
        n_components_accepted=n_cells,
        processor_name="TestProcessor",
        processor_params={"init": {"gSig": [3, 3]}},
        source_file="movie.tif",
    )


def test_round_trip(tmp_path):
    original = _result()
    path = tmp_path / "out" / "result.npz"
    save_calcium_result(original, path)
    loaded = load_calcium_result(path)

    np.testing.assert_allclose(loaded.dff, original.dff)
    np.testing.assert_allclose(loaded.timestamps, original.timestamps)
    np.testing.assert_allclose(loaded.raw_C, original.raw_C)
    np.testing.assert_allclose(loaded.spatial_footprints, original.spatial_footprints)
    assert loaded.frame_rate == original.frame_rate
    assert loaded.frame_dims == original.frame_dims
    assert loaded.n_components_total == 6
    assert loaded.n_components_accepted == 4
    assert loaded.processor_name == "TestProcessor"
    assert loaded.processor_params == {"init": {"gSig": [3, 3]}}
    assert loaded.source_file == "movie.tif"
    assert loaded.schema_version == original.schema_version


def test_optional_fields_absent(tmp_path):
    original = CalciumResult(dff=np.zeros((5, 2)), timestamps=np.arange(5) / 20.0, frame_rate=20.0)
    path = tmp_path / "minimal.npz"
    save_calcium_result(original, path)
    loaded = load_calcium_result(path)

    assert loaded.raw_C is None
    assert loaded.spatial_footprints is None
    assert loaded.frame_dims is None
    assert loaded.n_components_accepted is None


def test_legacy_file_infers_frame_rate(tmp_path):
    # legacy artifacts (DANDI sample) only have dff + timestamps
    path = tmp_path / "legacy.npz"
    np.savez(path, dff=np.zeros((30, 3)), timestamps=100.0 + np.arange(30) / 30.0)
    loaded = load_calcium_result(path)

    assert loaded.frame_rate == pytest.approx(30.0)
    assert loaded.schema_version == "unknown"
    assert loaded.processor_params == {}
