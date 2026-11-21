"""Recherche de tous les assemblages géométriques (sans chevauchement)."""
from .geometry import SLOTS, canonical, orientations, place, shape_classes


def assemble(pieces):
    names = list(pieces)
    P = {n: [[(o, place(cs, s)) for o, cs in orientations(pieces[n])] for s in SLOTS]
         for n in names}
    sols = []

    def bt(si, used, occ, cur):
        if si == 6:
            sols.append(list(cur))
            return
        for n in names:
            if n in used:
                continue
            for o, cs in P[n][si]:
                if occ & cs:
                    continue
                cur.append((n, si, o, cs))
                used.add(n)
                bt(si + 1, used, occ | cs, cur)
                cur.pop()
                used.discard(n)

    bt(0, set(), frozenset(), [])
    return sols



def unique_assemblies(pieces):
    """Assemblages distincts, une fois retirés les doublons dus aux symétries et aux pièces identiques."""
    cls = shape_classes(pieces)
    raw = assemble(pieces)
    uniq = {}
    for s in raw:
        uniq.setdefault(canonical(s, cls), s)
    return list(uniq.values()), len(raw)
