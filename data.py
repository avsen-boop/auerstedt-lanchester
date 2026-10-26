"""
Historical inputs for the Battle of Auerstedt (14 October 1806).

Every number here is an ESTIMATE. Sources disagree, sometimes widely.
Times are expressed as hours after 07:00 (so t = 3.0 means 10:00).

Main sources (see README for the full list):
  - J. Rickard, "Battle of Auerstadt, 14 October 1806", historyofwar.org (2012)
  - Wikipedia, "Battle of Jena-Auerstedt" and its order-of-battle article
  - F. L. Petre, "Napoleon's Conquest of Prussia 1806" (cited via Wikipedia)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Formation:
    name: str
    strength: float        # men (all arms)
    arrival: float         # hours after 07:00 when it could reach the fighting
    historical_commit: float | None  # when it was actually thrown in (None = never)


def clock(t: float) -> str:
    """Convert model time (hours after 07:00) to a clock string."""
    minutes = int(round((7 + t) * 60))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# French III Corps (Davout)
# Division strengths from the Jena-Auerstedt order of battle (Wikipedia);
# Rickard gives 26,000 infantry + 1,622 cavalry + 1,681 gunners, 46 guns.
# Arrival times: Gudin ~07:00, Friant ~09:30, Morand ~11:00 (multiple sources).
# ---------------------------------------------------------------------------
FRENCH = [
    Formation("Gudin (3rd Div.)",        8_473, 0.0, 0.0),
    Formation("Friant (2nd Div.)",       7_293, 2.5, 2.5),
    Formation("Vialannes (light cav.)",  1_622, 2.5, 2.5),
    Formation("Morand (1st Div.)",       9_867, 4.0, 4.0),
]

# ---------------------------------------------------------------------------
# Prussian main army (Brunswick, then King Frederick William III)
# Totals: Petre ~49,800; Rickard 60-63,000 with "around 50,000" taking part.
# Division-level strengths are NOT reliably published in the sources checked;
# the split below is an approximation (Prussian divisions of 1806 had roughly
# 10-11 battalions + 15 squadrons + 3 batteries, i.e. ~10,000 men; Orange's
# division is given as ~10,000 by napoleon-empire.org).
# Timings: Blücher's cavalry in contact ~07:00; Schmettau ~08:00;
# Wartensleben arrived ~08:30-09:30 and attacked ~10:00; Orange ~10:30-11:00;
# Arnim's reserve division engaged only late; Kuhnheim (Guard) never.
# ---------------------------------------------------------------------------
PRUSSIAN = [
    Formation("Blücher (advance cavalry)",   2_500, 0.0, 0.0),
    Formation("Schmettau (3rd Div.)",       10_500, 1.0, 1.0),
    Formation("Wartensleben (2nd Div.)",    11_000, 2.0, 2.75),
    Formation("Orange (1st Div.)",          10_000, 3.5, 3.75),
    Formation("Arnim (2nd Reserve Div.)",    8_000, 4.0, 5.0),
    Formation("Kuhnheim (1st Reserve/Guard)", 8_000, 4.0, None),
]

# ---------------------------------------------------------------------------
# Alternative timeline following D. G. Chandler, "The Campaigns of Napoleon"
# (1966; pp. 489-495 by the book's own index). Chandler's account differs on
# the points that matter most for this model:
#   * 08:00  Schmettau "in position", but the opening is "a skirmish between the
#            light infantry screens" plus Blücher's premature cavalry charges.
#   * 09:30  Wartensleben still coming into line (his column was "badly
#            entangled with convoys of baggage"); Friant deploys at the same time.
#   * 09:45  Schmettau AND Wartensleben "at length advanced to attack".
#   * 11:00  Orange makes "a belated appearance" and splits his division.
#   * The reserve (Chandler: "14 battalions, 5 squadrons and 3 batteries")
#            was not engaged before the withdrawal at 12:30.
# Strengths are kept identical to the timeline above so that only timing differs.
# ---------------------------------------------------------------------------
PRUSSIAN_CHANDLER = [
    Formation("Blücher (advance cavalry)",   2_500, 0.0, 0.0),
    Formation("Schmettau (3rd Div.)",       10_500, 1.0, 2.75),
    Formation("Wartensleben (2nd Div.)",    11_000, 2.5, 2.75),
    Formation("Orange (1st Div.)",          10_000, 3.5, 4.0),
    Formation("Arnim (2nd Reserve Div.)",    8_000, 4.0, None),
    Formation("Kuhnheim (1st Reserve/Guard)", 8_000, 4.0, None),
]

TIMELINES = {
    "Online sources": PRUSSIAN,
    "Chandler (1966)": PRUSSIAN_CHANDLER,
}

FRENCH_TOTAL = sum(f.strength for f in FRENCH)       # ~27,255
PRUSSIAN_TOTAL = sum(f.strength for f in PRUSSIAN)   # 50,000 (conservative)
# Cross-checks against Chandler: he gives Davout 27,000 (26,000 in one place)
# and Brunswick's army 60,000 with 230 guns in the text, 50,000 on his map.
# The Monte Carlo below varies the Prussian total between 50,000 and 60,000.

# ---------------------------------------------------------------------------
# Casualties (killed + wounded)
#   French: Davout reported 258 officers + 6,794 men = 7,052 (whole day).
#             (Chandler gives the same 258 + 6,794, and >40% loss in Gudin's division.)
#   Prussian: estimates range ~10,000 (Davout's estimate, via Petre; Chandler
#             also gives 10,000 "killed" + 3,000 prisoners + 115 guns)
#             to ~15,000 (Rickard), plus ~3,000 prisoners.
# The model is calibrated to the main action, which ended with the Prussian
# withdrawal around 12:30 (t = 5.5); some losses came later in the pursuit,
# hence the calibration targets below are ranges, not single numbers.
# ---------------------------------------------------------------------------
HISTORICAL_END = 5.5                       # 12:30
FRENCH_LOSS_RANGE = (5_600, 7_052)
PRUSSIAN_LOSS_RANGE = (9_000, 13_000)
FRENCH_LOSS_CENTRAL = 6_500
PRUSSIAN_LOSS_CENTRAL = 11_000
