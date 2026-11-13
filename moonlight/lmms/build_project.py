#!/usr/bin/env python3
"""
Moonlight // Two Ways  --  score-to-LMMS project generator.

Beethoven, Piano Sonata No. 14 in C# minor, Op. 27 No. 2
  Act I   : I.  Adagio sostenuto, bars 1-9        (quarter = 56)
  bridge  : timpani roll on G# (V) + noise riser, accelerando
  Act II  : III. Presto agitato, bars 1-64        (quarter = 168)
  Coda    : III. Presto agitato, bars 191-201

One global tempo of 168 BPM. The Adagio is written at 3x note values, so
Adagio quarter = 56 exactly (3:1 metric modulation): the Adagio's triplet
pulse becomes the Presto's quarter-note beat.

Input : JSON note events produced by moonlight/score/extract.py (music21 parse of
        Craig Sapp's Humdrum encoding of the Durand 1915 edition).
Output: an LMMS project (.mmp, plain XML, file-format version 31).
"""
import json, math, random, sys
import xml.etree.ElementTree as ET
from collections import defaultdict

TPQ = 48                     # LMMS ticks per quarter note (192 per 4/4 bar)
BPM = 168
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

# ---- timeline (in LMMS quarter notes) -------------------------------------
ADAGIO_X = 3                 # Adagio note values are stretched 3x
A_START = 0
A_LEN = 36 * ADAGIO_X        # 9 bars of 4 quarters -> 108 Q
BR_START = A_START + A_LEN   # bridge: 2 bars
BR_LEN = 8
P_START = BR_START + BR_LEN  # Presto bars 1-64 -> 256 Q
P_LEN = 256
C_START = P_START + P_LEN    # Coda bars 191-201 -> 41 Q
C_LEN = 41
SONG_END = C_START + C_LEN + 8

DYN = {"ppp": 38, "pp": 46, "p": 58, "mp": 64, "mf": 78, "f": 98, "ff": 114, "fff": 124}

rng = random.Random(1801)    # year of composition; deterministic humanisation


def T(q):
    return int(round(q * TPQ))


# ---- id allocation for automatable models ---------------------------------
_next_id = [4_100_000]


def new_id():
    _next_id[0] += 1
    return _next_id[0]


# ---- score loading ---------------------------------------------------------
def load(path):
    o = json.load(open(path))
    for h in ("LH", "RH"):
        o[h] = [e for e in o[h] if e["d"] > 0]          # drop grace notes
    return o


def dyn_at(dyn, t):
    """Most recent non-accent dynamic level at score time t."""
    lvl = 52
    for (dt, v) in dyn:
        if dt > t + 1e-6:
            break
        if v in DYN:
            lvl = DYN[v]
    return lvl


def sf_at(dyn, t):
    return any(abs(dt - t) < 1e-6 and v in ("sf", "sfz", "fz") for dt, v in dyn)


# ---- XML builders ----------------------------------------------------------
def el(parent, tag, **attrs):
    e = ET.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k.replace("_", "-") if k in ("chord_enabled", "arp_enabled") else k, str(v))
    return e


def env(parent, tag, att=0.0, hold=0.0, dec=0.5, sus=1.0, rel=0.1, amt=1.0):
    return el(parent, tag, pdel=0, att=att, hold=hold, dec=dec, sustain=sus, rel=rel,
              amt=amt, lpdel=0, latt=0, lspd=0.1, lamt=0, lshp=0, x100=0, ctlenvamt=0)


import os
TRIMS = json.load(open(os.environ["TRIMS"])) if os.environ.get("TRIMS") else {}
NO_MASTER = bool(os.environ.get("NO_MASTER"))
_track_key = {}


