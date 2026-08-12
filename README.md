# VisionCorrect

**Personalized computational rendering for vision-adaptive displays.**

VisionCorrect pre-distorts what's on screen so that a person's own (imperfect)
eye focuses it into a sharp image — without glasses or contacts. Instead of
correcting the *eye*, it applies the mathematical *inverse* of the eye's blur to
the *image*. When the eye then blurs the pre-distorted image, the blur and the
pre-distortion cancel:

```
        EyeBlur( Precompensate(Image) )  ≈  Image
```

> ⚠️ **Experimental R&D prototype — not a medical device.** This is not a
> diagnostic tool and not a replacement for prescribed corrective eyewear. The
> prescription→blur mapping is an experimental approximation, not a clinically
> validated optical model. See [`docs/optical-model.md`](docs/optical-model.md).

---

## Does it actually work?

Yes — and you can prove it without having the prescription yourself, because the
engine can also *simulate* the eye. Run:

```bash
cd backend && pip install -r requirements.txt
python ../research/experiments/prove_correction.py
```

This renders four panels into `research/test-images/comparison.png`:

| # | Panel | What it is |
|---|-------|------------|
| 1 | Original | The sharp image we want you to perceive |
| 2 | Eye view, correction **OFF** | What a −2.5 / −1.0 × 110° eye sees looking at panel 1 (blurry) |
| 3 | Shown on screen | The pre-distorted image (looks odd — full of "halos") |
| 4 | Eye view, correction **ON** | What the same eye sees looking at panel 3 |

Panel 4 is visibly sharper than panel 2 — the smaller letters that are mush in
panel 2 become legible. The cost is contrast: panel 4 is greyer, because a normal
display can't show the negative/over-bright values full inversion needs, so we
trade contrast for sharpness (see *dynamic range* below).

## Both eyes

You can enter a separate prescription for each eye (OD/OS) and choose a mode:
**Right**, **Left**, or **Both (averaged)**. Because a normal screen shows one
image to both eyes, it cannot perfectly pre-distort for two different eyes at
once — *Right*/*Left* (view with one eye) give true clarity, *Both* is a
power-vector-averaged compromise, and perfect per-eye correction needs a per-eye
display (VR/AR). The averaging uses proper dioptric power vectors, not naive
number-averaging. See [`docs/optical-model.md`](docs/optical-model.md#binocular-use).

## No-install option: one self-contained HTML file

Don't want to run a server? Open **[`standalone/visioncorrect.html`](standalone/visioncorrect.html)**
in any browser. The entire engine (FFT-based correction, eye simulation) and the
human test harness run locally in JavaScript — no backend, works offline, works on
a phone. It's numerically identical to the Python engine (verified to ~1e-15).
See [`standalone/README.md`](standalone/README.md).

## Try it in a browser (with the backend)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

The demo page lets you pick a test image (or upload your own), dial in a
prescription, and watch the four panels update live.

## Test it on a real human

Open **`http://localhost:8000/test`** for a blinded, 3-condition letter-ID study
(original vs contrast-only control vs full correction) that exports CSV/JSON. The
meaningful result is *correction beats the contrast-matched control*. Full
protocol and caveats: [`docs/testing.md`](docs/testing.md).

## Distance-adaptive correction (front camera)

Open **`http://localhost:8000/distance`**: the front camera estimates how far your
face is (from iris spacing) and the correction re-renders live as you move. Manual
slider works without a camera. How it works, accuracy, and the native-iOS/TrueDepth
alternative: [`docs/distance-adaptation.md`](docs/distance-adaptation.md).

---

## Repository layout

```
visioncorrect/
├── README.md
├── render.yaml                 # Render.com deployment
├── docs/                       # architecture, optical model, API, research notes
├── backend/
│   ├── app/                    # FastAPI: routes, models, services
│   ├── vision_engine/          # ★ the algorithm (UI-independent, reusable)
│   │   ├── optical_model.py    #   prescription → blur (replaceable interface)
│   │   ├── psf.py              #   point-spread-function kernels
│   │   ├── deconvolution.py    #   Wiener pre-compensation + forward blur
│   │   ├── color.py            #   sRGB ↔ linear light
│   │   ├── calibration.py      #   interactive tuning + A/B staircase
│   │   └── renderer.py         #   full pipeline (the intellectual core)
│   ├── static/                 # browser demo
│   ├── tests/                  # pytest: engine + API
│   ├── requirements.txt
│   └── Dockerfile
├── mobile/                     # React Native / Expo app skeleton
├── research/                   # experiments, test images, notebooks
└── sdk/                        # future reusable-engine SDK
```

The **vision engine is deliberately isolated from the UI** so the same core can
later become a GPU shader, native mobile library, or OEM display stage.

## API

`POST /v1/correct` (multipart) returns the pre-compensated PNG. Pass
`precompensate=false` for the contrast-only control condition.
`POST /v1/demo` returns all four base64 panels for before/after comparison.
`GET  /health` returns service status.
Full contract: [`docs/api.md`](docs/api.md).

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## How the algorithm works (one paragraph)

The eye's blur is modelled as a Point Spread Function (PSF) — an anisotropic,
rotated Gaussian whose size comes from the prescription, pupil size, viewing
distance, and screen pixel density. Pre-compensation is a **regularised (Wiener)
inverse filter** in the frequency domain: `P = IFFT( FFT(I)·conj(H)/(|H|²+K) )`.
Because full inversion pushes pixels outside what a display can show, the target's
**contrast is reduced first** to create headroom — this is the accepted technique
for pre-compensation on conventional (non-light-field) displays. Details:
[`docs/architecture.md`](docs/architecture.md).

## Adaptive ("AI") glasses — concept track

A different mechanism from the screen correction: wearable glasses with a
**physically tunable lens** whose power self-updates as your eyes drift, so you
need far fewer optician visits *for prescription updates* (it does not replace an
eye-health exam). The control software — tunable-lens abstraction, self-refraction,
and distance-based autofocus — lives in
[`backend/vision_engine/adaptive_lens.py`](backend/vision_engine/adaptive_lens.py).

A six-year simulation shows self-refracting glasses keep residual blur under the
noticeable threshold **100% of the time** vs. **54%** for glasses updated only at
2-year visits:

```bash
cd backend && pip install -r requirements.txt matplotlib
python ../research/experiments/adaptive_glasses_sim.py   # writes research/test-images/adaptive_glasses.png
```

Design, lens technologies, and the honest limits: [`docs/adaptive-glasses.md`](docs/adaptive-glasses.md).

## Roadmap

- **v0.1 (this)** — engine, API, browser demo, eye simulation, tests.
- **v0.2** — interactive calibration, separate L/R eyes, better PSF, experiment logging.
- **v0.3** — camera feed, on-device GPU rendering.
- **v0.4** — video, live viewing-distance/eye-tracking, real-time adaptation.
- **v1.0 research target** — measurable improvement on a controlled screen-vision
  task for a defined user group.

## License / IP note

Before treating any algorithm here as proprietary or non-infringing, conduct a
professional patent landscape and freedom-to-operate review — there is
significant prior art in vision-correcting and computational displays.
