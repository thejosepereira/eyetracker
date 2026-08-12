"""Multi-year simulation: adaptive glasses vs. static glasses updated at visits.

Question: if a person's prescription drifts over years, how much better off are they
with self-refracting adaptive glasses than with normal glasses they only update at
periodic doctor visits?

We model a realistic-ish drift, then compare the *residual defocus* (the blur they
actually experience, in dioptres) under two regimes:

  A. Static glasses, updated to the true Rx only at each doctor visit (e.g. every
     24 months); the Rx goes stale in between as the eye keeps drifting.
  B. Adaptive glasses that self-refract monthly and retune a tunable lens
     (quantised/clamped to the device's real limits).

Residual defocus maps directly to blur and lost acuity, so lower is better.
A residual of ~0.25 D is roughly the threshold of noticeable blur.

Run:  python research/experiments/adaptive_glasses_sim.py
"""

from __future__ import annotations

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from vision_engine import TunableLens, SelfRefraction, LENS_SPECS  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "test-images")
os.makedirs(OUT, exist_ok=True)


def true_rx(month: int) -> float:
    """A plausible sphere trajectory over ~6 years (dioptres).

    Starts at -2.00, myopia progresses ~-0.4 D/yr for 3 years then stabilises,
    with small seasonal wobble. Deterministic (seeded) so runs are reproducible.
    """
    yr = month / 12.0
    progression = -0.4 * min(yr, 3.0)
    wobble = 0.06 * np.sin(month / 3.0)
    return -2.00 + progression + wobble


def self_refract(true_power: float, rng: np.random.Generator) -> float:
    """Simulate an on-device self-refraction: find the correction that maximises
    clarity. Clarity peaks when applied power cancels the true error; add small
    response noise so it isn't a cheat."""
    noise = rng.normal(0, 0.03)
    oracle = lambda p: -abs(p - true_power) + noise * np.sin(p)  # unimodal peak at true_power
    return SelfRefraction(resolution_d=0.25).measure(oracle)


def main() -> None:
    rng = np.random.default_rng(42)
    months = np.arange(0, 72)
    true = np.array([true_rx(m) for m in months])

    # --- A. static glasses, updated every VISIT_EVERY months ---
    VISIT_EVERY = 24
    static_applied = np.empty_like(true)
    last_rx = true[0]
    for i, m in enumerate(months):
        if m % VISIT_EVERY == 0:
            last_rx = round(true[i] / 0.25) * 0.25  # measured at the visit
        static_applied[i] = last_rx
    static_resid = np.abs(true - static_applied)

    # --- B. adaptive glasses, self-refract monthly, drive a tunable lens ---
    # Use a wide-range (fluidic) lens: this myope drifts past -3.26 D, which a
    # liquid-crystal lens (+/-3 D) could not reach. Device range must cover the
    # expected prescription -- an LC lens would saturate and blur here.
    lens = TunableLens("fluidic")
    lc_saturates = min(true) < LENS_SPECS["lc"].min_sphere_d
    adapt_applied = np.empty_like(true)
    for i in range(len(months)):
        est = self_refract(true[i], rng)          # monthly self-measurement
        cmd = lens.command(est)                    # quantise + clamp to device
        adapt_applied[i] = cmd.sphere_d
    adapt_resid = np.abs(true - adapt_applied)

    # --- report ---
    print(f"true Rx: {true[0]:+.2f} D -> {true[-1]:+.2f} D over {len(months)} months")
    print(f"doctor visits (static): every {VISIT_EVERY} months "
          f"= {len(months)//VISIT_EVERY} updates")
    print(f"self-refractions (adaptive): monthly = {len(months)} updates")
    print()
    print(f"mean residual defocus  static  : {static_resid.mean():.3f} D "
          f"(worst {static_resid.max():.2f} D)")
    print(f"mean residual defocus  adaptive: {adapt_resid.mean():.3f} D "
          f"(worst {adapt_resid.max():.2f} D)")
    frac = np.mean(static_resid > 0.25) * 100
    print(f"time the static wearer spends noticeably blurred (>0.25 D): {frac:.0f}%")
    print(f"time the adaptive wearer spends noticeably blurred (>0.25 D): "
          f"{np.mean(adapt_resid > 0.25)*100:.0f}%")
    if lc_saturates:
        print(f"note: a liquid-crystal lens (+/-3 D) would SATURATE for this Rx "
              f"(reaches {min(true):.2f} D) -> pick a wider-range lens for high myopia")

    # --- plot ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    yr = months / 12.0
    ax1.plot(yr, true, "k--", lw=1.5, label="true prescription (drifts)")
    ax1.step(yr, static_applied, where="post", color="#e07a3c", lw=2,
             label=f"static glasses (visit every {VISIT_EVERY} mo)")
    ax1.step(yr, adapt_applied, where="post", color="#3c7ae0", lw=2,
             label="adaptive glasses (self-refract monthly)")
    ax1.set_ylabel("sphere power (D)")
    ax1.set_title("Adaptive glasses track a drifting prescription")
    ax1.legend(loc="lower left", fontsize=9)
    ax1.grid(alpha=0.2)

    ax2.fill_between(yr, 0, static_resid, step="post", color="#e07a3c", alpha=0.5,
                     label="static residual blur")
    ax2.fill_between(yr, 0, adapt_resid, step="post", color="#3c7ae0", alpha=0.7,
                     label="adaptive residual blur")
    ax2.axhline(0.25, color="k", ls=":", lw=1, label="~noticeable-blur threshold")
    ax2.set_ylabel("residual defocus |true - applied| (D)")
    ax2.set_xlabel("years")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(alpha=0.2)

    fig.tight_layout()
    path = os.path.join(OUT, "adaptive_glasses.png")
    fig.savefig(path, dpi=110)
    print(f"\nSaved chart -> {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