def instrument_track(key, tc, name, mixch, plugin_el_builder, vol=100, pan=0,
                     volenv=None, filt=None, color=None):
    trim_db = TRIMS.get(key, 0.0)
    vol = max(1, min(200, round(vol * 10 ** (trim_db / 20))))
    tr = el(tc, "track", type=0, name=name, muted=0, solo=0)
    if color:
        tr.set("color", color)
    it = el(tr, "instrumenttrack", vol=vol, pan=pan, mixch=mixch, pitch=0,
            pitchrange=1, basenote=69, usemasterpitch=1)
    ins = el(it, "instrument", name=plugin_el_builder[0])
    plugin_el_builder[1](ins)
    ed = el(it, "eldata", fcut=(filt or {}).get("fcut", 14000), ftype=(filt or {}).get("ftype", 0),
            fres=(filt or {}).get("fres", 0.5), fwet=1 if filt else 0)
    if volenv:
        env(ed, "elvol", **volenv)
    else:
        env(ed, "elvol", amt=0)
    if filt and "cutenv" in filt:
        env(ed, "elcut", **filt["cutenv"])
    else:
        env(ed, "elcut", amt=0)
    env(ed, "elres", amt=0)
    el(it, "chordcreator", chord_enabled=0, chord=0, chordrange=1)
    el(it, "arpeggiator", arp_enabled=0)
    el(it, "midiport", basevelocity=127, inputchannel=0, outputchannel=1, readable=0,
       writable=0, fixedinputvelocity=-1, fixedoutputvelocity=-1, fixedoutputnote=-1,
       outputprogram=1, inputcontroller=0, outputcontroller=0)
    el(it, "fxchain", numofeffects=0, enabled=0)
    return tr


def sf2(patch, bank=0, gain=1.0):
    def b(ins):
        el(ins, "sf2player", src=SF2, patch=patch, bank=bank, gain=gain,
           reverbOn=0, chorusOn=0)
    return ("sf2player", b)


def triple(oscs, **extra):
    """oscs: list of 3 dicts with wave, vol, coarse, finel, finer, pan."""
    def b(ins):
        a = {}
        for i, o in enumerate(oscs):
            a.update({f"wavetype{i}": o.get("wave", 0), f"vol{i}": o.get("vol", 33),
                      f"coarse{i}": o.get("coarse", 0), f"finel{i}": o.get("finel", 0),
                      f"finer{i}": o.get("finer", 0), f"pan{i}": o.get("pan", 0),
                      f"phoffset{i}": o.get("ph", 0), f"stphdetun{i}": o.get("stph", 0),
                      f"userwavefile{i}": ""})
        for i in (1, 2, 3):
            a[f"modalgo{i}"] = 2
            a[f"useWaveTable{i}"] = 1
        a.update(extra)
        el(ins, "tripleoscillator", **a)
    return ("tripleoscillator", b)


def kicker(**k):
    def b(ins):
        el(ins, "kicker", **k)
    return ("kicker", b)


def afp(src, amp=100, **k):
    def b(ins):
        el(ins, "audiofileprocessor", src=src, amp=amp, reversed=0, looped=0,
           sframe=0, eframe=1, lframe=0, stutter=0, interp=1, **k)
    return ("audiofileprocessor", b)


LB302_CUT_ID = new_id()


def lb302():
    def b(ins):
        e = el(ins, "lb302", vcf_res=0.62, vcf_mod=0.55, vcf_dec=0.22, dist=0.22,
               shape=8, slide_dec=0.6, slide=0, dead=0, db24=1)
        el(e, "vcf_cut", id=LB302_CUT_ID, value=0.25)
    return ("lb302", b)


def clip(track, name, start_q, len_q, notes):
    """notes: list of (q_pos_abs, q_len, midi, vel127, pan)."""
    mc = el(track, "midiclip", pos=T(start_q), len=T(len_q), type=1, name=name,
            muted=0, steps=16, autoresize=0, off=0)
    for (q, ql, m, v, pan) in sorted(notes):
        rel = T(q) - T(start_q)
        ln = max(1, T(ql))
        vol = max(1, min(200, int(round(v * 100 / 127))))
        el(mc, "note", pos=rel, len=ln, key=int(m), vol=vol, pan=pan, type=0)
    return mc


# ---- effects ---------------------------------------------------------------
def fxchain(parent, effects):
    fc = el(parent, "fxchain", numofeffects=len(effects), enabled=1 if effects else 0)
    for (name, ctl_tag, params, wet) in effects:
        e = el(fc, "effect", name=name, on=1, wet=wet, gate=0, autoquit=1,
               autoquit_numerator=4, autoquit_denominator=4, autoquit_syncmode=0)
        el(e, ctl_tag, **params)
        el(e, "key")
    return fc


