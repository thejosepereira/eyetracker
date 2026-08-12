"""VisionRenderer: the full pre-compensation pipeline (spec section 14 & 15).

    INPUT IMAGE
        -> linearise RGB
        -> optical model -> PSF
        -> Wiener inverse filtering (per channel)
        -> dynamic-range management (handle over/undershoot)
        -> contrast management
        -> gamma re-encode
    OUTPUT IMAGE

This module is the intellectual core of the system and is deliberately
independent of the web/mobile layers so the same engine can later become a GPU
shader, native library, or OEM display stage.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .optical_model import OpticalModel, EyePrescription, DisplayParams, BlurParams
from .psf import generate_psf_auto
from .deconvolution import wiener_precompensate, apply_psf
from .calibration import CalibrationProfile
from . import color


@dataclass
class RenderResult:
    image: np.ndarray            # uint8 HxWx3, ready to display
    blur: BlurParams
    psf_shape: tuple[int, int]
    clipped_fraction: float      # diagnostic: how much of the signal hit the rails


def _reduce_contrast(lin: np.ndarray, dynamic_range: float) -> np.ndarray:
    """Squeeze a linear-light channel toward mid-grey to create headroom.

    Pre-compensation must push some pixels below 0 / above 1 to cancel the eye's
    blur, but a physical display can only show [0,1]. Reducing the target's
    contrast first keeps the pre-compensated result inside the displayable range,
    so clipping barely damages the cancellation. This is the accepted technique
    for pre-compensation on conventional (non-light-field) displays.
    """
    dr = float(np.clip(dynamic_range, 0.05, 1.0))
    return 0.5 + (lin - 0.5) * dr


class VisionRenderer:
    def __init__(self, optical_model: OpticalModel | None = None) -> None:
        self.optical_model = optical_model or OpticalModel()

    def render(
        self,
        image: np.ndarray,
        prescription: EyePrescription,
        display: DisplayParams,
        viewing_distance_mm: float,
        calibration: CalibrationProfile | None = None,
        precompensate: bool = True,
    ) -> RenderResult:
        """image: uint8 HxWx3 (sRGB). Returns a RenderResult.

        `precompensate=False` applies the same contrast reduction (dynamic range)
        but skips the inverse filter. This yields the study's *control* condition:
        contrast-matched to the corrected image but without the pre-distortion, so
        a real-human test can isolate the sharpening from the contrast change.
        """
        cal = calibration or CalibrationProfile()
        if image.ndim == 2:
            image = np.stack([image] * 3, axis=-1)
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        blur = self.optical_model.prescription_to_blur(
            prescription, viewing_distance_mm, display,
            correction_strength=cal.correction_strength,
        )
        psf = generate_psf_auto(blur.sigma_x, blur.sigma_y, blur.angle_degrees)

        chroma = (
            (cal.chromatic.red, cal.chromatic.green, cal.chromatic.blue)
            if cal.chromatic else (1.0, 1.0, 1.0)
        )

        srgb = image.astype(np.float64) / 255.0
        out = np.empty_like(srgb)
        clipped = 0.0
        for c in range(3):
            lin = color.srgb_to_linear(srgb[..., c])
            # Squeeze the target's contrast to leave room for the overshoot that
            # pre-compensation needs, then invert the blur.
            target = _reduce_contrast(lin, cal.dynamic_range)
            # Per-channel PSF scaling supports (later) chromatic-aberration comp.
            chan_psf = psf if chroma[c] == 1.0 else generate_psf_auto(
                blur.sigma_x * chroma[c], blur.sigma_y * chroma[c], blur.angle_degrees
            )
            if precompensate:
                pre = wiener_precompensate(target, chan_psf, regularization=cal.regularization)
            else:
                pre = target  # control: contrast-reduced only, no inverse filter

            clipped += float(np.mean((pre < 0.0) | (pre > 1.0)))
            managed = np.clip(0.5 + (pre - 0.5) * cal.contrast_boost, 0.0, 1.0)
            out[..., c] = color.linear_to_srgb(managed)

        result = np.clip(out * 255.0, 0, 255).astype(np.uint8)
        return RenderResult(
            image=result,
            blur=blur,
            psf_shape=psf.shape,
            clipped_fraction=clipped / 3.0,
        )

    def simulate_eye_view(
        self,
        image: np.ndarray,
        prescription: EyePrescription,
        display: DisplayParams,
        viewing_distance_mm: float,
        correction_strength: float = 1.0,
    ) -> np.ndarray:
        """Simulate what this prescription's eye perceives when it looks at `image`.

        Convolves the image with the estimated eye PSF (in linear light). Used to
        demonstrate that EyeBlur(P(Image)) ~= Image.
        """
        if image.ndim == 2:
            image = np.stack([image] * 3, axis=-1)
        blur = self.optical_model.prescription_to_blur(
            prescription, viewing_distance_mm, display, correction_strength
        )
        psf = generate_psf_auto(blur.sigma_x, blur.sigma_y, blur.angle_degrees)

        srgb = image.astype(np.float64) / 255.0
        out = np.empty_like(srgb)
        for c in range(3):
            lin = color.srgb_to_linear(srgb[..., c])
            blurred = apply_psf(lin, psf)
            out[..., c] = color.linear_to_srgb(np.clip(blurred, 0.0, 1.0))
        return np.clip(out * 255.0, 0, 255).astype(np.uint8)
