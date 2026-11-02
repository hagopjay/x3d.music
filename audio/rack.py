"""The rack: which Faust voice plays which instrument id, and the machinery that renders a card's notes into stems.

Every instrument id on a score card has one stem: the Faust instruments are rendered through DawDreamer (48 kHz, 32-bit float, stereo), the grand piano by the sampler in sampler.py.
Rendering is deterministic: the same card, the same Faust files and the same library versions give the same samples on one machine.
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FAUST = os.path.join(HERE, "faust")
SR = 48000

# voices: simultaneous notes the instrument can hold; tail: seconds a voice keeps ringing after its note ends (the Faust envelope sets the real decay, this only keeps the voice alive)
RACK = {
    "kick": dict(dsp="kick.dsp", voices=4, tail=0.8),
    "snare": dict(dsp="snare.dsp", voices=6, tail=0.6),
    "hat": dict(dsp="hat.dsp", voices=8, tail=0.6),
    "clap": dict(dsp="clap.dsp", voices=4, tail=0.6),
    "tom": dict(dsp="tom.dsp", voices=6, tail=0.8),
    "rim": dict(dsp="rim.dsp", voices=4, tail=0.3),
    "bass": dict(dsp="bass.dsp", voices=4, tail=0.5),
    "pad": dict(dsp="pad.dsp", voices=24, tail=1.4),
    "brass": dict(dsp="brass.dsp", voices=16, tail=0.5),
    "strings": dict(dsp="strings.dsp", voices=24, tail=1.0),
    "ep": dict(dsp="ep.dsp", voices=12, tail=0.6),
    "choir": dict(dsp="choir.dsp", voices=24, tail=1.4),
    "lead": dict(dsp="lead.dsp", voices=6, tail=0.5),
    "timp": dict(dsp="timp.dsp", voices=6, tail=2.0),
    "davul": dict(dsp="davul.dsp", voices=4, tail=1.0),
    "cymbal": dict(dsp="cymbal.dsp", voices=6, tail=3.0),
    "triangle": dict(dsp="triangle.dsp", voices=8, tail=2.0),
    "jingle": dict(dsp="jingle.dsp", voices=6, tail=0.6),
    "clatter": dict(dsp="clatter.dsp", voices=6, tail=0.4),
}


def render_faust(inst, notes, seconds):
    """notes: dicts with pitch, vel, t, dur. Returns float32 (n, 2) of exactly `seconds`."""
    import dawdreamer as daw
    spec = RACK[inst]
    engine = daw.RenderEngine(SR, 512)
    proc = engine.make_faust_processor(inst)
    proc.faust_libraries_path = FAUST
    cwd = os.getcwd()
    os.chdir(FAUST)                                  # the voice files import "common.lib" from their own folder
    try:
        assert proc.set_dsp(os.path.join(FAUST, spec["dsp"])), "Faust could not compile " + spec["dsp"]
    finally:
        os.chdir(cwd)
    proc.num_voices = spec["voices"]
    proc.release_length = spec["tail"]
    for n in notes:
        proc.add_midi_note(int(n["pitch"]), int(n["vel"]), float(n["t"]), max(float(n["dur"]), 0.002))
    engine.load_graph([(proc, [])])
    engine.render(seconds)
    audio = engine.get_audio()
    out = np.zeros((int(round(seconds * SR)), 2), dtype="float32")
    n = min(out.shape[0], audio.shape[1])
    out[:n] = audio[:, :n].T
    return out


def instrument_notes(card):
    """{instrument id: [notes]} for every sounding instrument of a card: the arrangement layer as written, the composer notes through the card's routing."""
    by = {}
    routing = card.get("routing")
    for n in card["notes"]:
        if n["layer"] == "composer" and routing and n["inst"] in routing:
            for r in routing[n["inst"]].get(n["section"], []):
                m = dict(n)
                m.update(inst=r["inst"], pitch=n["pitch"] + 12 * (n.get("oct", 0) + r.get("rel", 0)), vel=max(1, min(127, n["vel"] + r.get("vel", 0))))
                if r.get("dur"):
                    m["dur"] = n["dur"] * r["dur"]
                by.setdefault(r["inst"], []).append(m)
        else:
            by.setdefault(n["inst"], []).append(n)
    return by


def render_stems(card, seconds, grand=None):
    """All stems of a card: {instrument id: float32 (n, 2)}, each exactly `seconds` long."""
    stems = {}
    by = instrument_notes(card)
    for inst in sorted(by):
        if inst == "pno":
            from sampler import Grand
            stems[inst] = (grand or Grand()).render(by[inst], seconds)[: int(round(seconds * SR))]
            if len(stems[inst]) < int(round(seconds * SR)):
                stems[inst] = np.pad(stems[inst], ((0, int(round(seconds * SR)) - len(stems[inst])), (0, 0)))
        else:
            stems[inst] = render_faust(inst, by[inst], seconds)
    return stems
