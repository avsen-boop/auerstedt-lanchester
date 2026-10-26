"""
Run every experiment and write the figures + result tables.

    python run_all.py

Outputs:
    figures/1_historical_battle.png
    figures/2_strategy_vs_timing.png
    figures/3_monte_carlo_win_probability.png
    figures/4_sensitivity_double_envelopment.png
    figures/5_commitment_share.png
    results/summary.md
    results/monte_carlo.csv
"""

import csv
import os
from dataclasses import replace

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data import (FRENCH, PRUSSIAN, TIMELINES, FRENCH_TOTAL, PRUSSIAN_TOTAL,
                  FRENCH_LOSS_RANGE, PRUSSIAN_LOSS_RANGE,
                  FRENCH_LOSS_CENTRAL, PRUSSIAN_LOSS_CENTRAL, clock)
from model import Params, simulate
from scenarios import (french_waves, historical, concentrated, orange_one_wing,
                       single_envelopment, double_envelopment, calibrate,
                       with_commitment, as_fought_with_commitment,
                       historical_commitment)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
RES = os.path.join(HERE, "results")
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)

# ----------------------------------------------------------------- styling
BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 11, "axes.titlesize": 14,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 2,
    "legend.frameon": False,
})

STRATEGIES = {
    "Concentrated frontal attack": (concentrated, ORANGE),
    "Single envelopment (south)": (single_envelopment, AQUA),
    "Double envelopment": (double_envelopment, BLUE),
}


def clock_ticks(ax, start=0, stop=10, step=1):
    ticks = np.arange(start, stop + 1e-9, step)
    ax.set_xticks(ticks)
    ax.set_xticklabels([clock(t) for t in ticks])


def margin(r, p: Params):
    """> 0 means the French are closer to breaking than the Prussians (good for Prussia)."""
    f = r.french_losses[-1] / (p.break_french * r.french_total)
    pr = r.prussian_losses[-1] / (p.break_prussian * r.prussian_total)
    return f - pr


# ===================================================================== 1. baseline
base = Params(alpha=0.1, beta=0.2)
base = calibrate(base, PRUSSIAN_TOTAL, FRENCH_TOTAL,
                 FRENCH_LOSS_CENTRAL, PRUSSIAN_LOSS_CENTRAL)
# The Prussian army broke, in reality, at roughly its 12:30 casualty level.
base.break_prussian = PRUSSIAN_LOSS_CENTRAL / PRUSSIAN_TOTAL

hist = simulate(base, historical(), french_waves(), PRUSSIAN_TOTAL, FRENCH_TOTAL)

# Figure 1 - the historical battle as the model sees it
fig, ax = plt.subplots(figsize=(10, 5.6))
t = np.array(hist.t)
ax.plot(t, hist.prussian_in_action, color=BLUE)
ax.plot(t, hist.french_in_action, color=ORANGE)
ax.text(t[-1] + 0.05, hist.prussian_in_action[-1], "Prussians in action",
        color=INK, va="center", fontsize=10)
ax.text(t[-1] + 0.05, hist.french_in_action[-1], "French in action",
        color=INK, va="center", fontsize=10)
for f in PRUSSIAN:
    if f.historical_commit is not None and f.historical_commit > 0:
        ax.axvline(f.historical_commit, color=BLUE, alpha=0.25, lw=1, ls="--")
        ax.text(f.historical_commit + 0.03, 1_000, f.name.split(" (")[0],
                rotation=90, fontsize=8, color=INK2, va="bottom")
for f in FRENCH:
    if f.arrival > 0 and "cav" not in f.name:
        ax.axvline(f.arrival, color=ORANGE, alpha=0.25, lw=1, ls=":")
        ax.text(f.arrival + 0.03, 36_000, f.name.split(" (")[0],
                rotation=90, fontsize=8, color=INK2, va="bottom")
ax.set_xlim(0, 6.6)
clock_ticks(ax, 0, 6)
ax.set_ylim(0, 45_000)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
ax.set_ylabel("Men committed and still fighting")
ax.set_title("Auerstedt as fought: Prussian divisions fed in one at a time")
ax.text(0, -0.16, f"Model calibrated to ~{FRENCH_LOSS_CENTRAL:,} French and "
        f"~{PRUSSIAN_LOSS_CENTRAL:,} Prussian casualties by 12:30. "
        f"Prussian army breaks at {clock(hist.end_time)}.",
        transform=ax.transAxes, fontsize=9, color=INK2)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "1_historical_battle.png"), dpi=160)
