# Distance-Adaptive Correction

The correction the eye needs depends on how far the screen is. If we can measure
that distance live, we can retarget the blur as the user moves — spec section 22
("Viewing-Distance and Eye-Position Adaptation").

## Try it

```bash
cd backend && uvicorn app.main:app --port 8000
# open http://localhost:8000/distance   (localhost is a secure context, so the camera works)
```

Also `standalone/distance.html` (single file). Note: browsers only grant camera
access on **https or localhost** (not `file://`), so serve it rather than
double-clicking. A **manual distance slider** works with no camera at all.

## How distance is estimated

Two paths — the demo uses the second:

1. **TrueDepth IR (native iOS/iPadOS).** ARKit's `ARFaceAnchor` returns the
   face's position in metres straight from the FaceID depth sensor: ~cm accuracy,
   60 Hz, plus head pose and eye transforms. This is the "infrared camera" path.
   Requires a native app — a browser cannot reach the IR sensor.

2. **Front RGB camera + iris tracking (cross-platform, used here).** MediaPipe
   FaceMesh (with `refineLandmarks`) gives iris centres. The human iris is
   ~11.7 mm wide and inter-pupillary distance ~63 mm with low variance, so:

   ```
   distance_mm ≈ focal_px · IPD_mm / ipd_pixels
   ```

   `focal_px` is unknown per webcam, so we seed it from an assumed 60° field of
   view and refine with a **one-point calibration** (hold at a known distance,
   tap calibrate → `scaleK = known_mm · ipd_px`, then `distance = scaleK/ipd_px`).
   Good to roughly a centimetre. Works on Android and in-browser too — no IR
   required.

## The real bottleneck: re-rendering, not sensing

Measuring distance at 30 Hz is trivial. Re-running the FFT deconvolution per
frame is not. The demo keeps it cheap by only re-rendering when distance changes
past a threshold (~1.5 cm) and debouncing. Production options:

- **Precomputed kernel bank** — one PSF/filter per distance bucket, snap to nearest.
- **GPU deconvolution** (WebGPU / Metal / Vulkan) for true per-frame real-time.
- Because head motion is slow, threshold + debounce already feels live.

## A better physics model this unlocks

The current engine treats `sphere` as a fixed blur and scales it by distance.
With a live distance signal we can use the physically correct relationship: an
uncorrected eye is sharp at its **far point** (= 1 / dioptric error) and blurs as
the screen departs from it:

```
defocus(distance) = | 1/distance − 1/far_point |     (bounded by accommodation)
```

This is more accurate than the fixed-blur approximation and is only possible once
distance is known. It is a natural next step (see `optical-model.md`).

## Privacy

Camera frames, face mesh, and depth stay **on-device** and are never uploaded.
That is both correct and a differentiator versus any cloud approach.
