"""
A small, transparent Lanchester combat model with three battlefield sectors.

Core idea (Lanchester's "square law", 1916):
    dP/dt = -beta  * F      Prussians lose men in proportion to French firing
    dF/dt = -alpha * P      French lose men in proportion to Prussians firing

alpha = how many Frenchmen one Prussian in contact disables per hour
beta  = how many Prussians one Frenchman in contact disables per hour

Three additions make it usable for a Napoleonic battle:

1. FRONTAGE LIMIT. Only so many men can fight at once along a given width of
   front (roughly 3,000-4,500 men per km in 1806 line/column tactics). Men
   beyond that limit wait behind as supports; they replace losses but do not
   add firepower. On a narrow front this blunts numerical superiority.

2. SECTORS. The battle has a "front" sector plus optional "north" and "south"
   flank sectors. Attacking a flank opens extra frontage -> more men in contact.

3. BREAKPOINTS. Real armies stop fighting long before annihilation. A side
   "breaks" when its cumulative losses reach a set fraction of its strength.

The French defender is assumed to have perfect interior lines: at every
moment Davout spreads his men across sectors in proportion to the Prussian
threat there. This is deliberately generous to the French.
"""

from dataclasses import dataclass, field

SECTORS = ("front", "north", "south")


@dataclass
class Params:
    alpha: float                 # Prussian lethality (per man in contact, per hour)
    beta: float                  # French lethality (per man in contact, per hour)
    density: float = 3_500.0     # men per km who can fight in contact
    width: dict = field(default_factory=lambda: {"front": 3.5, "north": 1.5, "south": 1.5})
    flank_bonus: float = 1.5     # multiplier on Prussian lethality in flank sectors
    break_prussian: float = 0.22 # Prussians break at this loss fraction of their army
    break_french: float = 0.35   # French break at this loss fraction of their corps
    frontage: bool = True        # switch the frontage limit on/off
    breakpoints: bool = True     # switch breakpoints on/off


@dataclass
class Wave:
    """A body of troops entering combat at time `time` in sector `sector`."""
    strength: float
    time: float
    sector: str = "front"
    name: str = ""


@dataclass
class Result:
    t: list
    prussian_in_action: list
    french_in_action: list
    prussian_losses: list
    french_losses: list
    winner: str              # "Prussia", "France" or "Undecided"
    end_time: float
    prussian_total: float
    french_total: float


def simulate(params: Params,
             prussian_waves: list[Wave],
             french_waves: list[Wave],
             prussian_total: float,
             french_total: float,
             t_end: float = 10.0,
             dt: float = 1 / 60) -> Result:
    """Integrate the model with simple Euler steps (dt = 1 minute by default)."""
    P = {s: 0.0 for s in SECTORS}   # Prussians committed and still fighting, per sector
    F = 0.0                         # French on the field (redistributed every step)
    p_loss = f_loss = 0.0
    p_pending = sorted(prussian_waves, key=lambda w: w.time)
    f_pending = sorted(french_waves, key=lambda w: w.time)

    out_t, out_p, out_f, out_pl, out_fl = [], [], [], [], []
    winner, t = "Undecided", 0.0
    steps = int(round(t_end / dt))

    for i in range(steps + 1):
        t = i * dt
        # --- arrivals -----------------------------------------------------
        while p_pending and p_pending[0].time <= t + 1e-9:
            w = p_pending.pop(0)
            P[w.sector] += w.strength
        while f_pending and f_pending[0].time <= t + 1e-9:
            F += f_pending.pop(0).strength

        out_t.append(t)
        out_p.append(sum(P.values()))
        out_f.append(F)
        out_pl.append(p_loss)
        out_fl.append(f_loss)

        # --- breakpoints --------------------------------------------------
        if params.breakpoints:
            p_broke = p_loss >= params.break_prussian * prussian_total
            f_broke = f_loss >= params.break_french * french_total
            if p_broke or f_broke:
                if p_broke and f_broke:
                    # both crossed in the same minute: whoever is further past wins
                    p_ratio = p_loss / (params.break_prussian * prussian_total)
                    f_ratio = f_loss / (params.break_french * french_total)
                    winner = "France" if p_ratio >= f_ratio else "Prussia"
                else:
                    winner = "France" if p_broke else "Prussia"
                break
        if i == steps:
            break

        # --- French distribute themselves across threatened sectors -------
        p_sum = sum(P.values())
        share = {s: (P[s] / p_sum if p_sum > 0 else (1.0 if s == "front" else 0.0))
                 for s in SECTORS}

        dP_total = dF_total = 0.0
        for s in SECTORS:
            Fs = F * share[s]
            if P[s] <= 0 or Fs <= 0:
                continue
            cap = params.density * params.width[s] if params.frontage else float("inf")
            p_engaged = min(P[s], cap)
            f_engaged = min(Fs, cap)
            bonus = params.flank_bonus if s != "front" else 1.0
            dF = params.alpha * bonus * p_engaged * dt    # French casualties
            dP = params.beta * f_engaged * dt             # Prussian casualties
            dP = min(dP, P[s])
            P[s] -= dP
            dP_total += dP
            dF_total += dF

        dF_total = min(dF_total, F)
        F -= dF_total
        p_loss += dP_total
        f_loss += dF_total

    return Result(out_t, out_p, out_f, out_pl, out_fl, winner, t,
                  prussian_total, french_total)
