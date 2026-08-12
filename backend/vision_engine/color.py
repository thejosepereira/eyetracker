"""sRGB <-> linear-light conversion.

Blur (and therefore de-blur) is a physical, linear-light phenomenon. Working in
gamma-encoded sRGB would distort the convolution, so the pipeline linearises
before filtering and re-encodes afterwards.
"""

from __future__ import annotations

import numpy as np


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    """x in [0,1] gamma-encoded sRGB -> linear light [0,1]."""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    """Linear light [0,1] -> gamma-encoded sRGB [0,1]."""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1 / 2.4)) - 0.055)
