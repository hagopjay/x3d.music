"""Mix recipes: what each piece wants from the mixing machinery in mix.py. One dict per piece.

A recipe is  {"qpm": the beat the delay follows, "stems": {instrument: {chain, level, gain, pan, duck, sends, bus}}, "returns": {space: dB}, "drum_bus": factory, "master_chain": factory}.
  chain   a factory for the instrument's pedalboard (a fresh board per mix, so no state carries over)
  level   the stem's integrated loudness in LUFS at its fader, after the chain, before ducking and panning
  duck    how far the kick pulls the stem down (0.3 is about -3 dB at each kick, recovering with a time constant of 0.12 s)
  pan     balance, -1 left to +1 right      sends  {space: dB} to the hall, room, plate (gated on the snare and clap) and delay      bus   "drums" glues the stem with the kit
Levels are chosen by the numbers in docs/MIX.md (band balance, loudness range, correlation) and not by ear: no ear was available to the build.
"""
from pedalboard import (Chorus, Compressor, Distortion, HighpassFilter, HighShelfFilter, LowpassFilter, LowShelfFilter, PeakFilter, Pedalboard)


def board(*fx):
    return Pedalboard(list(fx))


def _comp(th, ratio, att, rel):
    return Compressor(threshold_db=th, ratio=ratio, attack_ms=att, release_ms=rel)


TURCA = {
    "qpm": 126,
    "stems": {
        "pno":      dict(chain=lambda: board(HighpassFilter(32), PeakFilter(280, -1.5, 0.9), PeakFilter(4000, -1.5, 0.9), HighShelfFilter(9000, 1.0), _comp(-26, 2.0, 25, 180)),
                         level=-18.0, crest=19.0, pan=0.0, sends=dict(hall=-12, room=-18, delay=-26)),
        "kick":     dict(chain=lambda: board(HighpassFilter(38), HighpassFilter(38), LowShelfFilter(55, -2.5), PeakFilter(85, 2.0, 1.0), PeakFilter(350, -3.0, 1.0), PeakFilter(4000, 2.0, 1.0), _comp(-20, 3.0, 12, 90)),
                         level=-20.0, crest=15.0, pan=0.0, sends=dict(room=-24), bus="drums"),
        "snare":    dict(chain=lambda: board(HighpassFilter(110), PeakFilter(200, 1.5, 1.0), PeakFilter(5500, 1.5, 0.9), _comp(-22, 3.0, 6, 80)),
                         level=-21.0, crest=16.0, pan=0.0, sends=dict(plate=-3, room=-12), bus="drums"),
        "clap":     dict(chain=lambda: board(HighpassFilter(350), PeakFilter(1800, 2.0, 1.0)),
                         level=-26.0, crest=16.0, pan=0.0, sends=dict(plate=-6, room=-14), bus="drums"),
        "hat":      dict(chain=lambda: board(HighpassFilter(600), LowpassFilter(15000), HighShelfFilter(9000, -1.0)),
                         level=-31.0, crest=14.0, pan=0.25, sends=dict(room=-22), bus="drums"),
        "tom":      dict(chain=lambda: board(HighpassFilter(60), PeakFilter(300, -2.5, 1.0), _comp(-22, 3.0, 5, 120)),
                         level=-25.0, crest=15.0, pan=-0.3, sends=dict(room=-12, plate=-10), bus="drums"),
        "davul":    dict(chain=lambda: board(HighpassFilter(48), HighpassFilter(48), PeakFilter(250, -2.0, 1.0), LowpassFilter(6000)),
                         level=-23.0, crest=15.0, pan=0.0, sends=dict(hall=-18), bus="drums"),
        "cymbal":   dict(chain=lambda: board(HighpassFilter(500), LowpassFilter(15000)),
                         level=-31.0, crest=15.0, pan=-0.3, sends=dict(hall=-10)),
        "triangle": dict(chain=lambda: board(HighpassFilter(1200)),
                         level=-31.0, crest=15.0, pan=0.35, sends=dict(hall=-14, delay=-18)),
        "jingle":   dict(chain=lambda: board(HighpassFilter(1500), LowpassFilter(14000)),
                         level=-35.0, crest=15.0, pan=-0.4, sends=dict(hall=-16)),
        "bass":     dict(chain=lambda: board(Distortion(8.0), HighpassFilter(36), HighpassFilter(36), LowShelfFilter(60, -4.0), LowpassFilter(2500), _comp(-22, 4.0, 8, 100), HighpassFilter(24)),      # the last high-pass takes out the DC that the saturation and the compressor leave in a saw-based bass
                         level=-21.0, crest=11.0, pan=0.0, duck=0.35),
        "pad":      dict(chain=lambda: board(HighpassFilter(220), LowpassFilter(9500), Chorus(rate_hz=0.35, depth=0.3, centre_delay_ms=9.0, mix=0.5)),
                         level=-28.0, crest=13.0, pan=0.0, duck=0.5, sends=dict(hall=-8)),
        "brass":    dict(chain=lambda: board(HighpassFilter(170), PeakFilter(2500, -1.5, 1.0), PeakFilter(4300, -3.0, 1.2), LowpassFilter(9500), _comp(-22, 2.5, 12, 120), Chorus(rate_hz=0.5, depth=0.2, centre_delay_ms=8.0, mix=0.25)),
                         level=-24.0, crest=15.0, pan=0.0, duck=0.25, sends=dict(hall=-9, room=-16)),
    },
    "returns": dict(hall=0.0, room=0.0, plate=0.0, delay=0.0),
    # the dynamic arc: the loudness each pass of the form should have, relative to the others (LUFS before mastering): a soft opening, the C and F refrains lifting, the D and G breaks pulling back, the Janissary refrain and the coda the top
    "arc": {"A1": -20.0, "A2": -18.5, "B1": -17.5, "B2": -16.0, "C1": -13.5, "C2": -13.0, "D1": -19.0, "D2": -18.5, "E1": -15.5, "E2": -15.0, "F1": -12.5, "F2": -12.0,
            "G1": -19.0, "G2": -17.5, "H1": -16.0, "H2": -14.0, "I1": -11.5, "I2": -11.0, "J1": -10.5},
    "drum_bus": lambda: board(_comp(-16, 2.0, 28, 140), LowShelfFilter(70, 0.8)),
    "master_chain": lambda: board(HighpassFilter(28), HighpassFilter(28), LowShelfFilter(110, 0.5), PeakFilter(300, -0.8, 0.8), HighShelfFilter(7500, 1.0), _comp(-20, 1.4, 30, 220)),
}

