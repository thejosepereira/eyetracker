# Research Notes

## Purpose

Track what the prototype does and does **not** establish, so the engineering
roadmap stays honest and future clinical-study design has a paper trail.

## What v0.1 demonstrates

- The pre-compensation math is correct: without display clipping,
  `EyeBlur(Precompensate(I)) ≈ I` (verified in `tests/` and
  `research/experiments/prove_correction.py`).
- On a **conventional display** with limited dynamic range, correction of a large
  blur (e.g. −2.5 D at 35 cm) produces a perceptibly sharper — but lower-contrast
  — image in simulation. Smaller letters that are illegible uncorrected become
  legible corrected.

## What v0.1 does NOT establish

- That the prescription→PSF mapping matches any individual's real eye. It is a
  first-order approximation (see `optical-model.md`).
- Any clinical outcome. Simulation ≠ a human looking at a physical screen.
- That the contrast trade-off is net-beneficial for real reading tasks — that
  needs human measurement.

## Known limitations & open questions

1. **Dynamic range is the ceiling.** Full inversion needs out-of-gamut values a
   normal display can't produce. Light-field / multilayer displays sidestep this;
   for flat panels, contrast reduction is the pragmatic trade.
2. **Accommodation is ignored.** A myope viewing inside their far point sees more
   clearly than the model assumes; the model treats the full sphere as residual
   defocus. A distance-aware, accommodation-aware model is future work.
3. **Single global PSF.** Real blur varies across the field and with eye
   movement. Later: spatially-varying and eye-tracked PSFs.
4. **Ringing vs. sharpness.** Regularisation `K` trades ringing for sharpness;
   the optimal value is user- and content-dependent → calibration.

## Experiment-logging schema (v0.2 target)

```json
{
  "algorithmVersion": "0.1.0",
  "sphere": -2.5, "cylinder": -0.75, "axis": 90,
  "distanceMm": 350,
  "correctionStrength": 1.16, "regularization": 0.018,
  "beforeScore": 4, "afterScore": 6
}
```

Do not interpret these internal scores as clinical evidence.

## Validation plan (future)

```
known uncorrected refractive error
      → controlled viewing distance
      → baseline screen-vision task (smallest readable font, contrast
        sensitivity, reading speed, letter-ID accuracy, subjective clarity)
      → enable VisionCorrect → repeat task → compare
```

## Prior art to review before any IP claim

Vision-correcting displays, computational light-field displays, prescription-aware
rendering, optical aberration pre-compensation, PSF-based prefiltering, AR/VR
vision correction. Consult qualified patent counsel before filing or launch.
