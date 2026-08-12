import io
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _png_bytes(w=48, h=48) -> bytes:
    arr = (np.random.default_rng(0).random((h, w, 3)) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "VisionCorrect API"


def test_correct_returns_png():
    r = client.post(
        "/v1/correct",
        data={"sphere": "-2.5", "cylinder": "-1.0", "axis": "110"},
        files={"image": ("in.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    Image.open(io.BytesIO(r.content)).verify()  # valid PNG


def test_correct_json_mode():
    r = client.post(
        "/v1/correct?response=json",
        data={"sphere": "-2.0"},
        files={"image": ("in.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["output_base64"].startswith("data:image/png;base64,")
    assert body["blur"]["psf_width"] > 0


def test_demo_returns_four_panels():
    r = client.post(
        "/v1/demo",
        data={"sphere": "-2.5", "cylinder": "-1.0", "axis": "110"},
        files={"image": ("in.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("original", "uncorrected", "precompensated", "corrected"):
        assert body[key].startswith("data:image/png;base64,")


def test_control_condition_skips_precompensation():
    # precompensate=false should produce a *different* image than precompensate=true
    # (the control condition B for the human test harness).
    img = _png_bytes(160, 160)
    common = {"sphere": "-2.5", "cylinder": "-1.0", "axis": "110", "dynamic_range": "0.55"}
    corrected = client.post(
        "/v1/correct", data={**common, "precompensate": "true"},
        files={"image": ("in.png", img, "image/png")}).content
    control = client.post(
        "/v1/correct", data={**common, "precompensate": "false"},
        files={"image": ("in.png", img, "image/png")}).content
    assert corrected != control


def test_test_harness_served():
    r = client.get("/test")
    assert r.status_code == 200
    assert "Human Test Harness" in r.text


def test_distance_page_served():
    r = client.get("/distance")
    assert r.status_code == 200
    assert "distance-adaptive" in r.text


def test_selftest_page_served():
    r = client.get("/selftest")
    assert r.status_code == 200
    assert "Self-test" in r.text


def test_invalid_image_rejected():
    r = client.post(
        "/v1/correct",
        data={"sphere": "-2.0"},
        files={"image": ("in.png", b"not-an-image", "image/png")},
    )
    assert r.status_code == 400


def test_invalid_prescription_rejected():
    r = client.post(
        "/v1/correct",
        data={"sphere": "-999"},
        files={"image": ("in.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 422


def test_missing_required_field():
    r = client.post(
        "/v1/correct",
        files={"image": ("in.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 422  # sphere is required
