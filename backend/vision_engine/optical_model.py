"""Optical model: prescription + viewing geometry -> blur description (PSF params).

IMPORTANT (research boundary, per product spec section 3 & 11):
    The mapping implemented here is an *experimental approximation*. An eyeglass
    prescription (Sphere / Cylinder / Axis) does NOT fully characterise the eye's
    Point Spread Function. Real eyes have higher-order aberrations, chromatic
    aberration, scatter, an accommodating lens, and a pupil that changes size.

    This class is deliberately isolated behind a small, replaceable interface so
    that `prescription_to_psf_params` can later be swapped for a wavefront /
    measured-PSF model without touching the rendering pipeline. Do NOT present the
    heuristic below as clinically validated.

Physics used (first-order defocus + astigmatism):
    A defocused eye images a point as a blur circle on the retina. The angular
    diameter of that blur circle is approximately

        beta (radians) ~= pupil_diameter_m * |power_error_diopters|

    For a spherocylindrical prescription the dioptric error depends on meridian:
    the power along the axis meridian is |Sphere|, and along the perpendicular
    meridian it is |Sphere + Cylinder| (minus-cylinder convention). This produces
    an *elliptical* (astigmatic) blur oriented with the axis.

    The angular blur is projected onto the screen at the viewing distance and
    converted to pixels using the display pixel pitch, then approximated as a
    Gaussian whose sigma is a fraction of the blur-circle diameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math


MM_PER_INCH = 25.4


@dataclass
class EyePrescription:
    sphere: float          # dioptres (negative = myopia)
    cylinder: float = 0.0  # dioptres (minus-cylinder convention)
    axis: float = 0.0      # degrees, 0..180

    def validate(self) -> None:
        if not (-30.0 <= self.sphere <= 30.0):
            raise ValueError(f"sphere out of plausible range: {self.sphere}")
        if not (-12.0 <= self.cylinder <= 12.0):
            raise ValueError(f"cylinder out of plausible range: {self.cylinder}")
        if not (0.0 <= self.axis <= 180.0):
            raise ValueError(f"axis must be in [0, 180], got {self.axis}")


@dataclass
class DisplayParams:
    pixels_per_inch: float = 264.0     # default ~ iPad; overridden by device detection
    width_pixels: int = 0
    height_pixels: int = 0

    @property
    def pixel_pitch_mm(self) -> float:
        return MM_PER_INCH / self.pixels_per_inch


@dataclass
class BlurParams:
    """Anisotropic Gaussian blur description in *pixels*."""
    sigma_x: float
    sigma_y: float
    angle_degrees: float  # orientation of sigma_x axis
    # Diagnostics (not used by the renderer, useful for the research log):
    blur_diameter_px_meridian1: float = 0.0
    blur_diameter_px_meridian2: float = 0.0


class OpticalModel:
    """Replaceable optical model. Experimental approximation only."""

    def __init__(
        self,
        pupil_diameter_mm: float = 4.0,
        # Gaussian sigma as a fraction of the geometric blur-circle diameter.
        # A uniform disk of diameter d has an equivalent Gaussian sigma ~ d/4.
        sigma_per_diameter: float = 0.25,
        min_sigma_px: float = 0.35,
    ) -> None:
        self.pupil_diameter_mm = pupil_diameter_mm
        self.sigma_per_diameter = sigma_per_diameter
        self.min_sigma_px = min_sigma_px

    @staticmethod
    def _residual_defocus(power_diopters: float, viewing_distance_mm: float) -> float:
        """Residual defocus (dioptres) actually experienced at this distance.

        Far-point model: a relaxed myopic eye of power `S` (negative) is in focus
        at its far point (distance = -1/S) and blurs only for objects BEYOND it.
        Accommodation keeps nearer objects sharp, so

            defocus = max(0, -S - 1/distance_m)

        This makes a -2.5 D eye sharp at ~40 cm (its far point), blurred farther
        away, and bounds the blur instead of growing without limit with distance.
        An emmetrope (S=0) gets 0 at all distances it can accommodate to.
        """
        d_m = max(viewing_distance_mm / 1000.0, 1e-3)
        return max(0.0, -power_diopters - 1.0 / d_m)

    def _meridian_blur_diameter_px(
        self, power_diopters: float, viewing_distance_mm: float, display: DisplayParams
    ) -> float:
        """Geometric blur-circle diameter on screen, in pixels, for one meridian."""
        pupil_m = self.pupil_diameter_mm / 1000.0
        defocus = self._residual_defocus(power_diopters, viewing_distance_mm)
        beta_rad = pupil_m * defocus                       # blur angle (radians)
        blur_diameter_mm = beta_rad * viewing_distance_mm  # small-angle projection
        return blur_diameter_mm / display.pixel_pitch_mm

    def prescription_to_blur(
        self,
        prescription: EyePrescription,
        viewing_distance_mm: float,
        display: DisplayParams,
        correction_strength: float = 1.0,
    ) -> BlurParams:
        prescription.validate()

        # Dioptric power along the two principal meridians.
        power_axis = prescription.sphere
        power_perp = prescription.sphere + prescription.cylinder

        d1 = self._meridian_blur_diameter_px(power_axis, viewing_distance_mm, display)
        d2 = self._meridian_blur_diameter_px(power_perp, viewing_distance_mm, display)

        sigma1 = max(d1 * self.sigma_per_diameter * correction_strength, self.min_sigma_px)
        sigma2 = max(d2 * self.sigma_per_diameter * correction_strength, self.min_sigma_px)

        # The axis meridian carries `sigma1`. `sigma_x` is aligned to `angle`.
        return BlurParams(
            sigma_x=sigma1,
            sigma_y=sigma2,
            angle_degrees=prescription.axis,
            blur_diameter_px_meridian1=d1,
            blur_diameter_px_meridian2=d2,
        )