ODE = {
    "qpm": 116,
    "stems": {
        "strings": dict(chain=lambda: board(HighpassFilter(90), PeakFilter(300, -1.5, 0.9), LowpassFilter(8500), _comp(-24, 2.0, 25, 200)),
                        level=-22.0, crest=15.0, pan=0.0, sends=dict(hall=-7, room=-18)),
        "bass":    dict(chain=lambda: board(Distortion(8.0), HighpassFilter(36), HighpassFilter(36), LowShelfFilter(60, -4.0), LowpassFilter(2500), _comp(-22, 4.0, 8, 100), HighpassFilter(24)),      # the last high-pass takes out the DC that the saturation and the compressor leave in a saw-based bass
                        level=-21.0, crest=11.0, pan=0.0, duck=0.35),
        "ep":      dict(chain=lambda: board(HighpassFilter(80), PeakFilter(300, -1.5, 0.9), HighShelfFilter(9000, -1.0), _comp(-26, 2.0, 20, 160), Chorus(rate_hz=0.6, depth=0.2, centre_delay_ms=8.0, mix=0.3)),
                        level=-24.0, crest=17.0, pan=-0.2, sends=dict(hall=-11, delay=-22)),
        "lead":    dict(chain=lambda: board(HighpassFilter(180), PeakFilter(3800, -1.5, 1.0), LowpassFilter(10000), _comp(-24, 2.5, 15, 140)),
                        level=-22.0, crest=15.0, pan=0.08, sends=dict(delay=-13, hall=-11)),
        "brass":   dict(chain=lambda: board(HighpassFilter(170), PeakFilter(2500, -1.5, 1.0), PeakFilter(4300, -3.0, 1.2), LowpassFilter(9500), _comp(-22, 2.5, 12, 120),
                                            Chorus(rate_hz=0.5, depth=0.2, centre_delay_ms=8.0, mix=0.25)),
                        level=-24.0, crest=15.0, pan=0.0, duck=0.25, sends=dict(hall=-9, room=-16)),
        "choir":   dict(chain=lambda: board(HighpassFilter(200), LowpassFilter(7500), _comp(-24, 2.0, 30, 220)),
                        level=-27.0, crest=14.0, pan=0.0, sends=dict(hall=-5)),
        "pad":     dict(chain=lambda: board(HighpassFilter(200), LowpassFilter(9500), Chorus(rate_hz=0.35, depth=0.3, centre_delay_ms=9.0, mix=0.5)),
                        level=-29.0, crest=13.0, pan=0.0, duck=0.4, sends=dict(hall=-8)),
        "timp":    dict(chain=lambda: board(HighpassFilter(38), HighpassFilter(38), PeakFilter(250, -2.0, 1.0), _comp(-22, 2.5, 8, 140)),
                        level=-24.0, crest=15.0, pan=0.0, sends=dict(hall=-8, room=-14)),
        "kick":    dict(chain=lambda: board(HighpassFilter(38), HighpassFilter(38), LowShelfFilter(55, -2.5), PeakFilter(85, 2.0, 1.0), PeakFilter(350, -3.0, 1.0), PeakFilter(4000, 2.0, 1.0), _comp(-20, 3.0, 12, 90)),
                        level=-20.0, crest=15.0, pan=0.0, sends=dict(room=-24), bus="drums"),
        "snare":   dict(chain=lambda: board(HighpassFilter(110), PeakFilter(200, 1.5, 1.0), PeakFilter(5500, 1.5, 0.9), _comp(-22, 3.0, 6, 80)),
                        level=-21.0, crest=16.0, pan=0.0, sends=dict(plate=-3, room=-12), bus="drums"),
        "clap":    dict(chain=lambda: board(HighpassFilter(350), PeakFilter(1800, 2.0, 1.0)),
                        level=-26.0, crest=16.0, pan=0.0, sends=dict(plate=-6, room=-14), bus="drums"),
        "hat":     dict(chain=lambda: board(HighpassFilter(600), LowpassFilter(15000), HighShelfFilter(9000, -1.0)),
                        level=-31.0, crest=14.0, pan=0.25, sends=dict(room=-22), bus="drums"),
        "tom":     dict(chain=lambda: board(HighpassFilter(60), PeakFilter(300, -2.5, 1.0), _comp(-22, 3.0, 5, 120)),
                        level=-25.0, crest=15.0, pan=-0.3, sends=dict(room=-12, plate=-10), bus="drums"),
        "rim":     dict(chain=lambda: board(HighpassFilter(400), LowpassFilter(12000)),
                        level=-27.0, crest=14.0, pan=-0.15, sends=dict(room=-10, plate=-12), bus="drums"),
        "cymbal":  dict(chain=lambda: board(HighpassFilter(500), LowpassFilter(15000)),
                        level=-30.0, crest=15.0, pan=-0.3, sends=dict(hall=-9)),
        "clatter": dict(chain=lambda: board(HighpassFilter(800), LowpassFilter(12000), _comp(-24, 2.0, 5, 80)),
                        level=-29.0, crest=14.0, pan=0.3, sends=dict(hall=-11, delay=-16, room=-12)),
    },
    "returns": dict(hall=0.0, room=0.0, plate=0.0, delay=0.0),
    # the dynamic arc: the loom wakes quietly, the theme alone, the groove arriving, gold, the tutti, and the coda holding the top until its one hit
    "arc": {"Intro1": -24.0, "S11": -21.0, "S21": -17.5, "S31": -14.0, "S41": -11.5, "Coda1": -11.5},
    "drum_bus": lambda: board(_comp(-16, 2.0, 28, 140), LowShelfFilter(70, 0.8)),
    "master_chain": lambda: board(HighpassFilter(28), HighpassFilter(28), LowShelfFilter(110, 0.5), PeakFilter(300, -0.8, 0.8), HighShelfFilter(7500, 1.0), _comp(-20, 1.4, 30, 220)),
}

RECIPES = {"turca": TURCA, "ode": ODE}