plt.close(fig)

# Figure 2 - each strategy vs. the hour it is launched, under BOTH timelines.
# Each timeline gets its own calibration, because the fitted lethalities
# depend on when the historical attacks went in.
attack_times = np.arange(1.5, 4.51, 0.25)   # 08:30 .. 11:30
fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True)
baseline_rows, calib = [], {}
for ax, (tl_name, forms) in zip(axes, TIMELINES.items()):
    p = calibrate(Params(alpha=0.1, beta=0.2), PRUSSIAN_TOTAL, FRENCH_TOTAL,
                  FRENCH_LOSS_CENTRAL, PRUSSIAN_LOSS_CENTRAL, formations=forms)
    p.break_prussian = PRUSSIAN_LOSS_CENTRAL / PRUSSIAN_TOTAL
    calib[tl_name] = p
    for name, (fn, color) in STRATEGIES.items():
        m = []
        for T in attack_times:
            r = simulate(p, fn(T, formations=forms), french_waves(),
                         PRUSSIAN_TOTAL, FRENCH_TOTAL)
            m.append(margin(r, p))
            baseline_rows.append((tl_name, name, clock(T), r.winner, clock(r.end_time),
                                  round(r.prussian_losses[-1]), round(r.french_losses[-1])))
        ax.plot(attack_times, m, color=color, marker="o", markersize=5, label=name)
    h = simulate(p, historical(forms), french_waves(), PRUSSIAN_TOTAL, FRENCH_TOTAL)
    ax.axhline(margin(h, p), color=INK2, lw=1.2, ls="--")
    ax.text(attack_times[-1], margin(h, p) + 0.01, "As fought (piecemeal)",
            color=INK2, fontsize=9, va="bottom", ha="right")
    ax.axhline(0, color=INK, lw=1)
    ax.text(attack_times[-1], 0.01, "Prussia wins above this line", ha="right",
            va="bottom", fontsize=9, color=INK)
    for x, lbl in [(2.5, "Friant arrives"), (4.0, "Morand arrives")]:
        ax.axvline(x, color=ORANGE, alpha=0.3, lw=1, ls=":")
    clock_ticks(ax, 1.5, 4.5, 0.5)
    ax.set_xlabel("Time the coordinated Prussian attack is launched")
    ax.set_title(f"Timeline: {tl_name}  (fitted French edge {p.beta/p.alpha:.2f}×)",
                 fontsize=12)
axes[0].set_ylabel("Breaking margin (French − Prussian)")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=3,
           fontsize=10, frameon=False)
fig.suptitle("Envelopment beats concentration under both timelines; "
             "how much timing matters depends on the source",
             x=0.01, y=0.99, ha="left", fontweight="bold", fontsize=14)
fig.text(0.01, -0.02, "Dotted lines: Friant (09:30) and Morand (11:00) arrive. "
         "Each panel is calibrated separately to the same casualty figures.",
         fontsize=9, color=INK2)
fig.tight_layout(rect=(0, 0, 1, 0.87), w_pad=3)
fig.savefig(os.path.join(FIG, "2_strategy_vs_timing.png"), dpi=160, bbox_inches="tight")
plt.close(fig)

