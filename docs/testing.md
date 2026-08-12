# Testing on a Real Human

Everything else only proves the math against our own blur model. A real eye's
Point Spread Function differs from the model, so **a human test is the only real
validation.** This document describes the protocol and the built-in harness.

> Not a medical device. Informed consent, no safety-critical use, no diagnostic
> claims. Anything beyond informal friends-and-family testing needs ethics/IRB
> review and a vision-care professional.

## The built-in harness

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --port 8000
# open http://localhost:8000/test
```

It runs a **blinded, 3-condition, letter-identification study** and exports the
results as CSV and JSON.

### The three conditions (why there are three, not two)

The correction *reduces contrast* to buy sharpness. If you only compare
"correction ON" vs "original", any improvement could just be the contrast change.
So each trial randomly shows one of:

| | Condition | What it is |
|---|-----------|------------|
| **A** | Original | the letter, unmodified |
| **B** | Contrast-reduced only | same contrast reduction as C, **no** pre-distortion (the control) |
| **C** | Full correction | contrast reduction **+** pre-distortion |

The meaningful result is **C − B**. If C beats B, the pre-distortion itself is
doing the work. C beating only A is not enough.

Backend support: `POST /v1/correct` takes `precompensate` (true/false) and
`dynamic_range`, so the three conditions are:

- A → `precompensate=false`, `dynamic_range=1.0`
- B → `precompensate=false`, `dynamic_range=<DR>`
- C → `precompensate=true`,  `dynamic_range=<DR>`

### Protocol enforced by the harness

- **Glasses/contacts off** — the eye must supply the real blur.
- **Monocular** — cover the untested eye; run each eye separately with its own
  prescription (the correction is eye-specific).
- **Fixed distance + real PPI** — entered at setup; the blur model needs both.
- **Blinded** — conditions are shuffled and never shown during the run.
- **Randomised Sloan letters** (C D H K N O R S V Z) each trial — no memorising.
- **Objective scoring** — % correct letter identification; reaction time logged too.

### Calibrating difficulty

Use the *Letter box (px)* control so uncorrected (condition A) accuracy lands
around **50–70%**. Too easy (ceiling) or too hard (floor) leaves no room to
detect a difference.

### Output

CSV (one row per trial) and JSON (config + trials) using the experiment schema
from the spec, e.g.:

```json
{ "algorithmVersion": "0.1.0", "sphere": -2.5, "cylinder": -1.0, "axis": 110,
  "config": { "distanceCm": 35, "ppi": 264, "cs": 1.0, "dr": 0.55, "reg": 0.012 },
  "trials": [ { "trial": 1, "condition": "C", "target": "K", "response": "K",
               "correct": 1, "rt_ms": 1840 } ] }
```

## A 10-minute self-test (n = 1)

Glasses off, one eye covered, phone at a fixed distance, open `/test`, enter your
prescription, run ~15 trials/condition. Not evidence — but a fast sanity check.

## Toward real evidence

- **Repeat** across both eyes, multiple sessions, and several subjects.
- **Analyse properly** — per-condition accuracy with confidence intervals; a
  paired test on C vs B across subjects. Don't over-read one session.
- **Pre-register** the hypothesis and letter-box/difficulty before collecting, to
  avoid tuning until it looks good.
- **Involve a professional** — optometrist / vision scientist — before any claim.

See `docs/research-notes.md` for standing limitations (dynamic-range ceiling,
accommodation, single global PSF).
