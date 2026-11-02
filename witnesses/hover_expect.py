#!/usr/bin/env python3
"""What the hover card must say, worked out from the score card and the world's own tables, not from the page: the reference the page test compares the page against.

    python3 -I witnesses/hover_expect.py ode  col,row col,row ...     tapestry cells: the thread and the note that owns each cell
    python3 -I witnesses/hover_expect.py note <piece> <index> ...      a note's card line
Prints one JSON object per line.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
import worldlib as W                # noqa: E402

PC = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]


def pitch_name(m):
    return PC[m % 12] + str(m // 12 - 1)


def note_line(card, i):
    """A note's card line. Bar and beat are the score card's own record of the note, not a sum redone from its seconds: the card keeps seconds to six decimals, so a note that sits on a bar line
    (an arrangement note of the Ode's choir does: 279.9999996 quarters) would land on the bar before it with beat 5, where the page's four-decimal seconds happen to round the other way. The page's
    bar and beat are still worked out from seconds and the tempo map (that arithmetic is what this test holds to the card)."""
    n = card.notes[i]
    return dict(i=i, id=n["id"], line1="%s · %s" % (pitch_name(n["pitch"]), n["inst"]), bar=n["bar"], beat=round(float(n["beat"]), 2), who="composer" if n["layer"] == "composer" else "arrangement", vel=n["vel"])


def main(a):
    if a[0] == "ode":
        import world_ode as O, picture_ode as PIC
        card = W.Card("ode")
        rows = [[e[5] for e in r] for r in O.EventTable("weave", O.weave_rows(card), card.D).rows]
        cb = PIC.cells()
        for pt in a[1:]:
            col, row = (int(x) for x in pt.split(","))
            byte = int(cb[row][col])
            code = byte & 7
            out = dict(col=col, row=row, code=code, thread=(O.LAYERS[code - 1]["name"] if code else None))
            if code:
                owner = O.cell_owner(rows, code - 1, col, row)
                out["owner"] = owner
                out.update(note_line(card, owner) if owner is not None else {})
            print(json.dumps(out, ensure_ascii=False))
    elif a[0] == "note":
        card = W.Card(a[1])
        for i in a[2:]:
            print(json.dumps(note_line(card, int(i)), ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