# ================================================================ 2. Monte Carlo
rng = np.random.default_rng(1806)
N = 2000
mc_times = [2.0, 3.0, 4.0]   # 09:00, 10:00, 11:00
rows = []
TL = list(TIMELINES)
wins = {(tl, n, T): 0 for tl in TL for n in STRATEGIES for T in mc_times}
wins_hist = {tl: 0 for tl in TL}
wins_orange = {tl: 0 for tl in TL}
draws = []          # calibrated set-ups, re-used by the commitment experiment
for i in range(N):
    s = dict(
        french_loss=rng.uniform(*FRENCH_LOSS_RANGE),
        prussian_loss=rng.uniform(*PRUSSIAN_LOSS_RANGE),
        french_scale=rng.uniform(1.0, 28_936 / FRENCH_TOTAL),   # with/without corps gunners
        extra_reserve=rng.uniform(0, 10_000),                   # army of 50k-60k
        density=rng.uniform(3_000, 4_500),
        w_front=rng.uniform(3.0, 4.5),
        w_flank=rng.uniform(1.0, 2.0),
        flank_bonus=rng.uniform(1.0, 2.0),
        break_french=rng.uniform(0.30, 0.45),
        break_mult=rng.uniform(0.9, 1.2),
        flank_delay=rng.uniform(0.5, 1.25),
    )
    f_total = FRENCH_TOTAL * s["french_scale"]
    fw = french_waves(s["french_scale"])
    row = {k: round(v, 4) for k, v in s.items()}
    setups = {}
    # The same draw is evaluated under each timeline (a paired comparison).
    for tl, base_forms in TIMELINES.items():
        # The extra 0-10,000 men go to the never-engaged Guard reserve.
        forms = [replace(f, strength=f.strength + s["extra_reserve"])
                 if f.name.startswith("Kuhnheim") else f for f in base_forms]
        p_total = sum(f.strength for f in forms)
        p = Params(alpha=0.1, beta=0.2, density=s["density"],
                   width={"front": s["w_front"], "north": s["w_flank"],
                          "south": s["w_flank"]},
                   flank_bonus=s["flank_bonus"], break_french=s["break_french"])
        p = calibrate(p, p_total, f_total, s["french_loss"], s["prussian_loss"],
                      formations=forms, french_scale=s["french_scale"])
        p.break_prussian = s["prussian_loss"] * s["break_mult"] / p_total
        setups[tl] = (p, forms, p_total)
        row[f"{tl}: alpha"] = round(p.alpha, 5)
        row[f"{tl}: beta"] = round(p.beta, 5)

        r = simulate(p, historical(forms), fw, p_total, f_total)
        row[f"{tl}: as fought"] = r.winner
        wins_hist[tl] += r.winner == "Prussia"
        r = simulate(p, orange_one_wing("south", 0.0, forms), fw, p_total, f_total)
        row[f"{tl}: Orange on one wing"] = r.winner
        wins_orange[tl] += r.winner == "Prussia"
        for name, (fn, _) in STRATEGIES.items():
            for T in mc_times:
                if fn is concentrated:
                    waves = fn(T, formations=forms)
                else:
                    waves = fn(T, flank_delay=s["flank_delay"], formations=forms)
                r = simulate(p, waves, fw, p_total, f_total)
                row[f"{tl}: {name} @ {clock(T)}"] = r.winner
                wins[(tl, name, T)] += r.winner == "Prussia"
    rows.append(row)
    draws.append((s, fw, f_total, setups))


def pooled(name, T):
    """Win share averaged over both timelines (each weighted equally)."""
    return 100 * sum(wins[(tl, name, T)] for tl in TL) / (N * len(TL))

with open(os.path.join(RES, "monte_carlo.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# Figure 3 - win probability
fig, ax = plt.subplots(figsize=(10, 5.6))
x = np.arange(len(mc_times))
bw = 0.26
for k, (name, (_, color)) in enumerate(STRATEGIES.items()):
    vals = [pooled(name, T) for T in mc_times]
    bars = ax.bar(x + (k - 1) * bw, vals, bw - 0.03, color=color, label=name)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.0f}%",
                ha="center", fontsize=9, color=INK)
ax.set_xticks(x)
ax.set_xticklabels([f"Attack at {clock(T)}" for T in mc_times])
ax.set_ylim(0, 105)
ax.set_ylabel(f"Share of {N * len(TL):,} simulations Prussia wins (%)")
ax.set_title("Could Prussia have won? Sometimes - with a wide attack")
ax.legend(loc="upper left")
h_pool = 100 * sum(wins_hist.values()) / (N * len(TL))
o_pool = 100 * sum(wins_orange.values()) / (N * len(TL))
ax.text(0, -0.13, f"As fought: Prussia wins {h_pool:.0f}% of runs. "
        f"Chandler's 'Orange on one wing': {o_pool:.0f}%. "
        "Each run re-draws uncertain inputs and re-calibrates; both timelines pooled.",
        transform=ax.transAxes, fontsize=9, color=INK2)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "3_monte_carlo_win_probability.png"), dpi=160)
