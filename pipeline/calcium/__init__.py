from .base import CalciumProcessor, CalciumRecording, CalciumResult
from .io import load_calcium_result, save_calcium_result

__all__ = [
    "CalciumProcessor",
    "CalciumRecording",
    "CalciumResult",
    "load_calcium_result",
    "save_calcium_result",
]

try:
    from .caiman_processor import CaImAnProcessor  # noqa: F401

    __all__.append("CaImAnProcessor")
except ImportError:
    # caiman is only installed in the dedicated `caiman` conda env; importing
    # pipeline.calcium from the lightweight (streamlit/dandi) env should still work.
    pass