def eq(hp=30, lp=None, low_shelf=None, high_shelf=None, peaks=(), out=0.0):
    p = dict(Inputgain=0, Outputgain=out, HPactive=1, HPfreq=hp, HP=1, HP12=0, HP24=1, HP48=0,
             LPactive=1 if lp else 0, LPfreq=lp or 18000, LP=1, LP12=0, LP24=1, LP48=0,
             AnalyseIn=0, AnalyseOut=0)
    if low_shelf:
        p.update(Lowshelfactive=1, LowShelffreq=low_shelf[0], Lowshelfgain=low_shelf[1])
    if high_shelf:
        p.update(Highshelfactive=1, Highshelffreq=high_shelf[0], HighShelfgain=high_shelf[1])
    for i, (f, g, bw) in enumerate(peaks, 1):
        p.update({f"Peak{i}active": 1, f"Peak{i}freq": f, f"Peak{i}gain": g, f"Peak{i}bw": bw})
    return ("eq", "Eq", p, 1)


def comp(threshold=-12, ratio=3, attack=10, release=120, knee=6, out=0, limiter=0,
         lookahead=0, mix=100, peakmode=0, ingain=0, rms=64):
    return ("compressor", "CompressorControls",
            dict(threshold=threshold, ratio=ratio, attack=attack, release=release, knee=knee,
                 hold=0, range=-240, rms=rms, midside=0, peakmode=peakmode, lookaheadLength=3,
                 inBalance=0, outBalance=0, limiter=limiter, outGain=out, inGain=ingain, blend=0,
                 stereoBalance=0, autoMakeup=0, audition=0, feedback=0, autoAttack=0,
                 autoRelease=0, lookahead=lookahead, tilt=0, tiltFreq=150, stereoLink=1,
                 mix=mix), 1)


def reverb(size=0.88, color=9500, out=0):
    return ("reverbsc", "ReverbSCControls",
            dict(input_gain=0, size=size, color=color, output_gain=out), 1)


def delay(secs, fb, wet, out=0):
    return ("delay", "Delay", dict(DelayTimeSamples=secs, FeebackAmount=fb,
                                   LfoFrequency=0.2, LfoAmount=0.0004, OutGain=out), wet)


