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

## Phase 2 — implemented (high-quality deconvolution path)

Added a selectable **TV + box-constrained** algorithm alongside Wiener (engine:
`tvPrecompensate` / `tv_precompensate`; render `method:"tv"`; selector in the Lab):

- **Box-constrained deconvolution** — projected gradient solving
  `min_p ‖H·p − target‖² + λ·TV(p)` s.t. `0 ≤ p ≤ 1`. The display range is enforced
  *inside* the solve, so ringing is controlled by TV instead of by clipping a
  linear inverse afterward.
- **Total-variation regularization** — edge-preserving, replaces the L2/Wiener
  penalty on the HQ path.
- **Luma-only** — one solve on linear luminance; chroma passes through (≈3× cheaper
  for colour, avoids colour ringing).
- **Adaptive contrast** — the box constraint allocates headroom per image, so no
  fixed pre-squeeze is required beyond the optional `dynamicRange` bias.

**Empirical outcome (honest).** Benchmarked Wiener+clip vs TV on our own metrics
(contrast-normalised perceived sharpness + a background-ringing measure), luma bars/text:

| Regime | Wiener | TV | Takeaway |
|---|---|---|---|
| Mild blur (σ≲1 px) | already near-ideal | ~equal, slightly softer | little to gain |
| Strong blur (σ 5–8 px) | sharp ~3–6% | sharp ~3–6% | **both hit the physical ceiling** |
| Clipping (display-range use) | 8–27% clipped | **1–15% clipped** | TV's real, consistent win |

So TV is a *principled refinement* — it uses the display's range better (less
clipping) and controls ringing inside the solve — **not** a sharpness miracle. On a
smooth (Gaussian) OTF, Wiener is already close to optimal, and neither algorithm
beats the single-flat-screen ceiling at high blur. TV is exposed as an optional
"HQ (slower)" mode; Wiener stays the fast default for live/interactive pages.

## Phase 2 study — the decisive finding: use the DISK PSF

A full simulation sweep (`research/experiments/phase2_study.js`, chart
`research/test-images/phase2_study.png`, montage `phase2_montage.png`) pitted five
algorithms against a **physically-correct disk-blur eye** across prescriptions
(−1 to −3 D) and distances (50–90 cm), scored by contrast-normalised perceived
legibility (Pearson correlation to the sharp target).

**Result: the PSF *model* matters more than the deconvolution algorithm.**

| Config | −3 D @ 70 cm (σ≈4.3px) | vs OFF 0.35 |
|---|---|---|
| correction OFF | 0.35 | — |
| Wiener · **Gaussian** (old default) | 0.33 | **worse** |
| TV · Gaussian | 0.37 | +0.02 |
| **Wiener · DISK (matched)** | **0.59** | **+0.24** |
| TV · disk | 0.54 | +0.19 |
| TV · disk · band-limited | 0.45 | +0.10 |

The disk (pillbox) PSF is what a defocused eye *actually* produces; the Gaussian
we shipped first was the wrong model, which is why it barely helped and sometimes
hurt. With the matched disk PSF, **Wiener wins** and gives real gains across the
whole range (and beyond σ≈1px where Gaussian collapses toward/under OFF).

**Robustness (how accurate must calibration be?)** For the −3 D case, the disk
correction is robust to a **±15%** error in assumed blur (legibility 0.51–0.59)
but drops *below* OFF beyond **±30%**. So per-user calibration of the blur
(distance, PPI, pupil, prescription) is **essential** — this is exactly what the
"Dial to Clear" flow pins down. Wrong sigma is worse than no correction.

**Implemented:** disk PSF is now the **default** (`psfType:"disk"`) for both the
correction and the eye simulation in the JS and Python engines; `bandlimit` and
`psfType` are exposed (Lab has selectors). Band-limiting trades a little legibility
for less ringing/contrast cost — left optional.

**Honest caveat:** the study assumes the eye is an ideal disk and the correction
knows sigma exactly (matched). Real eyes soften the disk (diffraction, higher-order
aberrations) and we only know sigma approximately — so real-world results sit
between the pessimistic Gaussian curve and this matched-disk curve. That gap is
what real-eye data (Dial/Lab) will close.

## Calibration knob for real eyes: `softness`

A real eye is not an ideal hard disk — diffraction and higher-order aberrations
round its edge. Added a one-parameter **`softness`** (px) that convolves the disk
PSF with a Gaussian: `softness=0` = hard disk, larger = progressively softer,
approaching a Gaussian blob. Exposed in the engine (`buildPsf`/`_build_psf`) and as
a **Lab slider**. This is the single knob to tune once we have real-eye data: match
the model's `softness` (and confirm sigma) to what real eyes report through the
Dial/Lab, then the correction uses that calibrated PSF.

## Still deferred (largest remaining, but limited by the ceiling)

- **Band-limit the target below the first OTF null** and the **disk/pillbox PSF** —
  these go together (the disk PSF is physically correct and *has* nulls; the
  Gaussian we use has none, which is why Wiener is already stable on it). Expected
  to matter most where the disk-null problem bites; the flat-screen ceiling caps
  the payoff.
- **Per-channel chromatic correction** (defocus offsets ≈ {R +0.4, G 0, B −0.5} D).

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