plt.close(fig)

# ====================================================== 2b. how much to commit
# "Convention" (the user's assumption, not a documented rule): 75-80% of the
# army in the main attack, 10-15% in reserve, the rest detached.
# A separate random stream keeps the main Monte Carlo results unchanged.
rng_c = np.random.default_rng(1807)
RES_MODES = {"held": "reserve held back", "late": "reserve thrown in later"}
conv = {(tl, k): 0 for tl in TL for k in
        ["as fought"] + [f"{n}|{m}|{T}" for n in STRATEGIES for m in RES_MODES
                         for T in mc_times]}
hist_commit = {tl: [] for tl in TL}
conv_rows = []
for (s, fw, f_total, setups), row in zip(draws, rows):
    c = rng_c.uniform(0.75, 0.80)
    res_share = rng_c.uniform(0.10, 0.15)
    res_delay = rng_c.uniform(1.0, 2.0)
    row.update({"conv_commit": round(c, 4), "conv_reserve": round(res_share, 4),
                "conv_reserve_delay": round(res_delay, 4)})
    for tl, (p, forms, p_total) in setups.items():
        hist_commit[tl].append(historical_commitment(forms))
        r = simulate(p, as_fought_with_commitment(c, forms), fw, p_total, f_total)
        row[f"{tl}: as fought, 75-80% committed"] = r.winner
        conv[(tl, "as fought")] += r.winner == "Prussia"
        for name, (fn, _) in STRATEGIES.items():
            kw = {} if fn is concentrated else {"flank_delay": s["flank_delay"]}
            for mode in RES_MODES:
                for T in mc_times:
                    waves = with_commitment(fn, T, c, res_share, mode, res_delay,
                                            formations=forms, **kw)
                    r = simulate(p, waves, fw, p_total, f_total)
                    row[f"{tl}: {name} @ {clock(T)}, 75-80% + reserve {mode}"] = r.winner
                    conv[(tl, f"{name}|{mode}|{T}")] += r.winner == "Prussia"

# rewrite the CSV now that the commitment columns are in
with open(os.path.join(RES, "monte_carlo.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# Figure 5 - win rate vs share of the army committed (attack at 10:00, the
# reserve held back), on the first 500 draws to keep run time reasonable.
N_SWEEP = 500
fracs = np.round(np.arange(0.30, 1.001, 0.05), 2)
T_SWEEP = 3.0
sweep = {(n, f): 0 for n in STRATEGIES for f in fracs}
for s, fw, f_total, setups in draws[:N_SWEEP]:
    for tl, (p, forms, p_total) in setups.items():
        for name, (fn, _) in STRATEGIES.items():
            kw = {} if fn is concentrated else {"flank_delay": s["flank_delay"]}
            for fr in fracs:
                waves = with_commitment(fn, T_SWEEP, fr, 0.0, "held",
                                        formations=forms, **kw)
                sweep[(name, fr)] += simulate(p, waves, fw, p_total,
                                              f_total).winner == "Prussia"
fig, ax = plt.subplots(figsize=(10, 5.6))
ax.axvspan(75, 80, color=GRID, alpha=0.9, lw=0)
ax.text(77.5, 101, "75-80%\n'convention'", ha="center", va="bottom", fontsize=9, color=INK2)
for name, (_, color) in STRATEGIES.items():
    ys = [100 * sweep[(name, fr)] / (N_SWEEP * len(TL)) for fr in fracs]
    ax.plot(100 * fracs, ys, color=color, marker="o", markersize=5, label=name)
for tl, y in zip(TL, [-4, -10]):
    lo, hi = 100 * min(hist_commit[tl]), 100 * max(hist_commit[tl])
    ax.plot([lo, hi], [y, y], color=INK2, lw=4, solid_capstyle="butt")
    ax.text(lo - 1, y, f"Actually committed, {tl}", ha="right", va="center",
            fontsize=8, color=INK2)
ax.set_xlim(28, 102)
ax.set_ylim(-14, 112)
ax.set_xlabel("Share of the Prussian army in the attack (%)")
ax.set_ylabel("Share of simulations Prussia wins (%)")
ax.set_title("Beyond ~75% of the army, committing more men adds almost nothing", pad=34)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=10)
fig.text(0.01, 0.015, f"Attack launched at {clock(T_SWEEP)}; uncommitted men take no part; "
         f"{N_SWEEP} draws x {len(TL)} timelines.\nThe frontage limit caps how many men "
         "can fight at once, so extra men only replace losses.", fontsize=9, color=INK2)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(os.path.join(FIG, "5_commitment_share.png"), dpi=160)
plt.close(fig)

# ======================================================= 3. sensitivity heatmap
bonuses = np.linspace(1.0, 2.5, 16)
mults = np.linspace(0.8, 1.6, 17)
sens_times = [2.0, 3.0, 4.0]
fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), sharey=True)
for ax, T in zip(axes, sens_times):
    grid = np.zeros((len(mults), len(bonuses)))
    for i, mlt in enumerate(mults):
        for j, b in enumerate(bonuses):
            p = replace(base, flank_bonus=b, break_prussian=base.break_prussian * mlt)
            r = simulate(p, double_envelopment(T), french_waves(), PRUSSIAN_TOTAL, FRENCH_TOTAL)
            grid[i, j] = margin(r, p)
    lim = 0.6
    im = ax.imshow(np.clip(grid, -lim, lim), origin="lower", aspect="auto",
                   cmap="RdBu", vmin=-lim, vmax=lim,
                   extent=[bonuses[0], bonuses[-1], mults[0], mults[-1]])
    ax.contour(bonuses, mults, grid, levels=[0], colors=INK, linewidths=1.5)
    ax.plot(1.5, 1.0, marker="o", color=INK, markersize=6)
    ax.set_title(f"Double envelopment at {clock(T)}", fontsize=12)
    ax.set_xlabel("Flank-attack bonus (×)")
    ax.grid(False)
