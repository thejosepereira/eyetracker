# Optical Model & Scientific Boundary

## The honest disclaimer first

An eyeglass prescription (Sphere / Cylinder / Axis) **does not fully characterise
the optical Point Spread Function (PSF) of a real eye.** A complete model would
also need:

- pupil diameter (changes the blur-circle size and depth of field)
- viewing distance and accommodation (how much the lens is focusing)
- screen pixel density and physical size
- viewing angle
- higher-order aberrations (coma, spherical aberration, …)
- chromatic aberration
- tear film and intraocular scatter
- eye movement / microsaccades

**The mapping in `optical_model.py` is an experimental approximation and must not
be presented as clinically validated.** It exists to make a testable prototype,
and it is isolated behind a small interface so it can be replaced wholesale as
the research improves.

## The approximation we use (v0.1)

> **Updated after a literature review** (see [`research-findings.md`](research-findings.md)):
> the model is now accommodation-aware (handles myopia, hyperopia, and presbyopia),
> subtracts a depth-of-focus dead-band, and defaults to a 3.5 mm pupil. The
> far-point description below is the myopia special case of that model.

### 1. Defocus → angular blur (far-point / accommodation model)

The **residual defocus** actually experienced depends on distance. A relaxed
myopic eye of power `S` (negative) is in focus at its **far point** (distance
`-1/S`) and blurs only for objects *beyond* it; accommodation keeps nearer
objects sharp:

```
    residual_defocus(d) = max(0, -S - 1/d_metres)     [dioptres]
```

So a −2.5 D eye is **sharp at ~40 cm** (its far point), blurs progressively
farther away, and the blur stays **bounded** instead of growing without limit
with distance (an earlier version scaled blur by the full `|S|` at every
distance, which over-blurred far viewing). An emmetrope (`S=0`) gets ~0 at any
distance it can accommodate to.

A defocused eye then images a point as a **blur circle** on the retina, of
angular diameter:

```
    β (radians) ≈ pupil_diameter (m) × residual_defocus (dioptres)
```

### 2. Astigmatism → elliptical blur

For a spherocylindrical prescription the dioptric error depends on the meridian:

```
    power along the axis meridian        = | Sphere |
    power along the perpendicular meridian = | Sphere + Cylinder |   (minus-cyl convention)
```

Two different powers → two different blur diameters → an **elliptical** (rotated)
blur oriented with the prescription's `axis`.

### 3. Angle → pixels

The angular blur is projected onto the screen at the viewing distance and
converted to pixels using the display pixel pitch:

```
    blur_diameter_mm  = β × viewing_distance_mm         (small-angle)
    pixel_pitch_mm    = 25.4 / pixels_per_inch
    blur_diameter_px  = blur_diameter_mm / pixel_pitch_mm
```

### 4. Blur circle → Gaussian σ

A uniform disk of diameter `d` has an equivalent Gaussian `σ ≈ d/4`. We use
`σ = sigma_per_diameter × d` (default `0.25`), with a small floor so the PSF is
never degenerate.

## Worked example

`Sphere −2.5, Cylinder −1.0, Axis 110°`, pupil 4 mm, distance 350 mm, 264 PPI:

- axis meridian: `β = 0.004 × 2.5 = 0.010 rad` → `3.50 mm` → `σx ≈ 9.1 px`
- perp meridian: `β = 0.004 × 3.5 = 0.014 rad` → `4.90 mm` → `σy ≈ 12.7 px`

This is a **large** blur, near the limit of what a conventional display can
recover — which is exactly why contrast reduction (see `architecture.md`) is
necessary and why the perceived result is sharper but lower-contrast.

## Binocular use

A conventional 2-D screen shows a **single image to both eyes**, but the two eyes
usually need different corrections. You cannot pre-distort one shared image to be
simultaneously correct for two different prescriptions. So the engine resolves a
two-eye profile into one prescription per a mode:

- **Right / Left** — correct for that eye; view with the other eye covered. The
  only way to get a *truly* sharp image on a normal screen.
- **Both (averaged)** — a compromise for both-eyes-open viewing. The average is
  computed in **dioptric power-vector space** (M, J0, J45), not by naively
  averaging sphere/cylinder/axis (which is wrong for oblique axes):

  ```
  M   = S + C/2
  J0  = -(C/2)·cos(2·axis)
  J45 = -(C/2)·sin(2·axis)
  ```

  Average each across the eyes, then convert back:
  `C = -2·√(J0²+J45²)`, `S = M - C/2`, `axis = ½·atan2(J45, J0)`.
  Implemented as `averagePrescriptions()` / `resolveRx()` in the engine.

- **Perfect per-eye** — requires each eye to see its own image: a VR/AR headset
  (one display per eye) or a light-field / autostereoscopic display. This is why
  AR/VR is a natural target for the technology.

## What "stronger inputs" would look like

The architecture is meant to accept progressively better characterisations:

1. Prescription values (this version)
2. Interactive user calibration (A/B staircase — partially implemented)
3. Measured point-spread functions
4. Wavefront aberrometry (Zernike coefficients)
5. Eye tracking + continuous viewing-distance estimation
6. Machine-learning-assisted per-user optimisation

Do **not** interpret internal prototype scores as clinical evidence. A real claim
requires a properly designed study with qualified vision-science and clinical
professionals.
