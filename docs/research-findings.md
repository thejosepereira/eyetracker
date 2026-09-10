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
