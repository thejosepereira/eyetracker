"""Pre-compensation via regularised (Wiener) inverse filtering.

Given a desired image I and an estimated eye PSF H, we want a pre-compensated
image P such that convolving P with the eye's blur reproduces I:

        H * P  ~=  I

The naive inverse P = IFFT(FFT(I) / FFT(H)) explodes wherever FFT(H) is near
zero (high frequencies), producing extreme ringing and noise. We instead use the
regularised inverse

        G = conj(H_f) / (|H_f|^2 + K)
        P = IFFT( FFT(I) * G )

K is the regularisation term. Larger K -> more stable, softer correction; smaller
K -> stronger correction but more ringing/overshoot. This is the single most
important tuning knob and is exposed via the calibration profile.
"""

from __future__ import annotations

import numpy as np


def _psf_to_otf(psf: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Embed a small (already normalised) PSF into `shape` and return its FFT.

    The PSF centre is moved to the array origin (via ifftshift after centring)
    so that filtering introduces no spatial shift.
    """
    H, W = shape
    # Center-crop a PSF that is larger than the image, then renormalise. This
    # keeps small images working (the kernel tails are negligible).
    if psf.shape[0] > H or psf.shape[1] > W:
        ch, cw = psf.shape[0] // 2, psf.shape[1] // 2
        h2, w2 = min(H, psf.shape[0]) // 2, min(W, psf.shape[1]) // 2
        psf = psf[ch - h2: ch - h2 + min(H, psf.shape[0]),
                  cw - w2: cw - w2 + min(W, psf.shape[1])]
        s = psf.sum()
        if s > 0:
            psf = psf / s
    ph, pw = psf.shape

    padded = np.zeros(shape, dtype=np.float64)
    padded[:ph, :pw] = psf
    # Move the PSF centre to (0, 0).
    padded = np.roll(padded, -(ph // 2), axis=0)
    padded = np.roll(padded, -(pw // 2), axis=1)
    return np.fft.fft2(padded)


def wiener_precompensate(
    image: np.ndarray,
    psf: np.ndarray,
    regularization: float = 0.01,
) -> np.ndarray:
    """Return the pre-compensated single-channel image (float, may exceed [0,1]).

    `image` is a 2-D float array (linear light, nominally [0,1]).
    `psf`   is a normalised 2-D kernel.
    """
    if image.ndim != 2:
        raise ValueError("wiener_precompensate expects a single 2-D channel")
    K = max(float(regularization), 1e-8)

    otf = _psf_to_otf(psf, image.shape)
    img_f = np.fft.fft2(image)
    g = np.conj(otf) / (np.abs(otf) ** 2 + K)
    result = np.fft.ifft2(img_f * g)
    return np.real(result)


def apply_psf(image: np.ndarray, psf: np.ndarray) -> np.ndarray:
    """Convolve an image with a PSF (simulates the eye's blur). Single channel."""
    if image.ndim != 2:
        raise ValueError("apply_psf expects a single 2-D channel")
    otf = _psf_to_otf(psf, image.shape)
    return np.real(np.fft.ifft2(np.fft.fft2(image) * otf))
