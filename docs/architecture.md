# Architecture

## Layers

```
        Mobile app / Web demo         (UI — interchangeable)
                  │  HTTP (multipart image + prescription)
                  ▼
        FastAPI backend               (app/: routes, models, services)
                  │
                  ▼
        Vision Engine                 (vision_engine/ — UI-independent core)
          ├── OpticalModel            prescription → blur description
          ├── PSF generator           blur description → kernel
          ├── Precompensator (Wiener) image + PSF → pre-distorted image
          └── VisionRenderer          orchestrates the full pipeline
```

The **vision engine has no knowledge of HTTP, FastAPI, or React Native.** It
takes numpy arrays and dataclasses in, and returns numpy arrays out. This is the
single most important architectural rule: the engine is the reusable asset and
must be portable to a GPU shader, a native library, or an OS compositor stage.

## Pipeline (`VisionRenderer.render`)

```
INPUT IMAGE (sRGB uint8)
   │
   ├─ linearise RGB (sRGB → linear light)        color.srgb_to_linear
   │
   ├─ optical model → blur params (σx, σy, θ)    OpticalModel.prescription_to_blur
   │
   ├─ generate PSF kernel                        psf.generate_psf_auto
   │
   ├─ reduce target contrast (headroom)          renderer._reduce_contrast
   │
   ├─ Wiener inverse filtering (per channel)     deconvolution.wiener_precompensate
   │
   ├─ contrast management + clip to [0,1]
   │
   └─ gamma re-encode (linear → sRGB)            color.linear_to_srgb
   │
OUTPUT IMAGE (sRGB uint8)
```

Processing happens **per RGB channel in linear light**, never on a permanently
grayscale image. This keeps the door open for wavelength-dependent (R/G/B) PSFs
for chromatic-aberration compensation — the `chromatic` field in
`CalibrationProfile` already scales the PSF per channel.

## Why contrast reduction?

Perfect inversion of a blur requires displaying pixel values below 0 and above 1
(the "halos" you see in the pre-distorted panel). A physical display is clamped
to `[0, 1]`. If we simply clip, the cancellation breaks and the result can look
*worse* than no correction.

The fix used here — and in the vision-correcting-display literature — is to
squeeze the **target** image's contrast toward mid-grey *before* inverting. The
pre-distorted result then stays inside the displayable range, so clipping barely
hurts. The user perceives a sharp but lower-contrast image. The
`dynamic_range` calibration parameter controls this trade-off
(lower = sharper + flatter, higher = more contrast + more residual blur).

## Extension points

| Interface | Replace it with |
|-----------|-----------------|
| `OpticalModel.prescription_to_blur` | measured PSF, wavefront/Zernike model |
| `psf.generate_psf` | disk/defocus kernel, chromatic PSFs |
| `deconvolution.wiener_precompensate` | total-variation / learned inverse filter |
| `VisionRenderer` | GPU (Metal/Vulkan/WebGPU) real-time renderer |
