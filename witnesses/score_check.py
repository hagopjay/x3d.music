#!/usr/bin/env python3
"""The Score witness: do the score cards say what their sources say, and nothing else?

    python3 -I witnesses/score_check.py [--piece turca|ode|all] [--out build/runs/score.json]

For each card (score/<piece>.score.json) it re-derives the expected notes from the source with a different parser from the builder's (music21, plus a tiny line-based reader of the kern file)
and compares them exactly. Pass means: 0 missing, 0 extra; pitch, onset and duration equal as exact fractions of a quarter; seconds equal to the tempo map; ids well formed and unique;
harmony and key map consistent; and the 60 Hz tracks equal to a brute-force recomputation at random samples. Exit 1 on any failure.

check_piece(card, piece, root) returns the results so tests can feed it a damaged card and see it go red. Needs music21 (requirements-score.txt).
"""
import argparse, base64, bisect, functools, hashlib, json, math, os, random, re, struct, sys
from fractions import Fraction as Fr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "score"))
import harmony as H        # shared labelling and tension arithmetic (unit-tested on its own); the parsing below is independent of the builders

ID_RE = re.compile(r"^(?P<piece>[a-z]+)\.(?P<sec>[A-Za-z0-9]+)(?P<rep>[0-9])\.(?P<inst>[a-z0-9]+)\.(?P<voice>[A-Za-z0-9]+)\.(?P<n>[0-9]{4,})$")
GRACE_Q = Fr(1, 8)
FS = 60


class Results(list):
    def add(self, cid, claim, ok, detail=""):
        self.append({"id": cid, "claim": claim, "ok": bool(ok), "detail": detail})


# ---------------------------------------------------------------- exact helpers (re-written here on purpose: the witness does not import the builders' tempo or bar code)
def seconds(tempo, q):
    """tempo = [(q, qpm)] sorted. Exact."""
    t = Fr(0)
    for i, (q0, b) in enumerate(tempo):
        q1 = tempo[i + 1][0] if i + 1 < len(tempo) else None
        if q1 is None or q < q1:
            return t + (q - q0) * 60 / b
        t += (q1 - q0) * 60 / b
    raise AssertionError


def quarters(tempo, t):
    acc = Fr(0)
    for i, (q0, b) in enumerate(tempo):
        q1 = tempo[i + 1][0] if i + 1 < len(tempo) else None
        span = (q1 - q0) * 60 / b if q1 is not None else None
        if span is None or t < acc + span:
            return q0 + (t - acc) * b / 60
        acc += span
    raise AssertionError


def spq(tempo, q):
    b = [bb for qq, bb in tempo if qq <= q][-1]
    return 60 / b


