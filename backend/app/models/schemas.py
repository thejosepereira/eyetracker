"""Pydantic request/response models for the VisionCorrect API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    sphere: float
    cylinder: float
    axis: float


class BlurOut(BaseModel):
    sigma_x: float
    sigma_y: float
    angle_degrees: float
    psf_width: int
    psf_height: int
    clipped_fraction: float


class CorrectResponse(BaseModel):
    success: bool = True
    processing_ms: int
    profile: ProfileOut
    blur: BlurOut
    output_base64: str | None = None
    output_url: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "VisionCorrect API"
    version: str


class DemoPanels(BaseModel):
    """Base64-encoded PNGs powering the browser before/after demo."""
    original: str
    uncorrected: str      # what the eye sees with correction OFF
    precompensated: str   # the pre-distorted image actually shown on screen
    corrected: str        # what the eye sees with correction ON
    blur: BlurOut
    processing_ms: int
