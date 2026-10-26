"""
Prussian courses of action, and calibration of the model to the real battle.

Rules that apply to every counterfactual (to keep it honest):
  * Prussian divisions cannot arrive earlier than they historically could
    (they were marching in column along one road).
  * French arrivals are exactly as in history (Morand still arrives ~11:00).
  * Units waiting for the coordinated attack are assumed to take no losses.
  * Flank attacks need extra marching time (`flank_delay`) before they bite.
"""

from data import FRENCH, PRUSSIAN, HISTORICAL_END
from model import Params, Wave, simulate


def french_waves(scale: float = 1.0):
    """French arrivals as in history; `scale` lets us vary total strength."""
    return [Wave(f.strength * scale, f.arrival, "front", f.name) for f in FRENCH]


# ---------------------------------------------------------------- strategies
def historical(formations=PRUSSIAN):
    """What actually happened: divisions fed in one by one, all frontally."""
    return [Wave(f.strength, f.historical_commit, "front", f.name)
            for f in formations if f.historical_commit is not None]


def concentrated(attack_time: float, formations=PRUSSIAN):
    """Wait, assemble everything, then attack frontally all at once."""
    return [Wave(f.strength, max(f.arrival, attack_time), "front", f.name)
            for f in formations]


def single_envelopment(attack_time: float, side: str = "south",
                       flank_share: float = 0.4, flank_delay: float = 0.75,
                       formations=PRUSSIAN):
    """Pin the front with most of the army, swing a wing round one flank.
    'south' = the French left, historically Davout's weaker side."""
    waves = []
    for f in formations:
        t0 = max(f.arrival, attack_time)
        waves.append(Wave(f.strength * (1 - flank_share), t0, "front", f.name))
        waves.append(Wave(f.strength * flank_share, t0 + flank_delay, side, f.name))
    return waves


def double_envelopment(attack_time: float, flank_share: float = 0.25,
                       flank_delay: float = 0.75, formations=PRUSSIAN):
    """Pin the centre, attack both flanks (flank_share of the army on each)."""
    waves = []
    for f in formations:
        t0 = max(f.arrival, attack_time)
        waves.append(Wave(f.strength * (1 - 2 * flank_share), t0, "front", f.name))
        for side in ("north", "south"):
            waves.append(Wave(f.strength * flank_share, t0 + flank_delay, side, f.name))
    return waves


def orange_one_wing(side: str = "south", flank_delay: float = 0.0,
                    formations=PRUSSIAN):
    """Chandler's own counterfactual (in his Auerstedt account, pp. 489-495): everything happens as
    historically, except that Orange sends his WHOLE division against one flank
    instead of splitting it. Chandler judges this 'very probable' to have
    tipped the battle."""
    waves = []
    for f in formations:
        if f.historical_commit is None:
            continue
        sector = side if f.name.startswith("Orange") else "front"
        delay = flank_delay if sector != "front" else 0.0
        waves.append(Wave(f.strength, f.historical_commit + delay, sector, f.name))
    return waves


# ------------------------------------------------------ partial commitment
def split_army(formations, commit: float, reserve: float, key=None):
    """Split the army into a main body (`commit` share of all men), a reserve
    (`reserve` share) and an uncommitted remainder (detachments, baggage
    guards, stragglers). Men are assigned in order of `key` (default: arrival
    time), so the first-arriving divisions form the main body and the last
    ones the reserve - as they would in practice on a single road."""
    from dataclasses import replace
    key = key or (lambda f: f.arrival)
    total = sum(f.strength for f in formations)
    left_main, left_res = commit * total, reserve * total
    main, res = [], []
    for f in sorted(formations, key=key):
        s = f.strength
        take = min(s, left_main)
        left_main -= take
        s -= take
        if take > 0:
            main.append(replace(f, strength=take))
        take = min(s, left_res)
        left_res -= take
        if take > 0:
            res.append(replace(f, strength=take))
    return main, res


def with_commitment(strategy, attack_time: float, commit: float, reserve: float,
                    reserve_mode: str = "held", reserve_delay: float = 1.5,
                    formations=PRUSSIAN, **kw):
    """Run `strategy` with only `commit` of the army in the main attack.
    reserve_mode = "held":  the reserve never fights (it only exists).
    reserve_mode = "late":  the reserve follows the same plan `reserve_delay`
                            hours later, as a second blow."""
    main, res = split_army(formations, commit, reserve)
    waves = strategy(attack_time, formations=main, **kw)
    if reserve_mode == "late" and res:
        waves += strategy(attack_time + reserve_delay, formations=res, **kw)
    return waves


def as_fought_with_commitment(commit: float, formations=PRUSSIAN):
    """Historical piecemeal, frontal attacks at the historical times, but the
    total committed is set to `commit` of the army: never-used divisions are
    thrown in when they arrive (11:00), or the latest ones are held back."""
    from dataclasses import replace
    timed = [replace(f, historical_commit=f.arrival if f.historical_commit is None
                     else f.historical_commit) for f in formations]
    main, _ = split_army(timed, commit, 0.0, key=lambda f: f.historical_commit)
    return historical(main)


def historical_commitment(formations=PRUSSIAN) -> float:
    """Share of the army that historically entered the fight (in this model)."""
    total = sum(f.strength for f in formations)
    return sum(f.strength for f in formations if f.historical_commit is not None) / total


# --------------------------------------------------------------- calibration
def calibrate(params: Params, prussian_total: float, french_total: float,
              french_loss_target: float, prussian_loss_target: float,
              iterations: int = 30, formations=PRUSSIAN,
              french_scale: float = 1.0) -> Params:
    """Find alpha and beta so the HISTORICAL scenario reproduces the recorded
    losses by 12:30. Two unknowns, two targets: this is a fit, not a test."""
    p = Params(**{**params.__dict__, "breakpoints": False})
    for _ in range(iterations):
        r = simulate(p, historical(formations), french_waves(french_scale),
                     prussian_total, french_total,
                     t_end=HISTORICAL_END)
        f_loss, p_loss = r.french_losses[-1], r.prussian_losses[-1]
        # Each loss depends almost only on the OTHER side's lethality,
        # so rescaling each coefficient by target/actual converges in a few steps.
        p.alpha *= french_loss_target / f_loss
        p.beta *= prussian_loss_target / p_loss
    params.alpha, params.beta = p.alpha, p.beta
    return params
