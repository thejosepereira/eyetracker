# VisionCorrect — Standalone (no backend)

**`visioncorrect.html` is a single self-contained file.** Open it in any browser
(double-click, or host it anywhere) and everything runs locally in JavaScript —
the correction, the eye simulation, and the blinded human test. No Python, no
server, works offline, works on a phone.

This is the easiest way to **test on a real human**: put the file on a device,
open it, go.

## Use it

- **Double-click** `visioncorrect.html`, or
- serve the folder (`python -m http.server` then open the file), or
- host the single file on any static host / share it.

Two tabs:

- **Demo** — pick an image, set a prescription, see the four panels
  (original → eye-view-OFF → pre-distorted → eye-view-ON).
- **Human test** — the blinded, 3-condition, letter-identification study
  (A original · B contrast-only control · C full correction). Scores % correct,
  logs reaction time, exports CSV + JSON. Meaningful result: **C − B**.

### `selftest.html` — self-test viewer

A big live view of the pre-distorted image for testing on your own eyes. Change
the prescription per eye, pick content, and flip correction ON/OFF (button or
<kbd>space</kbd>) — glasses off, one eye covered, at the set distance. Toggling is
instant (the corrected frame is cached); changing settings recomputes. Side-by-side
and fullscreen modes included. Works offline (double-click is fine; no camera).

### `distance.html` — distance-adaptive (front camera)

The front camera estimates how far your face is (from iris spacing) and the
correction re-renders live as you lean in/out. A manual slider works with no
camera. **Serve it over localhost/https** (not `file://`) so the browser grants
camera access:

```bash
python -m http.server 8080   # then open http://localhost:8080/distance.html
```

Details and the native-iOS/TrueDepth alternative: `../docs/distance-adaptation.md`.

## What's inside

| File | Role |
|------|------|
| `engine.js` | The vision engine ported to pure JS: FFT, PSF, Wiener pre-compensation, sRGB↔linear, optical model, eye simulation. Source of truth. |
| `app.template.html` | UI + app logic, with a `/*__ENGINE__*/` placeholder. |
| `visioncorrect.html` | **Generated** single file = `engine.js` inlined into the template. This is the one you open. |

## Rebuild after editing

```bash
node -e 'const fs=require("fs");fs.writeFileSync("visioncorrect.html",
  fs.readFileSync("app.template.html","utf8").replace("/*__ENGINE__*/",()=>fs.readFileSync("engine.js","utf8")))'
```

## Fidelity

The JS engine matches the Python `vision_engine` to ~1e-15 (floating-point
round-off) on the Wiener pre-compensation and PSF — verified by
`engine.js` vs `backend/vision_engine`. Same algorithm, same result, just running
in the browser.

## Limitation vs the Python backend

The FFT here is radix-2, so images are internally padded to the next power of two
(with edge replication) and cropped back. For the small letter stimuli and demo
images this is imperceptible. The Python backend has no such constraint.

Same caveats as the whole project apply: experimental, not a medical device, not
a replacement for prescribed eyewear. See `../docs/testing.md` for the protocol.