axes[0].set_ylabel("Prussian staying power\n(× losses they took before breaking)")
cb = fig.colorbar(im, ax=axes, shrink=0.85)
cb.set_label("Margin: blue = Prussia wins, red = France wins")
fig.suptitle("Where the line sits: what an envelopment needs to succeed "
             "(online-sources timeline)",
             x=0.01, ha="left", fontweight="bold", fontsize=14)
fig.text(0.01, -0.06, "Black line = break-even. Dot = baseline assumptions. "
         "Staying power 1.0 = the casualty level at which the Prussians actually broke.",
         fontsize=9, color=INK2)
fig.savefig(os.path.join(FIG, "4_sensitivity_double_envelopment.png"), dpi=160,
            bbox_inches="tight")
plt.close(fig)

# ================================================================ 4. summary
lines = ["# Results (generated by run_all.py)\n",
         "Two historical timelines are modelled: one assembled from online sources and one",
         "following Chandler (1966). Each is calibrated separately to the same casualties.\n",
         "## Calibration\n",
         "| Timeline | alpha (Prussian lethality) | beta (French lethality) | French edge per man | "
         "Square-law break-even ratio |",
         "|---|---|---|---|---|"]
for tl, p in calib.items():
    lines.append(f"| {tl} | {p.alpha:.3f} | {p.beta:.3f} | {p.beta/p.alpha:.2f}x | "
                 f"{np.sqrt(p.beta/p.alpha):.2f} : 1 |")
lines += ["", f"Prussia's overall numerical ratio: {PRUSSIAN_TOTAL/FRENCH_TOTAL:.2f} : 1. "
          f"Historical run (online timeline): Prussian army breaks at "
          f"{clock(hist.end_time)} (by construction).\n",
          "## Baseline: strategy x launch time\n",
          "| Timeline | Strategy | Launched | Winner | Decided at | Prussian losses | French losses |",
          "|---|---|---|---|---|---|---|"]
lines += [f"| {a} | {b} | {c} | {d} | {e} | {f:,} | {g:,} |"
          for a, b, c, d, e, f, g in baseline_rows]
lines += ["", f"## Monte Carlo ({N:,} draws, each run under both timelines)\n",
          "Share of runs Prussia wins.\n",
          "| Strategy | Timeline | " + " | ".join(clock(T) for T in mc_times) + " |",
          "|---|---|" + "---|" * len(mc_times)]
