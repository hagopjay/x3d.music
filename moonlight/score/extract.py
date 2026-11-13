"""Score -> note events (JSON). Positions in quarter-lengths from start of excerpt."""
import json, sys
from music21 import converter, dynamics, chord, note

def load(path, bar_from, bar_to):
    s = converter.parse(path).stripTies()
    out = {}
    for part in s.parts:
        hand = 'LH' if part.id == 'spine_0' else 'RH'
        meas = part.getElementsByClass('Measure')
        start = None; evs = []; dyn=[]
        for m in meas:
            if m.number < bar_from or m.number > bar_to: continue
            if start is None: start = m.offset
            base = m.offset - start
            for el in m.recurse().notes:
                off = base + el.getOffsetInHierarchy(m)
                pitches = el.pitches
                for p in pitches:
                    evs.append(dict(t=float(off), d=float(el.quarterLength), m=int(p.midi),
                                    chord=len(pitches), bar=m.number))
            for d in m.recurse().getElementsByClass(dynamics.Dynamic):
                dyn.append((float(base + d.getOffsetInHierarchy(m)), d.value))
        out[hand] = evs; out[hand+'_dyn'] = dyn
    return out

if __name__ == '__main__':
    path, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    o = load(path, a, b)
    for h in ('LH','RH'):
        ev=o[h]; from collections import Counter
        print(h, len(ev), 'durations', Counter(round(e['d'],3) for e in ev).most_common(8),
              'range', min(e['m'] for e in ev), max(e['m'] for e in ev))
        print('  dyn', o[h+'_dyn'][:12])
    json.dump(o, open(sys.argv[4],'w'))
