import math
import pytest

from vision_engine import (
    TunableLens, LENS_SPECS, SOLID_STATE_LENSES, SelfRefraction, AdaptiveController,
    near_add_d, max_accommodation_d,
)


# ---- non-liquid (solid-state) lens options ----

def test_solid_state_lenses_available():
    # Alvarez / deformable / metasurface / electro-optic are all liquid-free.
    assert set(SOLID_STATE_LENSES) >= {"alvarez", "deformable", "metasurface", "electro_optic"}
    for k in SOLID_STATE_LENSES:
        assert LENS_SPECS[k].medium == "solid"
        assert LENS_SPECS[k].liquid_free


def test_metasurface_is_flat_and_can_do_cylinder():
    meta = LENS_SPECS["metasurface"]
    assert meta.liquid_free and not meta.moving_parts   # flat, no liquid, no motion
    assert meta.can_cylinder                            # can encode astigmatism
    cmd = TunableLens("metasurface").command(-2.0, cylinder_d=-1.5, axis_deg=90)
    assert cmd.cylinder_d < 0 and not cmd.unsupported_cyl


def test_control_is_lens_agnostic():
    # The same target power resolves through any backend (liquid or solid).
    for backend in ("fluidic", "alvarez", "metasurface", "electro_optic"):
        cmd = TunableLens(backend).command(-1.5)
        assert abs(cmd.sphere_d - (-1.5)) <= LENS_SPECS[backend].resolution_d + 1e-9


# ---- tunable lens ----

def test_lens_quantises_and_clamps():
    lens = TunableLens("lc")  # +/-3 D, 0.05 step
    cmd = lens.command(-2.53)
    assert cmd.sphere_d == pytest.approx(-2.55, abs=1e-9)  # snapped to 0.05 grid
    assert not cmd.clamped
    hi = lens.command(-9.0)                                 # beyond range
    assert hi.sphere_d == pytest.approx(-3.0)
    assert hi.clamped


def test_lens_cylinder_support():
    fluidic = TunableLens("fluidic")   # no cylinder
    cmd = fluidic.command(-2.0, cylinder_d=-1.0, axis_deg=90)
    assert cmd.cylinder_d == 0.0
    assert cmd.unsupported_cyl
    lc = TunableLens("lc")             # has cylinder
    cmd2 = lc.command(-2.0, cylinder_d=-1.0, axis_deg=90)
    assert cmd2.cylinder_d < 0
    assert not cmd2.unsupported_cyl


# ---- self-refraction ----

@pytest.mark.parametrize("true_power", [-1.0, -2.75, 0.5, -4.25])
def test_self_refraction_converges(true_power):
    oracle = lambda p: -abs(p - true_power)     # clarity peaks at the true power
    est = SelfRefraction(resolution_d=0.25).measure(oracle)
    assert abs(est - true_power) <= 0.25 + 1e-9


# ---- accommodation / near add ----

def test_young_eye_needs_no_add_but_presbyope_does():
    # reading at 40 cm
    assert near_add_d(0.40, age_years=20) == 0.0          # plenty of accommodation
    assert near_add_d(0.40, age_years=60) > 1.0           # presbyopia -> needs add
    assert max_accommodation_d(20) > max_accommodation_d(60)


# ---- controller ----

def test_controller_combines_distance_and_near_add():
    ctl = AdaptiveController(lens=TunableLens("fluidic"), age_years=55)
    ctl.update_from_refraction(-2.0)
    far = ctl.target(viewing_distance_m=None).sphere_d       # distance only
    near = ctl.target(viewing_distance_m=0.35).sphere_d      # near work adds plus
    assert far == pytest.approx(-2.0, abs=0.11)
    assert near > far                                        # more plus power for near
