"""Proof-of-concept experiment: does pre-compensation actually help?

We build a synthetic eye chart, then compare what a myopic/astigmatic eye
perceives in two conditions:

    (A) looking at the ORIGINAL image           -> EyeBlur(Image)
    (B) looking at the PRE-COMPENSATED image     -> EyeBlur(P(Image))

If the engine works, (B) should be measurably closer to the original sharp
image than (A). We report MSE against the ideal and a gradient-energy
"sharpness" score, and save a labelled comparison grid.

Run:  python research/experiments/prove_correction.py
"""

from __future__ import annotations

import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from vision_engine import (  # noqa: E402
    OpticalModel, EyePrescription, DisplayParams, CalibrationProfile, VisionRenderer,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "test-images")
os.makedirs(OUT_DIR, exist_ok=True)


def make_eye_chart(w=512, h=512) -> np.ndarray:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    rows = [("E", 120), ("F P", 78), ("T O Z", 54), ("L P E D", 40), ("P E C F D", 30)]
    y = 24
    for text, size in rows:
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            font = ImageFont.load_default()
        bbox = d.textbbox((0, 0), text, font=font)
        d.text(((w - (bbox[2] - bbox[0])) / 2, y), text, fill=(0, 0, 0), font=font)
        y += size + 22
    # A few fine lines to expose high-frequency behaviour.
    for i, x in enumerate(range(40, w - 40, 10)):
        d.line([(x, h - 70), (x, h - 30)], fill=(0, 0, 0), width=1 + (i % 2))
    return np.asarray(img, dtype=np.uint8)


def _stretch(x: np.ndarray) -> np.ndarray:
    """Contrast-normalise to [0,1] so we compare structure, not global contrast."""
    x = x.astype(np.float64)
    lo, hi = np.percentile(x, 1), np.percentile(x, 99)
    if hi - lo < 1e-6:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0, 1)


def mse(a: np.ndarray, b: np.ndarray) -> float:
    # Compare structure after normalising contrast (correction trades contrast
    # for sharpness by design, so a raw MSE would unfairly penalise it).
    return float(np.mean((_stretch(a) - _stretch(b)) ** 2)) * 255 ** 2


def sharpness(img: np.ndarray) -> float:
    g = img.astype(np.float64).mean(axis=2)
    gx = np.diff(g, axis=1)
    gy = np.diff(g, axis=0)
    return float(np.mean(gx ** 2) + np.mean(gy ** 2))


def label(img: np.ndarray, text: str) -> Image.Image:
    im = Image.fromarray(img).copy()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 26], fill=(20, 20, 20))
    d.text((8, 6), text, fill=(255, 255, 255))
    return im


def main() -> None:
    original = make_eye_chart()

    prescription = EyePrescription(sphere=-2.5, cylinder=-1.0, axis=110)
    display = DisplayParams(pixels_per_inch=264.0)
    distance_mm = 350.0
    cal = CalibrationProfile(correction_strength=1.0, regularization=0.012, contrast_boost=1.0)

    renderer = VisionRenderer(OpticalModel())

    # (A) uncorrected: what the eye sees looking at the original.
    seen_uncorrected = renderer.simulate_eye_view(
        original, prescription, display, distance_mm)

    # Pre-compensated image (what we would actually display).
    corrected = renderer.render(original, prescription, display, distance_mm, cal)
    precompensated = corrected.image

    # (B) corrected: what the eye sees looking at the pre-compensated image.
    seen_corrected = renderer.simulate_eye_view(
        precompensated, prescription, display, distance_mm)

    mse_a = mse(seen_uncorrected, original)
    mse_b = mse(seen_corrected, original)
    print(f"estimated blur (px):   sigma_x={corrected.blur.sigma_x:.2f} "
          f"sigma_y={corrected.blur.sigma_y:.2f} angle={corrected.blur.angle_degrees:.0f} deg")
    print(f"PSF kernel:            {corrected.psf_shape}")
    print(f"clipped fraction:      {corrected.clipped_fraction*100:.1f}%")
    print()
    print(f"MSE vs sharp  (A) uncorrected eye view : {mse_a:9.1f}")
    print(f"MSE vs sharp  (B) corrected  eye view  : {mse_b:9.1f}")
    improvement = (mse_a - mse_b) / mse_a * 100 if mse_a else 0.0
    print(f"MSE reduction from correction          : {improvement:6.1f}%")
    print()
    print(f"sharpness original                     : {sharpness(original):9.1f}")
    print(f"sharpness (A) uncorrected eye view     : {sharpness(seen_uncorrected):9.1f}")
    print(f"sharpness (B) corrected  eye view      : {sharpness(seen_corrected):9.1f}")

    # Assemble a 2x2 labelled comparison grid.
    tiles = [
        label(original, "1. Original (ideal / what we want you to see)"),
        label(seen_uncorrected, "2. What your eye sees NOW (correction OFF)"),
        label(precompensated, "3. Pre-distorted image shown on screen (looks weird!)"),
        label(seen_corrected, "4. What your eye sees with VisionCorrect ON"),
    ]
    tw, th = tiles[0].size
    grid = Image.new("RGB", (tw * 2 + 12, th * 2 + 12), (60, 60, 60))
    for i, t in enumerate(tiles):
        x = (i % 2) * (tw + 12)
        y = (i // 2) * (th + 12)
        grid.paste(t, (x, y))
    out_path = os.path.join(OUT_DIR, "comparison.png")
    grid.save(out_path)
    Image.fromarray(precompensated).save(os.path.join(OUT_DIR, "precompensated.png"))
    print(f"\nSaved comparison grid -> {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
