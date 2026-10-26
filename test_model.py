"""
Sanity checks. Run with:  python test_model.py   (or: pytest)
"""

import math

from data import PRUSSIAN_TOTAL, FRENCH_TOTAL, HISTORICAL_END
from model import Params, Wave, simulate
from scenarios import historical, french_waves, calibrate


def test_square_law_invariant():
    """Without frontage limits, alpha*P^2 - beta*F^2 must stay constant (Lanchester 1916).
    (alpha = Prussian lethality, so each side's "fighting strength" is its
    lethality times the SQUARE of its numbers.)"""
    p = Params(alpha=0.10, beta=0.15, frontage=False, breakpoints=False)
    r = simulate(p, [Wave(20_000, 0)], [Wave(15_000, 0)], 20_000, 15_000,
                 t_end=3.0, dt=1 / 3600)
    P0, F0 = r.prussian_in_action[0], r.french_in_action[0]
    P1, F1 = r.prussian_in_action[-1], r.french_in_action[-1]
    before = p.alpha * P0**2 - p.beta * F0**2
    after = p.alpha * P1**2 - p.beta * F1**2
    assert math.isclose(before, after, rel_tol=0.01), (before, after)


def test_square_law_winner():
    """Equal quality: the bigger side wins and keeps sqrt(P0^2 - F0^2) men."""
    p = Params(alpha=0.1, beta=0.1, frontage=False, breakpoints=False)
    r = simulate(p, [Wave(10_000, 0)], [Wave(6_000, 0)], 10_000, 6_000,
                 t_end=40.0, dt=1 / 600)
    assert r.french_in_action[-1] < 1
    assert abs(r.prussian_in_action[-1] - 8_000) < 100


def test_frontage_caps_firepower():
    """With a frontage cap, adding men beyond the cap must not raise enemy losses."""
    p = Params(alpha=0.1, beta=0.1, breakpoints=False)
    cap = p.density * p.width["front"]
    # both attackers stay above the cap for the whole half hour
    small = simulate(p, [Wave(2 * cap, 0)], [Wave(cap, 0)], 2 * cap, cap, t_end=0.5)
    big = simulate(p, [Wave(3 * cap, 0)], [Wave(cap, 0)], 3 * cap, cap, t_end=0.5)
    assert math.isclose(small.french_losses[-1], big.french_losses[-1], rel_tol=1e-6)


def test_calibration_hits_targets():
    p = calibrate(Params(alpha=0.1, beta=0.2), PRUSSIAN_TOTAL, FRENCH_TOTAL, 6_500, 11_000)
    r = simulate(Params(**{**p.__dict__, "breakpoints": False}), historical(),
                 french_waves(), PRUSSIAN_TOTAL, FRENCH_TOTAL, t_end=HISTORICAL_END)
    assert abs(r.french_losses[-1] - 6_500) < 1
    assert abs(r.prussian_losses[-1] - 11_000) < 1


def test_breakpoint_ends_battle():
    p = Params(alpha=0.1, beta=0.3, frontage=False, break_prussian=0.2, break_french=0.9)
    r = simulate(p, [Wave(10_000, 0)], [Wave(10_000, 0)], 10_000, 10_000)
    assert r.winner == "France"
    assert r.prussian_losses[-1] >= 2_000


def test_both_timelines_calibrate():
    from data import TIMELINES
    for name, forms in TIMELINES.items():
        p = calibrate(Params(alpha=0.1, beta=0.2), PRUSSIAN_TOTAL, FRENCH_TOTAL,
                      6_500, 11_000, formations=forms)
        r = simulate(Params(**{**p.__dict__, "breakpoints": False}), historical(forms),
                     french_waves(), PRUSSIAN_TOTAL, FRENCH_TOTAL, t_end=HISTORICAL_END)
        assert abs(r.french_losses[-1] - 6_500) < 1, name
        assert abs(r.prussian_losses[-1] - 11_000) < 1, name


def test_orange_one_wing_moves_only_orange():
    from scenarios import orange_one_wing
    waves = orange_one_wing("south")
    flank = [w for w in waves if w.sector != "front"]
    assert len(flank) == 1 and flank[0].name.startswith("Orange")
    assert sum(w.strength for w in waves) == sum(w.strength for w in historical())


def test_split_army_shares():
    from scenarios import split_army
    from data import PRUSSIAN
    main, res = split_army(PRUSSIAN, 0.78, 0.12)
    total = sum(f.strength for f in PRUSSIAN)
    assert abs(sum(f.strength for f in main) - 0.78 * total) < 1e-6
    assert abs(sum(f.strength for f in res) - 0.12 * total) < 1e-6
    # main body = first to arrive; the reserve comes from the later divisions
    assert max(f.arrival for f in main) <= min(f.arrival for f in res)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
