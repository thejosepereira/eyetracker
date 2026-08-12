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

### 1. Defocus → angular blur

A defocused eye images a point as a **blur circle** on the retina. Its angular
diameter is approximately:

```
    β (radians) ≈ pupil_diameter (m) × | power_error (dioptres) |
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
