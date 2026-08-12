"""Correction endpoints (spec section 10)."""

from __future__ import annotations

import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import Response

from app.models.schemas import CorrectResponse, ProfileOut, BlurOut, DemoPanels
from app.services import imaging

router = APIRouter(prefix="/v1", tags=["correction"])


def _blur_out(result) -> BlurOut:
    return BlurOut(
        sigma_x=round(result.blur.sigma_x, 3),
        sigma_y=round(result.blur.sigma_y, 3),
        angle_degrees=round(result.blur.angle_degrees, 1),
        psf_width=result.psf_shape[1],
        psf_height=result.psf_shape[0],
        clipped_fraction=round(result.clipped_fraction, 4),
    )


@router.post("/correct")
async def correct(
    image: UploadFile = File(...),
    sphere: float = Form(...),
    cylinder: float = Form(0.0),
    axis: float = Form(0.0),
    viewing_distance_mm: float = Form(350.0),
    ppi: float = Form(264.0),
    correction_strength: float = Form(1.0),
    regularization: float = Form(0.012),
    dynamic_range: float = Form(0.55),
    contrast_boost: float = Form(1.0),
    precompensate: bool = Form(True),
    response: str = Query("png", pattern="^(png|json)$"),
):
    """Return the pre-compensated image to display.

    `response=png` returns the PNG body directly (simplest prototype contract).
    `response=json` returns metadata plus a base64 data URL.
    """
    try:
        data = await image.read()
        arr = imaging.load_image(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid image: {exc}") from exc

    try:
        prescription, display, cal = imaging.build(
            sphere, cylinder, axis, viewing_distance_mm, ppi,
            correction_strength, regularization, dynamic_range, contrast_boost,
        )
        t0 = time.perf_counter()
        result = imaging.renderer().render(
            arr, prescription, display, viewing_distance_mm, cal,
            precompensate=precompensate)
        ms = int((time.perf_counter() - t0) * 1000)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if response == "png":
        return Response(content=imaging.png_bytes(result.image), media_type="image/png")

    return CorrectResponse(
        success=True,
        processing_ms=ms,
        profile=ProfileOut(sphere=sphere, cylinder=cylinder, axis=axis),
        blur=_blur_out(result),
        output_base64=imaging.png_base64(result.image),
    )


@router.post("/demo", response_model=DemoPanels)
async def demo(
    image: UploadFile = File(...),
    sphere: float = Form(...),
    cylinder: float = Form(0.0),
    axis: float = Form(0.0),
    viewing_distance_mm: float = Form(350.0),
    ppi: float = Form(264.0),
    correction_strength: float = Form(1.0),
    regularization: float = Form(0.012),
    dynamic_range: float = Form(0.55),
    contrast_boost: float = Form(1.0),
):
    """Produce the four demonstration panels used by the browser demo:

    original / eye-view-uncorrected / pre-distorted / eye-view-corrected.
    The eye simulation lets you *see* the effect without physically having the
    prescribed refractive error.
    """
    try:
        data = await image.read()
        arr = imaging.load_image(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid image: {exc}") from exc

    try:
        prescription, display, cal = imaging.build(
            sphere, cylinder, axis, viewing_distance_mm, ppi,
            correction_strength, regularization, dynamic_range, contrast_boost,
        )
        r = imaging.renderer()
        t0 = time.perf_counter()
        result = r.render(arr, prescription, display, viewing_distance_mm, cal)
        uncorrected = r.simulate_eye_view(arr, prescription, display, viewing_distance_mm,
                                          cal.correction_strength)
        corrected = r.simulate_eye_view(result.image, prescription, display,
                                        viewing_distance_mm, cal.correction_strength)
        ms = int((time.perf_counter() - t0) * 1000)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return DemoPanels(
        original=imaging.png_base64(arr),
        uncorrected=imaging.png_base64(uncorrected),
        precompensated=imaging.png_base64(result.image),
        corrected=imaging.png_base64(corrected),
        blur=_blur_out(result),
        processing_ms=ms,
    )
