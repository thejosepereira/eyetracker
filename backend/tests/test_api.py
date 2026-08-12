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
