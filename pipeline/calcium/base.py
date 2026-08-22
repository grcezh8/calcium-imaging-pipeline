from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

SCHEMA_VERSION = "1.0"


@dataclass
class CalciumRecording:
    movie_path: Path
    frame_rate: Optional[float] = None
    params: dict = field(default_factory=dict)


@dataclass
class CalciumResult:
    dff: np.ndarray
    timestamps: np.ndarray
    frame_rate: float
    raw_C: Optional[np.ndarray] = None
    spatial_footprints: Optional[np.ndarray] = None
    frame_dims: Optional[tuple] = None
    n_components_total: Optional[int] = None
    n_components_accepted: Optional[int] = None
    processor_name: str = ""
    processor_params: dict = field(default_factory=dict)
    source_file: str = ""
    schema_version: str = SCHEMA_VERSION


class CalciumProcessor(ABC):
    @abstractmethod
    def process(self, recording: CalciumRecording) -> CalciumResult:
        """Run motion correction + source extraction + dF/F on a raw calcium movie."""
