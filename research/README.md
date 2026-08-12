# Research

Experiments and notes that keep the prototype honest. See
[`../docs/research-notes.md`](../docs/research-notes.md) for the standing
limitations and validation plan.

## Experiments

- **`experiments/prove_correction.py`** — builds a synthetic eye chart, simulates
  what a myopic/astigmatic eye perceives with correction OFF vs ON, and saves a
  labelled comparison grid to `test-images/comparison.png`. Reports MSE (contrast-
  normalised) and gradient-energy sharpness.

  ```bash
  cd backend && pip install -r requirements.txt
  python ../research/experiments/prove_correction.py
  ```

## Directories

- `experiments/` — runnable scripts.
- `test-images/` — generated / sample images (git-ignored except samples).
- `notebooks/` — Jupyter explorations (empty for now).
