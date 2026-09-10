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


def generate_disk_psf(
    size: int, radius_x: float, radius_y: float, angle_degrees: float
) -> np.ndarray:
    """Elliptical uniform-disk (pillbox) PSF — the physically-correct geometric
    defocus PSF. Edge anti-aliased by 3x3 supersampling, normalised to sum 1.

    Unlike the Gaussian, the disk OTF has genuine nulls (this is what a defocused
    eye actually produces). Matching the correction PSF to this markedly improves
    the achievable correction (see docs/phase2-study.md).
    """
    rx = max(float(radius_x), 0.5)
    ry = max(float(radius_y), 0.5)
    c = (size - 1) / 2.0
    theta = math.radians(angle_degrees)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    ss = 3
    offs = [(k + 0.5) / ss - 0.5 for k in range(ss)]
    psf = np.zeros((size, size), dtype=np.float64)
    for y in range(size):
        for x in range(size):
            frac = 0
            for oy in offs:
                for ox in offs:
                    dx, dy = (x - c) + ox, (y - c) + oy
                    xr = dx * cos_t + dy * sin_t
                    yr = -dx * sin_t + dy * cos_t
                    if (xr / rx) ** 2 + (yr / ry) ** 2 <= 1.0:
                        frac += 1
            psf[y, x] = frac / (ss * ss)
    total = psf.sum()
    if total <= 0:
        psf[size // 2, size // 2] = 1.0
        return psf
    return psf / total


def kernel_size_for_sigma(sigma: float) -> int:
    """Odd kernel size that comfortably contains a Gaussian of given sigma."""
    size = int(math.ceil(sigma * 6.0)) | 1  # ~ +/-3 sigma, forced odd
    return max(size, 3)


def generate_psf_auto(sigma_x: float, sigma_y: float, angle_degrees: float) -> np.ndarray:
    """Convenience: pick a kernel size large enough for the given sigmas."""
    size = max(kernel_size_for_sigma(sigma_x), kernel_size_for_sigma(sigma_y))
    return generate_psf(size, size, sigma_x, sigma_y, angle_degrees)
