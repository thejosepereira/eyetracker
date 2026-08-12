"""Calibration profile + a simple pairwise-comparison converger.

Prescription -> PSF is only a starting estimate. Interactive calibration lets the
user refine the correction by repeatedly choosing which of two candidate
strengths looks clearer. A staircase converges on their preferred value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChromaticCompensation:
    red: float = 1.0
    green: float = 1.0
    blue: float = 1.0


@dataclass
class CalibrationProfile:
    correction_strength: float = 1.0   # scales the estimated blur / PSF sigma
    regularization: float = 0.01       # Wiener K
    # Fraction of the display's full dynamic range the *target* is squeezed into
    # before pre-compensation. A conventional display cannot show the negative /
    # >1 values that full inversion needs, so we trade contrast for headroom:
    # lower `dynamic_range` -> less clipping -> sharper perceived result but
    # flatter contrast. This is the key knob that makes correction work on a
    # normal (non-light-field) screen.
    dynamic_range: float = 0.55
    contrast_boost: float = 1.0        # final perceptual contrast multiplier
    edge_compensation: float = 0.0     # extra unsharp amount (0 = none)
    chromatic: Optional[ChromaticCompensation] = None


@dataclass
class PairwiseStaircase:
    """Converge on a preferred correction strength via A/B comparisons.

    Each round presents two strengths; the chosen one becomes the new centre and
    the step shrinks. Simple, deterministic, and easy to reason about for a demo.
    """
    center: float = 1.0
    step: float = 0.4
    min_step: float = 0.05
    shrink: float = 0.6
    _rounds: int = field(default=0, init=False)

    def candidates(self) -> tuple[float, float]:
        lo = max(0.0, self.center - self.step)
        hi = self.center + self.step
        return (round(lo, 3), round(hi, 3))

    def choose(self, chosen_value: float) -> None:
        self.center = max(0.0, float(chosen_value))
        self.step = max(self.min_step, self.step * self.shrink)
        self._rounds += 1

    @property
    def converged(self) -> bool:
        return self.step <= self.min_step

    @property
    def rounds(self) -> int:
        return self._rounds
