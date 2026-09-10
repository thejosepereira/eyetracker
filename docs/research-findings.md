# Research Findings & Model Changes

Three parallel research passes (ocular optics/PSF, accommodation & viewing
geometry, and vision-correcting-display prior art) reviewed the engine against the
vision-science and computational-imaging literature. This file records what they
confirmed, what we changed, and what we deliberately deferred. Sources are listed
per topic in the agents' domains (see also `optical-model.md`).

## Confirmed correct (no change)

- **Blur-circle relation** `β(rad) = pupil(m) × defocus(D)` — correct (Smith 1982;
  β[arcmin] = 3.44·p[mm]·D).
- **Screen projection** `blur_diameter_mm = β × distance_mm` — correct.
- **Disk→Gaussian** `σ = 0.25 × blur_diameter` — correct as the second-moment match
  (a uniform disk of radius R has σ = R/2 = diameter/4).
- **Astigmatism / minus-cylinder** meridian powers `P(φ) = S + C·sin²(φ − axis)`,
  with the elliptical blur's σ-axes aligned to the two principal meridians — our
  rotate-to-axis handling is correct.
- **Monocular, per-eye correction at a fixed distance/pupil** — correct and
  necessary (each eye's PSF differs; the correction assumes one aperture).
- **Contrast reduction before inversion** — matches the literature
  (Alonso-Barreto; Ji/Ye; Montalto).

## Changed (implemented)

1. **Accommodation-aware residual defocus (per meridian).** Was
   `max(0, -S - 1/d)` (myopia-only, and it wrongly returned 0 for all hyperopia).
   Now, with signed meridian power `R` and demand `V = 1/d`:
   `residual = max(0, -(V+R), (V+R) - A_max)` — adds the near-point branch
   (can't-focus-close) and correct hyperopia handling.
2. **Age → accommodation amplitude** (Hofstetter, conservative):
   `A_max = max(0, 15 - 0.25·age)`; ~0 by age 60. Exposed as an input; this is
   what makes presbyopia behave correctly.
3. **Depth-of-focus dead-band.** Subtract `DoF_half ≈ 1.0/pupil_mm` D (≈0.29 D at
   3.5 mm) before declaring visible blur — the eye tolerates small defocus, so we
   no longer pre-distort inside it (stops over-correction near the sweet spot).
4. **Pupil default 4.0 → 3.5 mm** (indoor screen, photopic-mesopic) and it drives
   the DoF dead-band. Still an input.

## Deferred (Phase 2 — bigger algorithm work, offered next)

From the prior-art review, these are the reported quality wins beyond our
Wiener+clip on a single flat panel:

- **Band-limit the target below the first OTF null** (don't invert across a
  zero-crossing) — reported as the single biggest win for a flat screen.
- **Box-constrained deconvolution** (enforce 0–1 inside the solve via
  ADMM/projected gradient) instead of clip-after-linear-inverse.
- **Total-variation regularization** instead of/atop Wiener (better perceived
  contrast at equal sharpness).
- **Luma-only (YUV) deconvolution**; leave chroma untouched.
- **Adaptive contrast squeeze** (minimum needed per image) instead of a fixed 0.55.
- **Per-channel chromatic correction** (defocus offsets ≈ {R +0.4, G 0, B −0.5} D)
  — worth ~0.5 D of residual color blur.
- **Disk/pillbox PSF** for deconvolution fidelity (needs the band-limiting above
  to stay stable; Gaussian remains the stable fallback).

## The honest ceiling (all sources agree)

A **single conventional flat display cannot fully restore vision.** The eye's
defocus OTF has nulls where information is irrecoverably lost, and a screen cannot
emit negative light, so pre-sharpening overshoots are paid for in contrast.
Realistic outcome: **≲1–1.5 D → a legible ~1–2 acuity-line gain with visible
contrast loss; beyond ~2 D it degrades badly.** Full correction is why the MIT/
Berkeley systems use light-field / multilayer hardware. Validation target:
uncorrected defocus costs **~0.2 logMAR (≈2 lines) per diopter** at a 4 mm pupil.

**Practical implication for testing:** validate on **mild prescriptions
(−0.5 to −1.5 D)** first — that is the regime where the physics says it can help.
