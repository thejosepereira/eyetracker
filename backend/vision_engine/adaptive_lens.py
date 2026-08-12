"""Adaptive ("AI") glasses: tunable-lens control instead of image pre-distortion.

Screen correction (the rest of this package) deconvolves a *known image*. Glasses
see the *real world*, so they cannot software-pre-distort the incoming light. They
instead use a physically **tunable lens** whose optical power changes on command,
driven by sensing + control software. This module models that control side:

    TunableLens        - hardware abstraction: target dioptres -> clamped/quantised
                         command, per lens technology (LC / fluidic / Alvarez).
    SelfRefraction     - estimate the wearer's *current* refractive error from
                         clarity feedback, so the Rx tracks drift over time
                         (the "fewer doctor visits" feature).
    AdaptiveController - combine the tracked distance Rx with a distance/gaze-based
                         near-add ("autofocals") into a single target power.

IMPORTANT: This corrects *refractive* error only. It does NOT replace a periodic
eye-health exam (glaucoma, retina, etc.). Experimental; not a medical device.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import math


# --------------------------------------------------------------------------- #
# Tunable lens hardware abstraction
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LensSpec:
    """Capabilities/limits of a tunable-lens technology (approximate, illustrative)."""
    name: str
    min_sphere_d: float      # most negative added power (dioptres)
    max_sphere_d: float      # most positive added power
    resolution_d: float      # smallest power step the driver can set
    settle_ms: float         # time to reach a new power
    can_cylinder: bool       # can it apply astigmatic (cylindrical) correction?
    max_cylinder_d: float = 0.0


# Illustrative device envelopes (not vendor specs).
LENS_SPECS = {
    "lc":      LensSpec("liquid-crystal", -3.0, 3.0, 0.05, 30.0, True, 2.0),
    "fluidic": LensSpec("fluidic/electrowetting", -8.0, 8.0, 0.10, 15.0, False),
    "alvarez": LensSpec("alvarez (motorised)", -6.0, 4.0, 0.01, 120.0, False),
}


@dataclass
class LensCommand:
    sphere_d: float
    cylinder_d: float
    axis_deg: float
    clamped: bool          # target exceeded the device range
    unsupported_cyl: bool  # cylinder requested but device can't do it


class TunableLens:
    """Maps a desired correction to a physically achievable lens command."""

    def __init__(self, spec: LensSpec | str = "lc"):
        self.spec = LENS_SPECS[spec] if isinstance(spec, str) else spec

    def _quantise(self, v: float) -> float:
        r = self.spec.resolution_d
        return round(v / r) * r

    def command(self, sphere_d: float, cylinder_d: float = 0.0, axis_deg: float = 0.0) -> LensCommand:
        s = self.spec
        clamped = sphere_d < s.min_sphere_d or sphere_d > s.max_sphere_d
        sph = self._quantise(min(max(sphere_d, s.min_sphere_d), s.max_sphere_d))

        unsupported = bool(cylinder_d) and not s.can_cylinder
        if not s.can_cylinder:
            cyl = 0.0
        else:
            if abs(cylinder_d) > s.max_cylinder_d:
                clamped = True
            cyl = self._quantise(max(-s.max_cylinder_d, min(0.0, cylinder_d)))
        return LensCommand(sph, cyl, axis_deg % 180, clamped, unsupported)


# --------------------------------------------------------------------------- #
# Accommodation / autofocus (autofocals)
# --------------------------------------------------------------------------- #

def max_accommodation_d(age_years: float) -> float:
    """Approximate remaining accommodation by age (Duane/Hofstetter, simplified)."""
    return max(0.5, 15.0 - 0.25 * age_years)


def near_add_d(distance_m: float, age_years: float, comfort: float = 0.5) -> float:
    """Extra plus power to focus at `distance_m`, beyond what the eye can accommodate.

    Demand to focus at distance d is 1/d dioptres. The eye can supply up to
    `max_accommodation_d(age)` (minus a comfort reserve). The lens makes up the
    shortfall — this is what presbyopes lose and what autofocals restore.
    """
    if distance_m <= 0:
        return 0.0
    demand = 1.0 / distance_m
    available = max_accommodation_d(age_years) * (1.0 - comfort)
    return max(0.0, demand - available)


# --------------------------------------------------------------------------- #
# Self-refraction (continuous prescription tracking)
# --------------------------------------------------------------------------- #

# A clarity oracle returns a "how sharp is it" score for a trial correction power.
# In the device this comes from the wearer's response (or an on-board wavefront
# sensor); in simulation it is a function of the residual defocus.
ClarityOracle = Callable[[float], float]


@dataclass
class SelfRefraction:
    """Estimate the sphere that maximises clarity, at clinical resolution.

    Coarse staircase to bracket the peak, then refine in `resolution_d` steps.
    Deterministic and robust to a unimodal-with-noise oracle.
    """
    lo: float = -10.0
    hi: float = 6.0
    resolution_d: float = 0.25
    coarse_step: float = 1.0

    def measure(self, oracle: ClarityOracle) -> float:
        # coarse scan
        best, best_score = self.lo, -math.inf
        v = self.lo
        while v <= self.hi + 1e-9:
            s = oracle(v)
            if s > best_score:
                best_score, best = s, v
            v += self.coarse_step
        # refine around the coarse best
        lo = max(self.lo, best - self.coarse_step)
        hi = min(self.hi, best + self.coarse_step)
        v = lo
        while v <= hi + 1e-9:
            s = oracle(v)
            if s > best_score:
                best_score, best = s, v
            v += self.resolution_d
        return round(best / self.resolution_d) * self.resolution_d


# --------------------------------------------------------------------------- #
# Adaptive controller
# --------------------------------------------------------------------------- #

@dataclass
class AdaptiveController:
    """Turn a tracked distance Rx + viewing distance into a target lens command."""
    lens: TunableLens = field(default_factory=lambda: TunableLens("lc"))
    age_years: float = 45.0
    tracked_sphere_d: float = 0.0     # distance-correction sphere (from self-refraction)
    tracked_cylinder_d: float = 0.0
    tracked_axis_deg: float = 0.0

    def update_from_refraction(self, sphere_d: float, cylinder_d: float = 0.0, axis_deg: float = 0.0) -> None:
        self.tracked_sphere_d = sphere_d
        self.tracked_cylinder_d = cylinder_d
        self.tracked_axis_deg = axis_deg

    def target(self, viewing_distance_m: float | None = None) -> LensCommand:
        add = near_add_d(viewing_distance_m, self.age_years) if viewing_distance_m else 0.0
        return self.lens.command(
            self.tracked_sphere_d + add, self.tracked_cylinder_d, self.tracked_axis_deg
        )
