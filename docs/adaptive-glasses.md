# Adaptive ("AI") Glasses

A concept track: wearable glasses whose **lens power changes on command**, so the
prescription tracks the wearer's eyes over time — far fewer trips to the optician
just to update numbers.

> **Different mechanism from the screen correction.** The rest of this project
> pre-distorts a *known image on a screen* (deconvolution). Glasses see the *real
> world*; you cannot software-pre-distort arbitrary incoming light. Adaptive
> glasses need a **physically tunable lens** plus sensing and control software.
> This module (`vision_engine/adaptive_lens.py`) is that control side.

> **Corrects blur only — not an eye exam.** Auto-refraction tracks *refractive*
> error. It does **not** check eye pressure (glaucoma), the retina, or eye health.
> The honest claim is "fewer visits for prescription updates," not "never see an
> eye doctor." Experimental; not a medical device.

## Architecture

```
   ┌─────────── sensing ───────────┐        ┌──── control ────┐      ┌── actuation ──┐
   self-refraction (clarity/​wavefront)  →   AdaptiveController  →     TunableLens  →  lens
   distance / gaze (depth, eye track) →        (target power)          (clamp+quantise)  driver
```

- **`SelfRefraction`** — estimates the sphere that maximises clarity, at clinical
  0.25 D resolution (coarse staircase → fine refine). On a device the "clarity
  oracle" is the wearer's response to A/B choices, or an on-board wavefront/
  autorefractor reading. Run it periodically → the Rx self-updates as eyes drift.
- **`near_add_d` / `max_accommodation_d`** — the *autofocals* piece: from the
  viewing distance and the wearer's remaining accommodation, compute the extra
  plus power needed for near work. This is what presbyopes lose; the lens restores
  it, adjusting as you look near vs. far.
- **`AdaptiveController`** — combines the tracked distance Rx with the distance-
  based near-add into one target, then asks the lens what it can actually do.
- **`TunableLens` / `LensSpec`** — hardware abstraction: clamps and quantises the
  target to a real device's limits. Swap the backend for the chosen technology.

## Tunable-lens technologies (illustrative envelopes in `LENS_SPECS`)

The control software only emits a **target power** — it is lens-agnostic, so any
backend below plugs in behind `TunableLens`. That includes several **no-liquid**
options (`medium == "solid"`, listed in `SOLID_STATE_LENSES`).

| Backend | Principle | Liquid? | Range* | Cylinder | Maturity | Notes |
|---------|-----------|---------|--------|----------|----------|-------|
| `fluidic` | membrane/electrowetting shape change | liquid | ±8 D | no | product | wide range; bulk |
| `lc` | liquid-crystal index vs. voltage | liquid-crystal | ±3 D | yes | emerging | fast, low power; limited range |
| `alvarez` | two sliding **solid** freeform plates | **solid** | −6…+4 D | no | product | mature no-liquid path; needs a small slide actuator |
| `deformable` | bend a **solid** polymer element | **solid** | ±4 D | no | emerging | middle ground; mechanical |
| `metasurface` | flat nanostructured "hologram" optic | **solid** | ±3 D | yes | research | ultra-thin & flat; can encode astigmatism; full-colour eyeglass-size is unsolved |
| `electro_optic` | **solid** ceramic (PLZT) index vs. voltage | **solid** | ±2 D | no | research | truly solid-state, voltage-driven; high V, small aperture today |

\* Approximate and illustrative — **not** vendor specifications. Real prior art:
Optotune & Varioptic (fluidic), Deep Optics / 32°N (LC), Adlens/Eyejusters
(Alvarez, manual today), metalens research (Capasso group and others), and
Stanford's *autofocals* research prototype.

### "No liquid" options, ranked by how real they are today

1. **Alvarez (solid plates)** — the practical no-liquid choice now: solid, cheap,
   wide range, good optics. Trade-off: a tiny motor slides the plates.
2. **Deformable solid** — bendable polymer; simpler motion, narrower range.
3. **Metasurface / holographic (flat)** — the "like a hologram" answer: a flat
   patterned-glass lens. Thin and elegant, and uniquely able to encode arbitrary
   wavefronts (astigmatism included) — but eyeglass-sized, full-colour, tunable
   versions are still lab-stage (efficiency and chromatic aberration are the hard
   parts).
4. **Electro-optic ceramic** — solid and purely electrically driven, but limited
   aperture/voltage today.

**Device range matters.** The simulation below reaches −3.26 D, which an LC lens
(±3 D) cannot deliver — it would saturate and blur. Pick a lens whose range covers
the expected prescription.

## Does the "fewer visits" idea hold up?

`research/experiments/adaptive_glasses_sim.py` simulates a myope drifting from
−2.00 D to −3.26 D over six years and compares residual blur under two regimes:

| | mean residual defocus | worst | time noticeably blurred (>0.25 D) |
|---|---|---|---|
| Static glasses, updated every 24 months | **0.25 D** | 0.71 D | **46%** |
| Adaptive glasses, self-refract monthly | **0.05 D** | 0.17 D | **0%** |

Static glasses go stale between visits; adaptive glasses stay continuously
in-prescription. (Chart: `research/test-images/adaptive_glasses.png`.)

## Where "AI" actually adds value

- **Continuous self-refraction** without a clinic — the core enabler.
- **Context/gaze-aware focus** (near vs. far) from depth + eye tracking.
- **Personalisation** — learn preferred correction (some people prefer slight
  under-correction), adapt to lighting/pupil size.
- **Drift detection** — flag when change is fast or unusual and *recommend a real
  exam* (the safety valve).

## Open engineering problems

- Cylinder (astigmatism) on a tunable lens is hard; LC can do some, fluidic can't.
- Power, weight, switching speed, optical quality across the field.
- Trustworthy on-device refraction (avoid accommodative spasm fooling it).
- Fail-safe behaviour and regulatory clearance (this is a medical device).

## What carries over from the screen engine

`OpticalModel` (Rx → defocus), the calibration staircase, and the far-point model
are shared vocabulary. The difference is the **output**: a target *lens power*, not
a pre-distorted image.
