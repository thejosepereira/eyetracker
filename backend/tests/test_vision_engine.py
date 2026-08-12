import numpy as np
import pytest

from vision_engine import (
    OpticalModel, EyePrescription, DisplayParams, CalibrationProfile, VisionRenderer,
    generate_psf, wiener_precompensate, apply_psf, PairwiseStaircase,
)


# ---- prescription validation ------------------------------------------------

def test_prescription_valid():
    EyePrescription(-2.5, -1.0, 110).validate()  # should not raise


@pytest.mark.parametrize("sph,cyl,axis", [
    (-99, 0, 0),        # sphere out of range
    (-2, -99, 0),       # cylinder out of range
    (-2, -1, 200),      # axis out of range
    (-2, -1, -5),       # negative axis
])
def test_prescription_invalid(sph, cyl, axis):
    with pytest.raises(ValueError):
        EyePrescription(sph, cyl, axis).validate()


# ---- PSF --------------------------------------------------------------------

def test_psf_normalized():
    psf = generate_psf(31, 31, 3.0, 5.0, 45.0)
    assert psf.shape == (31, 31)
    assert psf.sum() == pytest.approx(1.0, abs=1e-9)
    assert (psf >= 0).all()


def test_psf_asymmetric_and_rotation():
    # A 0-degree elongated PSF should be wider along x than y.
    psf = generate_psf(41, 41, 6.0, 2.0, 0.0)
    col_spread = (psf.sum(axis=0) > psf.max() * 0.1).sum()
    row_spread = (psf.sum(axis=1) > psf.max() * 0.1).sum()
    assert col_spread > row_spread
    # Rotating 90 degrees swaps the spread.
    psf90 = generate_psf(41, 41, 6.0, 2.0, 90.0)
    assert (psf90.sum(axis=1) > psf90.max() * 0.1).sum() > \
           (psf90.sum(axis=0) > psf90.max() * 0.1).sum()


def test_psf_degenerate_rejected():
    with pytest.raises(ValueError):
        generate_psf(0, 10, 1, 1, 0)


# ---- deconvolution math -----------------------------------------------------

def test_precompensation_cancels_blur_without_clipping():
    rng = np.random.default_rng(1)
    # Low-contrast, low-frequency-ish target: pre-comp should invert the blur.
    img = rng.random((96, 96)) * 0.4 + 0.3
    psf = generate_psf(21, 21, 2.0, 2.0, 0.0)
    pre = wiener_precompensate(img, psf, regularization=1e-4)
    recovered = apply_psf(pre, psf)
    # Reconvolving the pre-compensated image should approximate the target.
    assert np.mean((recovered - img) ** 2) < np.mean((apply_psf(img, psf) - img) ** 2)


# ---- optical model ----------------------------------------------------------

def test_stronger_prescription_gives_more_blur():
    model = OpticalModel()
    d = DisplayParams(264.0)
    weak = model.prescription_to_blur(EyePrescription(-1.0, 0, 0), 350, d)
    strong = model.prescription_to_blur(EyePrescription(-4.0, 0, 0), 350, d)
    assert strong.sigma_x > weak.sigma_x


def test_astigmatism_makes_blur_anisotropic():
    model = OpticalModel()
    d = DisplayParams(264.0)
    blur = model.prescription_to_blur(EyePrescription(-2.0, -2.0, 90), 350, d)
    assert abs(blur.sigma_x - blur.sigma_y) > 1e-3
    assert blur.angle_degrees == 90


# ---- renderer output --------------------------------------------------------

def test_render_output_dimensions_and_dtype():
    renderer = VisionRenderer()
    img = (np.random.default_rng(2).random((64, 80, 3)) * 255).astype(np.uint8)
    result = renderer.render(
        img, EyePrescription(-2.0, -0.5, 90), DisplayParams(264.0), 350.0,
        CalibrationProfile())
    assert result.image.shape == (64, 80, 3)
    assert result.image.dtype == np.uint8
    assert 0 <= result.image.min() and result.image.max() <= 255


def test_render_accepts_grayscale():
    renderer = VisionRenderer()
    img = (np.random.default_rng(3).random((32, 32)) * 255).astype(np.uint8)
    result = renderer.render(
        img, EyePrescription(-1.0), DisplayParams(264.0), 350.0)
    assert result.image.shape == (32, 32, 3)


# ---- calibration staircase --------------------------------------------------

def test_staircase_converges():
    s = PairwiseStaircase(center=1.0, step=0.4)
    guard = 0
    while not s.converged and guard < 50:
        lo, hi = s.candidates()
        s.choose(hi)  # always prefer stronger
        guard += 1
    assert s.converged
    assert s.center > 1.0
