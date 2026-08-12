"""VisionCorrect vision engine.

The engine is UI-independent so it can evolve into an SDK / GPU library / native
renderer. Public surface:

    OpticalModel, EyePrescription, DisplayParams   -- prescription -> blur
    generate_psf                                    -- PSF kernels
    wiener_precompensate, apply_psf                 -- inverse / forward filtering
    CalibrationProfile, PairwiseStaircase           -- interactive tuning
    VisionRenderer                                  -- full pipeline
"""

from .optical_model import OpticalModel, EyePrescription, DisplayParams, BlurParams
from .psf import generate_psf, generate_psf_auto
from .deconvolution import wiener_precompensate, apply_psf
from .calibration import CalibrationProfile, PairwiseStaircase, ChromaticCompensation
from .renderer import VisionRenderer, RenderResult

__all__ = [
    "OpticalModel", "EyePrescription", "DisplayParams", "BlurParams",
    "generate_psf", "generate_psf_auto",
    "wiener_precompensate", "apply_psf",
    "CalibrationProfile", "PairwiseStaircase", "ChromaticCompensation",
    "VisionRenderer", "RenderResult",
]

__version__ = "0.1.0"
