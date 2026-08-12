"""Glue between the HTTP layer and the vision engine."""

from __future__ import annotations

import io
import base64
import numpy as np
from PIL import Image

from vision_engine import (
    OpticalModel, EyePrescription, DisplayParams, CalibrationProfile, VisionRenderer,
)

_renderer = VisionRenderer(OpticalModel())

MAX_DIM = 1400  # cap work for interactive latency


def load_image(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


def png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def png_base64(arr: np.ndarray) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes(arr)).decode("ascii")


def build(
    sphere: float, cylinder: float, axis: float,
    viewing_distance_mm: float, ppi: float,
    correction_strength: float, regularization: float, dynamic_range: float,
    contrast_boost: float,
) -> tuple[EyePrescription, DisplayParams, CalibrationProfile]:
    prescription = EyePrescription(sphere=sphere, cylinder=cylinder, axis=axis)
    display = DisplayParams(pixels_per_inch=ppi)
    cal = CalibrationProfile(
        correction_strength=correction_strength,
        regularization=regularization,
        dynamic_range=dynamic_range,
        contrast_boost=contrast_boost,
    )
    return prescription, display, cal


def renderer() -> VisionRenderer:
    return _renderer