# ===========================================================================
def build(adagio, presto, coda):
    root = ET.Element("lmms-project", version="31", creator="LMMS",
                      creatorversion="1.3.0", type="song")
    head = el(root, "head", timesig_numerator=4, timesig_denominator=4,
              mastervol=100, masterpitch=0)
    BPM_ID = new_id()
    el(head, "bpm", id=BPM_ID, value=BPM)
    song = el(root, "song")
    tc = el(song, "trackcontainer", type="song", visible=1, x=5, y=5, width=900,
            height=600, maximized=1, minimized=0)

    # mixer channel map
    CH = dict(piano=1, synth=2, orch=3, bass=4, drums=5, riser=6, hall=7)

    # ------------------------------------------------------------------ tracks
    trk = {}
    trk["piano"] = instrument_track("piano", tc, "Piano | Beethoven (complete score)", CH["piano"],
                                    sf2(0), vol=100, color="#e8d9b5")
    trk["glass"] = instrument_track("glass", tc, "Glass Arp | Adagio triplets +8va", CH["synth"],
                                    triple([dict(wave=1, vol=40), dict(wave=0, vol=22, coarse=12),
                                            dict(wave=2, vol=6, coarse=12, finel=7, finer=-7)]),
                                    vol=46, volenv=dict(att=0.0, hold=0.0, dec=0.42, sus=0.0, rel=0.35),
                                    filt=dict(ftype=0, fcut=5200, fres=0.9), color="#7fd3ff")
    trk["choir"] = instrument_track("choir", tc, "Choir | Adagio harmony", CH["orch"], sf2(52),
                                    vol=48, color="#c7b8ff")
    trk["strings"] = instrument_track("strings", tc, "Strings | melody", CH["orch"], sf2(49),
                                      vol=70, color="#ffb37f")
    trk["sub"] = instrument_track("sub", tc, "Sub | Adagio bass", CH["bass"],
                                  triple([dict(wave=0, vol=70), dict(wave=1, vol=0), dict(wave=0, vol=0)]),
                                  vol=62, volenv=dict(att=0.12, hold=0.6, dec=0.6, sus=0.85, rel=0.45),
                                  color="#ff6b8b")
    trk["acid"] = instrument_track("acid", tc, "Acid 303 | Presto arpeggios", CH["synth"], lb302(),
                                   vol=34, color="#b6ff5c")
    trk["reese"] = instrument_track("reese", tc, "Reese Bass | Presto LH", CH["bass"],
                                    triple([dict(wave=2, vol=36, finel=-9, finer=-11),
                                            dict(wave=2, vol=36, finel=9, finer=11, ph=90),
                                            dict(wave=0, vol=60)]),
                                    vol=58, volenv=dict(att=0.0, hold=0.0, dec=0.35, sus=0.75, rel=0.12),
                                    filt=dict(ftype=6, fcut=620, fres=0.35,
                                              cutenv=dict(att=0, hold=0, dec=0.25, sus=0.0, rel=0.1, amt=0.35)),
                                    color="#ff3b6b")
    trk["brass"] = instrument_track("brass", tc, "Brass | sf hits", CH["orch"], sf2(61), vol=74, color="#ffd34d")
    trk["timp"] = instrument_track("timp", tc, "Timpani", CH["orch"], sf2(47), vol=92, color="#d6a36b")
    trk["kick"] = instrument_track("kick", tc, "Kick", CH["drums"],
                                   kicker(startfreq=190, endfreq=46, decay=330, dist=2.5, distend=0.8,
                                          gain=1.0, env=0.12, noise=0.0, click=0.45, slope=0.07,
                                          startnote=0, endnote=0, version=1), vol=92, color="#9aa4b1")
    trk["heart"] = instrument_track("heart", tc, "Heartbeat | alla breve", CH["drums"],
                                    kicker(startfreq=95, endfreq=38, decay=420, dist=0.4, distend=0.2,
                                           gain=1.0, env=0.2, noise=0.0, click=0.05, slope=0.12,
                                           startnote=0, endnote=0, version=1), vol=78, color="#9aa4b1")
    trk["snare"] = instrument_track("snare", tc, "Snare", CH["drums"], afp("drums/snare_electro01.ogg"),
                                    vol=72, color="#9aa4b1")
    trk["hat"] = instrument_track("hat", tc, "Hats", CH["drums"], afp("drums/hihat_closed02.ogg"),
                                  vol=46, pan=8, color="#9aa4b1")
    trk["ohat"] = instrument_track("ohat", tc, "Open Hat", CH["drums"], afp("drums/hihat_opened02.ogg"),
                                   vol=34, pan=8, color="#9aa4b1")
    trk["crash"] = instrument_track("crash", tc, "Crash", CH["drums"], afp("drums/crash01.ogg"),
                                    vol=46, pan=-10, color="#9aa4b1")
    trk["riser"] = instrument_track("riser", tc, "Riser | noise", CH["riser"],
                                    triple([dict(wave=6, vol=60), dict(wave=6, vol=0), dict(wave=6, vol=0)]),
                                    vol=40, volenv=dict(att=0.78, hold=0.0, dec=0.1, sus=1.0, rel=0.05),
                                    filt=dict(ftype=2, fcut=600, fres=1.6,
                                              cutenv=dict(att=0.8, hold=0, dec=0.1, sus=1.0, rel=0.05, amt=0.9)),
                                    color="#ffffff")
    notes = defaultdict(list)   # key -> list of (section, q, ql, m, v, pan)

    def add(key, section, q, ql, m, v, pan=0):
        notes[key].append((section, q, ql, m, max(1, min(127, int(v))), pan))

    # ============================================================== ACT I
    A = adagio
    def aq(t):
        return A_START + t * ADAGIO_X
    for h in ("LH", "RH"):
        for e in A[h]:
            t, d, m = e["t"], e["d"], e["m"]
            base = dyn_at(A[h + "_dyn"], t)
            triplet = abs(d - 1 / 3) < 0.02
            if h == "LH":
                v = base + 4
            elif triplet:
                pos_in_group = round((t * 3) % 3)
                v = base - 6 + (5 if pos_in_group == 0 else 0)
            else:                                   # melody: voice it on top
                v = base + 22
            v += rng.randint(-3, 3)
            ql = d * ADAGIO_X
            if h == "LH" or not triplet:
                ql *= 1.0
            else:
                ql *= 1.6                           # sustain-pedal legato for arpeggio
            add("piano", "A", aq(t), ql, m, v)

    # glass arp: triplets an octave up, from bar 3
    for e in A["RH"]:
        if abs(e["d"] - 1 / 3) < 0.02 and e["t"] >= 8:
            swell = min(1.0, (e["t"] - 8) / 12)
            add("glass", "A", aq(e["t"]), e["d"] * ADAGIO_X * 0.9, e["m"] + 12,
                54 + 30 * swell + rng.randint(-4, 4))

    # melody -> strings (+ octave below) from bar 5
    for e in A["RH"]:
        if abs(e["d"] - 1 / 3) > 0.02 and e["t"] >= 16:
            add("strings", "A", aq(e["t"]), e["d"] * ADAGIO_X, e["m"], 92)
            add("strings", "A", aq(e["t"]), e["d"] * ADAGIO_X, e["m"] - 12, 70)

    # choir: harmony of each Adagio beat (the triplet's pitch set), from bar 3
    beats = defaultdict(set)
    for e in A["RH"]:
        if abs(e["d"] - 1 / 3) < 0.02:
            beats[int(e["t"] + 1e-6)].add(e["m"])
    run = None
    for b in sorted(beats) + [None]:
        cur = tuple(sorted(beats[b])) if b is not None else None
        if run and (cur != run[1] or b != run[0] + run[2]):
            st, ch, n = run
            if st >= 8:
                for m in ch:
                    add("choir", "A", aq(st), n * ADAGIO_X, m, 50 + min(30, (st - 8) * 2.5))
            run = None
        if cur is None:
            break
        run = (run[0], run[1], run[2] + 1) if run else (b, cur, 1)

    # sub: lowest LH note per onset, from bar 5
    lh_on = defaultdict(list)
    for e in A["LH"]:
        lh_on[e["t"]].append(e)
    for t, grp in lh_on.items():
        if t >= 16:
            lo = min(grp, key=lambda e: e["m"])
            m = lo["m"] if lo["m"] < 45 else lo["m"] - 12
            add("sub", "A", aq(t), lo["d"] * ADAGIO_X, m, 100)

    # heartbeat on the alla-breve (2/2) pulse from bar 5: lub (beat) - dub (next triplet)
    for bar in range(5, 10):
        for half in (0, 2):
            t = (bar - 1) * 4 + half
            add("heart", "A", aq(t), 1.0, 36, 104)
            add("heart", "A", aq(t + 1 / 3), 1.0, 36, 70)

    # ============================================================== BRIDGE
    for i in range(32):                     # timpani roll on G#2, 16ths, crescendo
        q = BR_START + i * 0.25
        add("timp", "B", q, 0.3, 44, 34 + i * 2.8 + rng.randint(-4, 4))
    add("riser", "B", BR_START, BR_LEN, 72, 110)
    for m in (56, 59, 64, 68):              # E major chord held as choir swell (III ...)
        add("choir", "B", BR_START, 4, m, 72)
    for m in (56, 60, 63, 68):              # ... turning into G# major (V) for the drop
        add("choir", "B", BR_START + 4, 4, m, 92)
    add("crash", "B", BR_START + BR_LEN - 2, 2, 69, 40)

    # ============================================================== ACT II + CODA
    def presto_layer(S, sec, q0, first_bar, last_bar):
        hits = []
        rh_on = defaultdict(list)
        for e in S["RH"]:
            rh_on[e["t"]].append(e)
        for h in ("LH", "RH"):
            for e in S[h]:
                t, d, m = e["t"], e["d"], e["m"]
                base = dyn_at(S[h + "_dyn"], t)
                v = base + (26 if sf_at(S[h + "_dyn"], t) else 0)
                if h == "RH" and abs(d - 0.25) < 0.01:
                    v += 6 if abs((t * 4) % 4) < 1e-6 else -2   # beat accents in the arpeggio
                v += rng.randint(-3, 3)
                add("piano", sec, q0 + t, d, m, v)
        # acid 303 on the single-line 16ths
        for t, grp in rh_on.items():
            if len(grp) == 1 and abs(grp[0]["d"] - 0.25) < 0.01:
                e = grp[0]
                acc = 112 if abs((t * 4) % 4) < 1e-6 else 84
                add("acid", sec, q0 + t, 0.22, e["m"], acc)
        # brass + timpani on chordal hits (>=3 notes)
        for t, grp in sorted(rh_on.items()):
            if len(grp) >= 3 and grp[0]["d"] <= 1.01:
                v = dyn_at(S["RH_dyn"], t) + (26 if sf_at(S["RH_dyn"], t) else 8)
                for e in grp:
                    add("brass", sec, q0 + t, max(0.45, e["d"] * 0.9), e["m"] - 12, v)
                hits.append(t)
        # strings on sustained RH melody
        for e in S["RH"]:
            if e["d"] >= 0.5 and e["chord"] < 3:
                add("strings", sec, q0 + e["t"], e["d"], e["m"], 82 + (e["d"] >= 1) * 10)
        for e in S["LH"]:
            if e["d"] >= 1.5:
                add("strings", sec, q0 + e["t"], e["d"], e["m"], 72)
        # reese: lowest LH note per 8th window
        win = defaultdict(list)
        for e in S["LH"]:
            win[math.floor(e["t"] * 2 + 1e-6)].append(e)
        for w, grp in sorted(win.items()):
            lo = min(grp, key=lambda e: e["m"])
            m = lo["m"] - 12 if lo["m"] >= 48 else lo["m"]
            dlen = 0.45 if lo["d"] <= 0.5 else min(lo["d"], 2.0)
            add("reese", sec, q0 + w / 2, dlen, m, 100 + (8 if w % 2 == 0 else 0))
        # timpani: LH lowest on each hit, an octave clamped to timp range
        lh_on2 = defaultdict(list)
        for e in S["LH"]:
            lh_on2[e["t"]].append(e)
        for t in hits:
            cands = lh_on2.get(t) or []
            root = min(cands, key=lambda e: e["m"])["m"] if cands else 49
            while root > 52: root -= 12
            while root < 40: root += 12
            add("timp", sec, q0 + t, 0.5, root, 118)
        return hits

    hitsP = presto_layer(presto, "P", P_START, 1, 64)
    hitsC = presto_layer(coda, "C", C_START, 191, 201)

    # ---- drums: DnB two-step at 168, sections follow Beethoven's form
    def bar_q(sec_start, bar_idx):  # bar_idx from 0 within section
        return sec_start + bar_idx * 4

    kick_times = []

    def two_step(q, intensity=1.0, halftime=False, fill=False):
        if halftime:
            add("kick", "D", q, 0.5, 36, 118); kick_times.append(q)
            add("kick", "D", q + 2.5, 0.5, 36, 96); kick_times.append(q + 2.5)
            add("snare", "D", q + 2, 0.5, 69, 112)
        else:
            add("kick", "D", q, 0.5, 36, 120); kick_times.append(q)
            add("kick", "D", q + 2.5, 0.5, 36, 104); kick_times.append(q + 2.5)
            add("snare", "D", q + 1, 0.5, 69, 112)
            add("snare", "D", q + 3, 0.5, 69, 116)
            add("snare", "D", q + 1.75, 0.25, 69, 34)   # ghost
            add("snare", "D", q + 3.75, 0.25, 69, 30)   # ghost
        for i in range(8):
            hv = (78 if i % 2 == 0 else 54) * intensity + rng.randint(-5, 5)
            add("hat", "D", q + i * 0.5, 0.25, 69, hv)
            if intensity > 0.9:
                add("hat", "D", q + i * 0.5 + 0.25, 0.2, 69, 28 + rng.randint(-4, 4))
        if fill:
            for i in range(16):
                add("snare", "D", q + i * 0.25, 0.2, 69, 40 + i * 5)

    for b in range(64):
        bar = b + 1
        q = bar_q(P_START, b)
        if bar <= 4:            # intro: only hats + kick under the arpeggio
            for i in range(8):
                add("hat", "D", q + i * 0.5, 0.25, 69, 40 + i * 2)
            add("kick", "D", q, 0.5, 36, 110); kick_times.append(q)
        elif bar <= 20:
            two_step(q, 1.0, fill=(bar == 20))
        elif bar <= 56:         # second theme (G# minor): halftime, more air
            two_step(q, 0.85, halftime=True, fill=(bar == 56))
        else:                   # closing group + fill into the coda
            two_step(q, 1.0, fill=(bar == 64))
        if bar in (1, 5, 15, 21, 43, 57):
            add("crash", "D", q, 2, 69, 92)
        if bar % 2 == 0 and 5 <= bar <= 64 and not (21 <= bar <= 56):
            add("ohat", "D", q + 3.5, 0.5, 69, 70)

    for b in range(11):
        bar = 191 + b
        q = bar_q(C_START, b)
        if bar <= 198:
            two_step(q, 1.05, fill=(bar == 198))
            if bar in (191, 195):
                add("crash", "D", q, 2, 69, 104)
    for t in hitsC:
        if t >= 32:             # final hammered chords: kick + crash on each
            add("kick", "D", C_START + t, 0.5, 36, 127); kick_times.append(C_START + t)
            add("crash", "D", C_START + t, 3, 69, 110)

    # riser into the coda (bars 63-64)
    add("riser", "D", P_START + 62 * 4, 8, 72, 100)

    # ------------------------------------------------------------------ clips
    sections = {"A": (A_START, A_LEN, "Adagio"), "B": (BR_START, BR_LEN, "Bridge"),
                "P": (P_START, P_LEN, "Presto 1-64"), "C": (C_START, C_LEN + 6, "Coda 191-201")}
    for key, tr in trk.items():
        evs = notes.get(key, [])
        by_sec = defaultdict(list)
        for (sec, q, ql, m, v, pan) in evs:
            if sec == "D":
                sec = "P" if q < C_START else "C"
            by_sec[sec].append((q, ql, m, v, pan))
        for sec, lst in by_sec.items():
            st, ln, label = sections[sec]
            clip(tr, label, st, ln, lst)

    # ------------------------------------------------------------- automation
    def automation(name, obj_id, points, prog=1):
        tr = el(tc, "track", type=5, name=name, muted=0, solo=0)
        el(tr, "automationtrack")
        start = points[0][0]
        end = points[-1][0]
        ac = el(tr, "automationclip", pos=T(start), len=max(T(end - start), 1), name=name,
                prog=prog, tens=1, mute=0, off=0, autoresize=0)
        for (q, v) in points:
            el(ac, "time", pos=T(q) - T(start), value=v, outValue=v, inTan=0, outTan=0, lockedTan=0)
        el(ac, "object", id=obj_id)

    # tempo: ritardando into bar 9's cadence, accelerando through the timpani roll
    automation("Tempo (rit. / accel.)", BPM_ID, [
        (0, 168), (A_START + 32 * 3, 168), (BR_START, 138), (BR_START + 0.01, 138),
        (P_START, 168), (C_START + 36, 168), (C_START + 41, 150)])

    # acid filter: opens across bars 1-14, relaxes for the 2nd theme, screams in the coda
    automation("Acid cutoff", LB302_CUT_ID, [
        (P_START, 0.22), (P_START + 14 * 4, 0.95), (P_START + 20 * 4, 0.8),
        (P_START + 21 * 4, 0.45), (P_START + 56 * 4, 0.6), (P_START + 64 * 4, 1.15),
        (C_START, 1.0), (C_START + 41, 1.25)])

    # bass ducking (poor man's sidechain): dip on each kick, recover over an 8th
    BASS_VOL_ID = new_id()
    pts = [(P_START - 0.01, 1.0)]
    for q in sorted(set(kick_times)):
        if q < P_START:
            continue
        pts += [(q - 0.01, 1.0), (q, 0.32), (q + 0.42, 1.0)]
    pts.append((SONG_END, 1.0))
    # dedupe/monotonic
    clean = []
    for p in sorted(pts):
        if clean and abs(T(p[0]) - T(clean[-1][0])) == 0:
            clean[-1] = p
        else:
            clean.append(p)
    automation("Bass duck (kick sidechain)", BASS_VOL_ID, clean)

    # ------------------------------------------------------------------ mixer
    mixer = el(song, "mixer", visible=1, x=5, y=5, width=900, height=333, maximized=0, minimized=0)

    def channel(num, name, effects, sends, vol=1.0, vol_id=None, color=None):
        mc = el(mixer, "mixerchannel", num=num, name=name, muted=0, soloed=0)
        if color:
            mc.set("color", color)
        fxchain(mc, effects)
        if vol_id:
            el(mc, "volume", id=vol_id, value=vol)
        else:
            mc.set("volume", str(vol))
        for (ch, amt) in sends:
            el(mc, "send", channel=ch, amount=amt)
        return mc

    channel(0, "Master", [] if NO_MASTER else [eq(hp=24, low_shelf=(90, 1.0), high_shelf=(9000, 1.5)),
                          comp(threshold=-14, ratio=2.0, attack=25, release=180, knee=8, out=1.5),
                          comp(threshold=-1.2, ratio=20, attack=0.01, release=50, knee=0, limiter=1,
                               lookahead=1, out=0, peakmode=1, ingain=4.0, rms=1)], [], 1.0)
    PIANO_VOL_ID = new_id()
    automation("Piano lift (Adagio intimacy)", PIANO_VOL_ID, [
        (0, 1.55), (A_START + 16 * 3, 1.55), (BR_START, 1.25), (P_START, 1.0), (SONG_END, 1.0)])
    channel(CH["piano"], "Piano", [eq(hp=38, peaks=[(320, -2.0, 1.0), (3200, 1.5, 1.2)]),
                                   comp(threshold=-22, ratio=3, attack=6, release=140, knee=8, out=3)],
            [(0, 1.0), (CH["hall"], 0.32)], 1.55, vol_id=PIANO_VOL_ID, color="#e8d9b5")
    channel(CH["synth"], "Synths", [eq(hp=180), delay(60 / 56 / 2, 0.38, 0.28)],
            [(0, 1.0), (CH["hall"], 0.28)], 0.8, color="#7fd3ff")
    channel(CH["orch"], "Orchestra", [eq(hp=60, peaks=[(250, -2.5, 1.0)])],
            [(0, 1.0), (CH["hall"], 0.5)], 0.9, color="#ffb37f")
    channel(CH["bass"], "Bass", [eq(hp=28, lp=4200),
                                 comp(threshold=-18, ratio=4, attack=8, release=90, knee=6, out=4)],
            [(0, 1.0)], 1.0, vol_id=BASS_VOL_ID, color="#ff3b6b")
    channel(CH["drums"], "Drums", [eq(hp=30, peaks=[(4500, 1.5, 1.0)]),
                                   comp(threshold=-16, ratio=4, attack=12, release=80, knee=4, out=3)],
            [(0, 1.0), (CH["hall"], 0.08)], 0.9, color="#9aa4b1")
    channel(CH["riser"], "Riser", [eq(hp=300)], [(0, 1.0), (CH["hall"], 0.5)], 0.7)
    channel(CH["hall"], "Hall (send)", [eq(hp=220, lp=9000), reverb(0.9, 8500)], [(0, 1.0)], 0.75,
            color="#c7b8ff")

    el(song, "timeline", lp0pos=0, lp1pos=T(SONG_END), lpstate=0, stopbehaviour=1)
    el(song, "controllers")
    notes_el = el(song, "projectnotes", visible=0, x=5, y=5, width=600, height=400,
                  maximized=0, minimized=0)
    notes_el.text = (
        "<b>Moonlight // Two Ways</b><br>"
        "Beethoven, Piano Sonata No. 14 in C# minor, Op. 27 No. 2 (1801).<br>"
        "Act I: Adagio sostenuto bars 1-9 at quarter=56. Bridge: timpani roll on G# (V). "
        "Act II: Presto agitato bars 1-64 + 191-201 at quarter=168 (3:1 metric modulation).<br>"
        "Score data: Humdrum encoding by Craig Stuart Sapp of the Durand 1915 edition "
        "(github.com/craigsapp/beethoven-piano-sonatas). Generated by build_project.py.")
    return root


def main():
    adagio = load(sys.argv[1]); presto = load(sys.argv[2]); coda = load(sys.argv[3])
    root = build(adagio, presto, coda)
    ET.indent(root, space=" ")
    xml = '<?xml version="1.0"?>\n<!DOCTYPE lmms-project>\n' + ET.tostring(root, encoding="unicode")
    open(sys.argv[4], "w").write(xml)
    n = len(root.findall(".//note"))
    print(f"wrote {sys.argv[4]}: {n} notes, {len(root.findall('.//track'))} tracks, "
          f"{SONG_END / 4:.0f} bars, ~{SONG_END * 60 / BPM:.0f}s at {BPM} BPM (before tempo automation)")


if __name__ == "__main__":
    main()