for name in STRATEGIES:
    for tl in TL:
        lines.append(f"| {name} | {tl} | " + " | ".join(
            f"{100*wins[(tl, name, T)]/N:.0f}%" for T in mc_times) + " |")
    lines.append(f"| **{name}** | **both (pooled)** | " + " | ".join(
        f"**{pooled(name, T):.0f}%**" for T in mc_times) + " |")
lines += ["", "Scenarios with fixed (historical) timing:\n",
          "| Scenario | " + " | ".join(TL) + " |", "|---|" + "---|" * len(TL),
          "| As fought (piecemeal) | " + " | ".join(
              f"{100*wins_hist[tl]/N:.0f}%" for tl in TL) + " |",
          "| Chandler's counterfactual: Orange's whole division on the south flank, 11:00 | "
          + " | ".join(f"{100*wins_orange[tl]/N:.0f}%" for tl in TL) + " |"]
def cpct(tl, key):
    return 100 * conv[(tl, key)] / N


lines += ["", "## Commitment: 75-80% of the army attacking, 10-15% in reserve\n",
          "Historical commitment in the model: " + "; ".join(
              f"{tl} {100*min(hist_commit[tl]):.0f}-{100*max(hist_commit[tl]):.0f}%"
              for tl in TL) + " (depending on the 50,000-60,000 army size).\n",
          "| Strategy | Reserve | Timeline | " + " | ".join(clock(T) for T in mc_times)
          + " | Same strategy, everyone committed (" + clock(mc_times[0]) + ") |",
          "|---|---|---|" + "---|" * len(mc_times) + "---|"]
for tl in TL:
    lines.append(f"| As fought (piecemeal), 75-80% committed | none | {tl} | "
                 f"{cpct(tl, 'as fought'):.0f}% | n/a | n/a | "
                 f"{100*wins_hist[tl]/N:.0f}% (as actually fought) |")
for name in STRATEGIES:
    for mode, label in RES_MODES.items():
        for tl in TL:
            lines.append(f"| {name} | {label} | {tl} | " + " | ".join(
                f"{cpct(tl, f'{name}|{mode}|{T}'):.0f}%" for T in mc_times)
                + f" | {100*wins[(tl, name, mc_times[0])]/N:.0f}% |")
lines += ["", f"Win rate vs share committed (attack at {clock(T_SWEEP)}, reserve held, "
          f"{N_SWEEP} draws x both timelines):\n",
          "| Share committed | " + " | ".join(STRATEGIES) + " |",
          "|---|" + "---|" * len(STRATEGIES)]
for fr in fracs:
    lines.append(f"| {fr:.0%} | " + " | ".join(
        f"{100*sweep[(n, fr)]/(N_SWEEP*len(TL)):.0f}%" for n in STRATEGIES) + " |")

# Ablation: the same experiment with NO frontage limit (pure square law),
# re-calibrated from scratch so the comparison is fair.
lines += ["", "## Ablation: pure square law (no frontage limit), re-calibrated\n",
          "| Timeline | Strategy | " + " | ".join(clock(T) for T in mc_times) + " |",
          "|---|---|" + "---|" * len(mc_times)]
for tl, forms in TIMELINES.items():
    pure = calibrate(Params(alpha=0.1, beta=0.2, frontage=False), PRUSSIAN_TOTAL,
                     FRENCH_TOTAL, FRENCH_LOSS_CENTRAL, PRUSSIAN_LOSS_CENTRAL,
                     formations=forms)
    pure.break_prussian = PRUSSIAN_LOSS_CENTRAL / PRUSSIAN_TOTAL
    for name, (fn, _) in STRATEGIES.items():
        res = [simulate(pure, fn(T, formations=forms), french_waves(),
                        PRUSSIAN_TOTAL, FRENCH_TOTAL).winner for T in mc_times]
        lines.append(f"| {tl} | {name} | " + " | ".join(res) + " |")
    lines.append(f"| {tl} | As fought (piecemeal) | "
                 + simulate(pure, historical(forms), french_waves(),
                            PRUSSIAN_TOTAL, FRENCH_TOTAL).winner + " | n/a | n/a |")
open(os.path.join(RES, "summary.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