def bar_beat(q, beats, pickup):
    if pickup:
        x = q + (beats - pickup)
        return int(x // beats), x % beats + 1
    return int(q // beats) + 1, q % beats + 1


# ---------------------------------------------------------------- the line-based kern reader (independent of score/kern.py: it follows the left-hand column only)
def kern_independent(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    header = next(l for l in lines if l.startswith("**"))
    assert header.split("\t")[0] == "**kern"
    labels, plan, lh = [], [], Fr(0)
    barlines, offs = [], {}
    for i, l in enumerate(lines, 1):
        if not l or l.startswith("!!"):
            continue
        cols = l.split("\t")
        if l.startswith("*"):
            assert "*^" not in cols[:1], "the left-hand spine splits"
            m = re.match(r"\*>\[([^\]]*)\]", cols[0])
            if m:
                plan = m.group(1).split(",")
            elif re.match(r"\*>[A-Z][0-9]?$", cols[0]):
                labels.append((cols[0][2:], i))
                offs[cols[0][2:]] = lh
            continue
        if l.startswith("="):
            m = re.match(r"=+(\d+)", cols[0])
            barlines.append((i, int(m.group(1)) if m else None, lh))
            continue
        if l.startswith("!"):
            continue
        tok = cols[0]
        if tok == "." or "q" in tok.split(" ")[0]:
            continue
        m = re.search(r"(\d+)(\.*)", tok.split(" ")[0])
        n = int(m.group(1))
        d = Fr(4, n) if n else Fr(8)
        add = d
        for _ in m.group(2):
            add /= 2
            d += add
        lh += d
    return {"lines": lines, "labels": labels, "plan": plan, "end": lh, "offsets": offs, "barlines": barlines}


def pitch_of_token(sub):
    m = re.search(r"([a-g]+|[A-G]+)(#+|-+|n)?", sub)
    letters, acc = m.group(1), m.group(2) or ""
    oct_ = 3 + len(letters) if letters[0].islower() else 4 - len(letters)
    return 12 * (oct_ + 1) + {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[letters[0].lower()] + (acc.count("#") - acc.count("-") if acc != "n" else 0)


# ---------------------------------------------------------------- music21 readers
@functools.lru_cache(maxsize=None)
def m21_turca(path):
    import music21 as m21
    s = m21.converter.parse(path)
    heads = []
    for n in s.recurse().notes:
        off = Fr(n.getOffsetInHierarchy(s)).limit_denominator(1000)
        ql = Fr(n.duration.quarterLength).limit_denominator(1000)
        for p in (n.pitches if n.isChord else [n.pitch]):
            heads.append((off, p.midi, ql, bool(n.duration.isGrace)))
    return heads, Fr(s.highestTime).limit_denominator(1000)


@functools.lru_cache(maxsize=None)
def m21_ode(path):
    """Returns the raw heads: (measure, index, offset, midi, ql, tie) for every note, in order. No repeats expanded, no ties merged."""
    import music21 as m21
    s = m21.converter.parse(path)
    out = []
    part = s.parts[0]
    for m in part.getElementsByClass(m21.stream.Measure):
        idx = 0
        for el in m.notesAndRests:
            idx += 1
            if el.isRest:
                continue
            tie = el.tie.type if el.tie is not None else None
            out.append((m.number, idx, Fr(el.getOffsetInHierarchy(s)).limit_denominator(1000), el.pitch.midi, Fr(el.duration.quarterLength).limit_denominator(1000), tie))
    reps = []
    for m in part.getElementsByClass(m21.stream.Measure):
        for b in (m.leftBarline, m.rightBarline):
            if isinstance(b, m21.bar.Repeat):
                reps.append((m.number, b.direction))
    return out, reps, Fr(s.highestTime).limit_denominator(1000)


def merge_ties_m21(raw, a, b):
    """Heads whose onset is in [a, b), with tied chains merged when the whole chain lies inside; returns [(measure, index, offset, midi, ql)]."""
    out, open_ = [], {}
    for meas, idx, off, midi, ql, tie in raw:
        if not (a <= off < b):
            continue
        if tie in ("stop", "continue") and midi in open_:
            i = open_[midi]
            o = out[i]
            out[i] = (o[0], o[1], o[2], o[3], o[4] + ql)
            if tie == "stop":
                del open_[midi]
            continue
        out.append((meas, idx, off, midi, ql))
        if tie in ("start", "continue"):
            open_[midi] = len(out) - 1
    return out


# ---------------------------------------------------------------- the checks
def common_checks(card, piece, R):
    notes = [n for n in card["notes"] if n["layer"] == "composer"]
    tempo = [(Fr(e["q"]), Fr(e["qpm"])) for e in card["tempo_map"]]
    beats = int(card["meter"].split("/")[0])
    first = card["tempo_map"][0]
    pickup = (beats - (int(first["beat"]) - 1)) % beats if first["bar"] == 0 else 0
    # ids
    ids = [n["id"] for n in card["notes"]]
    bad = [i for i in ids if not ID_RE.match(i)]
    R.add("S6a", "every note id has the form <piece>.<section><rep>.<instrument>.<voice>.<counter> and is unique", not bad and len(set(ids)) == len(ids),
          "%d notes, %d unique, %d malformed" % (len(ids), len(set(ids)), len(bad)))
    # counters gapless per (section+rep, inst, voice) in the order of the file, and fields agree with the id
    groups, mism = {}, 0
    for n in card["notes"]:
        m = ID_RE.match(n["id"])
        if not m:
            continue
        if (m["piece"], m["sec"], int(m["rep"]), m["inst"], m["voice"]) != (card["piece"], n["section"], n["rep"], n["inst"], n["voice"]):
            mism += 1
        groups.setdefault((m["sec"], m["rep"], m["inst"], m["voice"]), []).append(int(m["n"]))
    gaps = [k for k, v in groups.items() if sorted(v) != list(range(1, len(v) + 1))]
    R.add("S6b", "counters run 1..n without gaps in each (section pass, instrument, voice), and section, rep, instrument and voice agree with the id", not gaps and not mism,
          "%d groups, %d with gaps, %d fields disagreeing" % (len(groups), len(gaps), mism))
    # seconds from the tempo map
    worst, worst_id = 0.0, None
    gsize = {}
    for n in notes:
        if n.get("g"):
            key = (n["section"], n["rep"], n["voice"], n["q"])
            gsize.setdefault(key, []).append(n)
    for n in notes:
        q = Fr(n["q"])
        if n.get("g"):
            grp = gsize[(n["section"], n["rep"], n["voice"], n["q"])]
            i = [x["id"] for x in grp].index(n["id"])
            g = GRACE_Q * spq(tempo, q)
            want_t = seconds(tempo, q) - (len(grp) - i) * g
            want_d = g
        else:
            want_t = seconds(tempo, q)
            want_d = seconds(tempo, q + Fr(n["ql"])) - want_t
        e = max(abs(float(want_t) - n["t"]), abs(float(want_d) - n["dur"]))
        if e > worst:
            worst, worst_id = e, n["id"]
    R.add("S4", "t and dur of every composer note equal the tempo map (graces: a 32nd per grace, just before the beat) within 0.6 microseconds", worst <= 6e-7, "worst error %.2e s at %s" % (worst, worst_id))
    # bar and beat
    bad = [n["id"] for n in notes if (lambda bb: (bb[0], float(bb[1])) != (n["bar"], n["beat"]))(bar_beat(Fr(n["q"]), beats, pickup))]
    bad = [i for i in bad][:3]
    R.add("S5", "bar and beat of every composer note follow from its performed quarter position", not bad, "first mismatches: %s" % bad if bad else "%d notes" % len(notes))
    # form
    form = card["form"]
    contiguous = all(Fr(form[i]["q1"]) == Fr(form[i + 1]["q0"]) for i in range(len(form) - 1)) and Fr(form[0]["q0"]) == 0
    tdiff = max(abs(float(seconds(tempo, Fr(f["q0"]))) - f["t0"]) for f in form)
    tdiff = max(tdiff, max(abs(float(seconds(tempo, Fr(f["q1"]))) - f["t1"]) for f in form))
    R.add("S2b", "the form passes follow one another without gaps from q = 0, and their seconds equal the tempo map", contiguous and tdiff <= 6e-7, "%d passes, last ends at q = %s" % (len(form), form[-1]["q1"]))
    R.add("S2c", "checks.quarters_performed and checks.seconds equal the end of the last pass", card["checks"]["quarters_performed"] == form[-1]["q1"]
          and abs(card["checks"]["seconds"] - float(seconds(tempo, Fr(form[-1]["q1"])))) <= 6e-7, "%s quarters, %.3f s" % (form[-1]["q1"], card["checks"]["seconds"]))
    # layers
    layers = {n["layer"] for n in card["notes"]}
    R.add("S10", "every note is on the composer or the arrangement layer, and every note's instrument is declared", layers <= {"composer", "arrangement"}
          and {n["inst"] for n in card["notes"]} <= {i["id"] for i in card["instruments"]}, "layers %s" % sorted(layers))
    # harmony
    hs = card["harmony"]
    gap = [i for i in range(len(hs) - 1) if Fr(hs[i]["q"]) + Fr(hs[i]["ql"]) != Fr(hs[i + 1]["q"])]
    cover = Fr(hs[0]["q"]) == 0 and Fr(hs[-1]["q"]) + Fr(hs[-1]["ql"]) == Fr(form[-1]["q1"])
    wrong = []
    for h in hs:
        if sorted((h["root"] + i) % 12 for i in H.QUAL[h["qual"]]) != h["pcs"]:
            wrong.append(("pcs", h["q"]))
        if h["roman"] != H.roman(h["root"], h["qual"], h["bass"], h["key"]):
            wrong.append(("roman", h["q"]))
        if abs(h["tension"] - round(H.tension(h["root"], h["qual"], h["key"]), 3)) > 1e-9:
            wrong.append(("tension", h["q"]))
        if abs(h["t"] - float(seconds(tempo, Fr(h["q"])))) > 6e-7:
            wrong.append(("t", h["q"]))
    R.add("S7", "harmony segments follow one another from q = 0 to the end, and each one's pitch classes, Roman numeral, tension and seconds are consistent", not gap and cover and not wrong,
          "%d segments, %d gaps, %d inconsistent%s" % (len(hs), len(gap), len(wrong), (" (first: %s)" % (wrong[0],)) if wrong else ""))
    km = card["key_map"]
    R.add("S8", "the key map starts at t = 0, rises in time and names keys the harmony uses", km[0]["t"] == 0 and all(km[i]["t"] < km[i + 1]["t"] for i in range(len(km) - 1))
          and {k["key"] for k in km} == {h["key"] for h in hs}, "%d key changes: %s" % (len(km), " ".join(k["key"] for k in km[:8])))
    return notes, tempo, beats, pickup


def check_turca(card, root, R):
    krn_path = os.path.join(root, card["source"]["path"])
    R.add("S0", "the card names the source file by its sha256", hashlib.sha256(open(krn_path, "rb").read()).hexdigest() == card["source"]["sha256"], card["source"]["path"])
    notes, tempo, beats, pickup = common_checks(card, "turca", R)
    ind = kern_independent(krn_path)
    heads, total = m21_turca(krn_path)
    # the plan and the section extents come from the file's own labels, read by the independent reader
    labs = [l for l, _ in ind["labels"]]
    R.add("S2a", "the form follows the file's own repeat plan (read by regex), with rep counted per label",
          [(f["id"], f["rep"]) for f in card["form"]] == [(x, ind["plan"][:i].count(x) + 1) for i, x in enumerate(ind["plan"])], ",".join(ind["plan"]))
    ext = {}
    for i, (lab, _) in enumerate(ind["labels"]):
        ext[lab] = (ind["offsets"][lab], ind["offsets"][ind["labels"][i + 1][0]] if i + 1 < len(labs) else ind["end"])
    # expected performed notes: every music21 head of the section, shifted to the pass
    exp, start = {}, Fr(0)
    for i, lab in enumerate(ind["plan"]):
        rep = ind["plan"][:i].count(lab) + 1
        a, b = ext[lab]
        for off, midi, ql, g in heads:
            if a <= off < b:
                k = (lab, rep, start + off - a, midi, ql, g)
                exp[k] = exp.get(k, 0) + 1
        start += b - a
    got = {}
    for n in notes:
        k = (n["section"], n["rep"], Fr(n["q"]), n["pitch"], Fr(n["ql"]), bool(n.get("g")))
        got[k] = got.get(k, 0) + 1
    missing = sum(max(0, v - got.get(k, 0)) for k, v in exp.items())
    extra = sum(max(0, v - exp.get(k, 0)) for k, v in got.items())
    R.add("S1", "composer notes equal the source expanded by the file's repeat plan: pitch, onset and duration as exact fractions of a quarter, 0 missing and 0 extra",
          not missing and not extra, "%d expected, %d in the card, %d missing, %d extra" % (sum(exp.values()), len(notes), missing, extra))
    # written heads: unique src pointers = the 1,613 note heads
    srcs = {n["src"] for n in notes}
    R.add("S3a", "the card's notes point at exactly %d distinct written note heads, the number music21 finds in the file (%d)" % (len(srcs), len(heads)), len(srcs) == len(heads) == card["checks"]["composer_note_heads"], "%d src pointers" % len(srcs))
    # src pointers: the line and column named by each note holds a head of that pitch
    bad = []
    lines = ind["lines"]
    for n in notes:
        m = re.match(r"^(\d+):(\d+)(?:\.(\d+))?$", n["src"])
        ln, col, sub = int(m[1]), int(m[2]), int(m[3] or 1)
        tok = lines[ln - 1].split("\t")[col - 1].split(" ")[sub - 1]
        if pitch_of_token(tok) != n["pitch"] or ("q" in tok) != bool(n.get("g")):
            bad.append(n["id"])
    R.add("S3b", "each note's src names a kern line and column whose token has the note's pitch (read by a separate pitch parser) and grace flag", not bad, "%d notes checked, %d wrong%s" % (len(notes), len(bad), (": " + ", ".join(bad[:3])) if bad else ""))
    # kern measure numbers
    barline_nums = [(ln, num) for ln, num, _ in ind["barlines"] if num is not None]
    bad = []
    for n in notes:
        ln = int(n["src"].split(":")[0])
        cur = 0
        for bl, num in barline_nums:
            if bl < ln:
                cur = num
            else:
                break
        if cur != n["kbar"]:
            bad.append(n["id"])
    R.add("S5b", "each note's kbar is the number of the last numbered barline above its src line", not bad, "%d wrong" % len(bad))
    # bars performed
    count = {lab: sum(1 for ln, num, _ in ind["barlines"] if num is not None and ind["labels"][i][1] <= ln < (ind["labels"][i + 1][1] if i + 1 < len(labs) else 10 ** 9)) for i, lab in enumerate(labs)}
    bars = sum(count[x] for x in ind["plan"])
    R.add("S3c", "bars performed = numbered barlines passed in plan order = 224; written note heads = 1,613; performed passes = 21",
          bars == card["checks"]["bars_performed"] == 224 and len(heads) == 1613 and len(card["form"]) == 21, "%d bars, %d heads, %d passes" % (bars, len(heads), len(card["form"])))
    R.add("S3d", "the written score is as long as the independent left-hand count says (256 quarters) and the performed score is the plan's total",
          total == ind["end"] == 256 and Fr(card["checks"]["quarters_performed"]) == sum(ext[x][1] - ext[x][0] for x in ind["plan"]), "written %s, performed %s" % (total, card["checks"]["quarters_performed"]))
    # form bars come from the content
    return notes, tempo


def check_ode(card, root, R):
    xml_path = os.path.join(root, card["source"]["path"])
    R.add("S0", "the card names the source file by its sha256", hashlib.sha256(open(xml_path, "rb").read()).hexdigest() == card["source"]["sha256"], card["source"]["path"])
    notes, tempo, beats, pickup = common_checks(card, "ode", R)
    raw, reps, total = m21_ode(xml_path)
    R.add("S2a", "the theme is 16 written bars (64 quarters) with a repeat over bars 9 to 16", total == 64 and reps == [(9, "start"), (16, "end")], "%s quarters, repeats %s (music21 calls them start and end)" % (total, reps))
    # the spec's arrangement table, restated: section -> (bars, written ranges in quarters of the theme)
    table = [("Intro", 8, []), ("S1", 16, [(0, 64)]), ("S2", 16, [(0, 64)]), ("S3", 24, [(0, 64), (32, 64)]), ("S4", 24, [(0, 64), (32, 64)]), ("Coda", 8, [(48, 64)])]
    R.add("S2d", "the form is the spec's table: Intro 8, statements 16, 16, 24, 24, coda 8 bars = 96 bars",
          [(f["id"], f["bars"][1] - f["bars"][0] + 1) for f in card["form"]] == [(t[0], t[1]) for t in table] and card["checks"]["bars_performed"] == 96, "96 bars" if card["checks"]["bars_performed"] == 96 else "wrong")
    exp, start = {}, Fr(0)
    for sid, nb, ranges in table:
        pos = start
        for a, b in ranges:
            for meas, idx, off, midi, ql in merge_ties_m21(raw, Fr(a), Fr(b)):
                k = (sid, 1, pos + off - a, midi, ql, "m%d.%d" % (meas, idx))
                exp[k] = exp.get(k, 0) + 1
            pos += b - a
        start += nb * 4
    got = {}
    for n in notes:
        k = (n["section"], n["rep"], Fr(n["q"]), n["pitch"], Fr(n["ql"]), n["src"].split("+")[0])
        got[k] = got.get(k, 0) + 1
    missing = sum(max(0, v - got.get(k, 0)) for k, v in exp.items())
    extra = sum(max(0, v - exp.get(k, 0)) for k, v in got.items())
    R.add("S1", "composer notes equal the theme expanded by the statement plan (tied notes merged): pitch, onset and duration as exact fractions of a quarter, 0 missing and 0 extra",
          not missing and not extra, "%d expected, %d in the card, %d missing, %d extra" % (sum(exp.values()), len(notes), missing, extra))
    tied = [n for n in notes if n.get("tied")]
    R.add("S3e", "the one tie (bar 12 into bar 13) is kept: six passes of the theme contain it (S1, S2 once; S3, S4 twice), each a single F sharp of two quarters starting on beat 4, and the coda's quote of bar 13 starts a fresh attack",
          len(tied) == 6 and all(n["pitch"] == 66 and Fr(n["ql"]) == 2 and n["src"] == "m12.4+m13.1" and n["beat"] == 4.0 for n in tied), "%d tied notes" % len(tied))
    R.add("S3a", "the card's heads number what music21 finds in the file (63 written heads, 62 after merging the tie)", card["checks"]["composer_note_heads"] == len(raw) == 63 and card["checks"]["theme_notes_after_ties"] == 62, "%d heads" % len(raw))
    return notes, tempo


# ---------------------------------------------------------------- tracks
def unpack(ch, n):
    return list(struct.unpack("<%dh" % n, base64.b64decode(ch["b64"])))


def check_tracks(card, tracks, card_path, tempo, beats, pickup, R, samples=300):
    n = tracks["n"]
    ok_hdr = tracks["fs"] == FS and n == int(math.ceil(card["checks"]["seconds"] * FS)) + 1 and tracks["card_sha256"] == hashlib.sha256(open(card_path, "rb").read()).hexdigest()
    R.add("T0", "tracks name their card by sha256, run at 60 Hz and cover the whole piece", ok_hdr, "n = %d samples" % n)
    ch = {k: unpack(v, n) for k, v in tracks["channels"].items()}
    notes = [x for x in card["notes"] if x["layer"] == "composer"]
    ev = [(x["t"], x["t"] + x["dur"], x["pitch"] + 12 * x.get("oct", 0), x.get("g", 0)) for x in notes]
    onsets = sorted(e[0] for e in ev if not e[3])
    form_q = [(Fr(f["q0"]), Fr(f["q1"])) for f in card["form"]]
    harm_t = [h["t"] for h in card["harmony"]]
    rng = random.Random(20261102)
    idx = sorted({0, n - 1} | {rng.randrange(n) for _ in range(samples)})
    bad = []
    for k in idx:
        t = k / FS
        q = quarters(tempo, Fr(k, FS))
        want = {}
        want["beat_phase"] = int(round(float(q % 1) * 1000)) % 1000
        x = q + (beats - pickup) if pickup else q
        want["bar_phase"] = int(round(float((x % beats) / beats) * 1000)) % 1000
        want["section"] = next((j for j, (a, b) in enumerate(form_q) if a <= q < b), len(form_q) - 1)
        h = max(0, bisect.bisect_right(harm_t, t + 1e-9) - 1)
        want["harmony"] = h
        want["tension"] = int(round(card["harmony"][h]["tension"] * 1000))
        want["density"] = int(round(sum(1 for o in onsets if t - 0.5 <= o < t + 0.5) * 10))
        act = [e for e in ev if e[0] <= t + 1e-9 and e[1] > t + 1e-9]
        want["active"] = len(act)
        if act:
            want["contour"] = max(a[2] for a in act)
            want["lo"] = min(a[2] for a in act)
            want["hi"] = max(a[2] for a in act)
        for name, w in want.items():
            if ch[name][k] != w:
                bad.append((name, k, ch[name][k], w))
    R.add("T1", "at %d random samples plus the first and last, every exact channel (phases, section, harmony, tension, density, active, and contour and register while notes sound) equals a brute-force recomputation from the card" % samples,
          not bad, "%d samples checked, %d differences%s" % (len(idx), len(bad), (": first %s" % (bad[0],)) if bad else ""))
    ranges = all(0 <= v < 1000 for v in ch["beat_phase"]) and all(0 <= v < 1000 for v in ch["bar_phase"]) and max(ch["section"]) < len(card["form"]) and max(ch["harmony"]) < len(card["harmony"])
    R.add("T2", "phases lie in [0, 1), and section and harmony indexes lie inside their lists", ranges, "")


# ---------------------------------------------------------------- driver
def check_piece(card, piece, root=ROOT, tracks=None, card_path=None):
    R = Results()
    if piece == "turca":
        notes, tempo = check_turca(card, root, R)
    elif piece == "ode":
        notes, tempo = check_ode(card, root, R)
    else:
        raise SystemExit("unknown piece " + piece)
    if tracks is not None:
        beats = int(card["meter"].split("/")[0])
        first = card["tempo_map"][0]
        pickup = (beats - (int(first["beat"]) - 1)) % beats if first["bar"] == 0 else 0
        check_tracks(card, tracks, card_path, tempo, beats, pickup, R)
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--piece", default="all", choices=["turca", "ode", "all"])
    ap.add_argument("--out")
    a = ap.parse_args()
    pieces = ["turca", "ode"] if a.piece == "all" else [a.piece]
    allr, failed = {}, 0
    for p in pieces:
        cp = os.path.join(ROOT, "score", p + ".score.json")
        card = json.load(open(cp, encoding="utf-8"))
        tracks = json.load(open(os.path.join(ROOT, "tracks", p + ".tracks.json"), encoding="utf-8"))
        R = check_piece(card, p, ROOT, tracks, cp)
        allr[p] = list(R)
        for r in R:
            print("%s %-4s %-5s %s  [%s]" % ("PASS" if r["ok"] else "FAIL", p, r["id"], r["claim"], r["detail"]))
            failed += not r["ok"]
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(allr, open(a.out, "w"), indent=1)
    print("score witness: %d checks, %d failed" % (sum(len(v) for v in allr.values()), failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
