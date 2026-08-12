"""Point Spread Function (PSF) generation.

The PSF is the image of a single point of light after passing through the eye's
(approximated) optics. Convolving a sharp image with the PSF simulates the blur
the eye adds; the pre-compensation engine inverts this PSF.

v0.1 uses a rotated, anisotropic Gaussian. This is intentionally simple and
deterministic. Later versions can add:
  * disk / defocus (circle-of-confusion) kernels,
  * wavelength-dependent (R/G/B) PSFs for chromatic-aberration compensation,
  * Zernike-coefficient-based PSFs from wavefront aberrometry.
"""

from __future__ import annotations

import math
import numpy as np


def generate_psf(
    width: int,
    height: int,
    sigma_x: float,
    sigma_y: float,
    angle_degrees: float,
) -> np.ndarray:
    """Return a normalised (sum == 1) HxW anisotropic Gaussian PSF.

    `sigma_x` is the standard deviation along the direction `angle_degrees`
    (measured counter-clockwise from the +x axis); `sigma_y` is perpendicular.
    """
    if width <= 0 or height <= 0:
        raise ValueError("PSF dimensions must be positive")
    sigma_x = max(float(sigma_x), 1e-3)
    sigma_y = max(float(sigma_y), 1e-3)

    cy, cx = (height - 1) / 2.0, (width - 1) / 2.0
    ys, xs = np.mgrid[0:height, 0:width]
    xs = xs - cx
    ys = ys - cy

    theta = math.radians(angle_degrees)
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    # Rotate coordinates into the PSF's principal axes.
    x_rot = xs * cos_t + ys * sin_t
    y_rot = -xs * sin_t + ys * cos_t

    psf = np.exp(-0.5 * ((x_rot / sigma_x) ** 2 + (y_rot / sigma_y) ** 2))
    total = psf.sum()
    if total <= 0:
        raise ValueError("degenerate PSF (sums to zero)")
    return (psf / total).astype(np.float64)


def kernel_size_for_sigma(sigma: float) -> int:
    """Odd kernel size that comfortably contains a Gaussian of given sigma."""
    size = int(math.ceil(sigma * 6.0)) | 1  # ~ +/-3 sigma, forced odd
    return max(size, 3)


def generate_psf_auto(sigma_x: float, sigma_y: float, angle_degrees: float) -> np.ndarray:
    """Convenience: pick a kernel size large enough for the given sigmas."""
    size = max(kernel_size_for_sigma(sigma_x), kernel_size_for_sigma(sigma_y))
    return generate_psf(size, size, sigma_x, sigma_y, angle_degrees)
