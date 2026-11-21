"""Recherche d'une séquence de démontage (BFS sur les translations unitaires de groupes de pièces)."""
from collections import deque

from .geometry import DIRS, OPP


def shift(cells, off):
    dx, dy, dz = off
    return {(x + dx, y + dy, z + dz) for x, y, z in cells}


def _rec(names, G, dname, k):
    """Décrit le mouvement avec le plus petit groupe (l'autre groupe bouge en sens inverse)."""
    n = len(names)
    if len(G) > n - len(G):
        G, dname = set(range(n)) - set(G), OPP[dname]
    return ([names[i] for i in sorted(G)], dname, k)


def disassemble(parts, max_states=300000, sep=12):
    """parts : dict nom -> cellules (globales). Renvoie (liste de mouvements, niveau) ou None."""
    names = list(parts)
    n = len(names)
    if n <= 1:
        return [], 0
    start = tuple((0, 0, 0) for _ in names)
    parent = {start: None}
    q = deque([start])
    while q and len(parent) < max_states:
        st = q.popleft()
        cur = [shift(parts[names[k]], st[k]) for k in range(n)]
        occ = {c: k for k in range(n) for c in cur[k]}
        tried = set()
        for dname, d in DIRS.items():
            for p in range(n):
                G, todo = {p}, [p]
                while todo:
                    g = todo.pop()
                    for c in shift(cur[g], d):
                        h = occ.get(c)
                        if h is not None and h not in G:
                            G.add(h)
                            todo.append(h)
                if len(G) == n:
                    continue
                key = (dname, frozenset(G))
                if key in tried:
                    continue
                tried.add(key)
                others = set().union(*(cur[k] for k in range(n) if k not in G))
                gcells = set().union(*(cur[k] for k in G))
                free = all(not (shift(gcells, tuple(sep_k * x for x in d)) & others)
                           for sep_k in range(1, sep + 1))
                if free:  # le groupe G sort complètement
                    path = []
                    s = st
                    while parent[s] is not None:
                        s, mv = parent[s]
                        path.append(mv)
                    path.reverse()
                    level = len(path) + 1
                    path.append(_rec(names, G, dname, "SORT"))
                    A = {names[k]: frozenset(cur[k]) for k in G}
                    B = {names[k]: frozenset(cur[k]) for k in range(n) if k not in G}
                    ra, rb = disassemble(A), disassemble(B)
                    if ra is None or rb is None:
                        continue
                    return path + ra[0] + rb[0], level
                new = list(st)
                for k in G:
                    new[k] = tuple(a + b for a, b in zip(new[k], d))
                ref = new[0]
                new = tuple(tuple(a - b for a, b in zip(o, ref)) for o in new)
                if new not in parent:
                    parent[new] = (st, _rec(names, G, dname, 1))
                    q.append(new)
    return None


def compress(moves):
    out = []
    for grp, d, k in moves:
        if out and out[-1][0] == grp and out[-1][1] == d and k != "SORT" and out[-1][2] != "SORT":
            out[-1] = (grp, d, out[-1][2] + k)
        else:
            out.append((grp, d, k))
    return out



# ------------------------------------------------------------ montage
def _norm(pos, names):
    c = [sum(pos[n][i] for n in names) / len(names) for i in range(3)]
    return sum(x * x for x in c)


def _shifted(pos, moved, d, dist):
    out = dict(pos)
    for n in moved:
        out[n] = tuple(a + dist * b for a, b in zip(pos[n], DIRS[d]))
    return out


def _overlap(pos, moved, cells):
    a = set().union(*(shift(cells[n], pos[n]) for n in moved))
    b = set().union(*(shift(cells[n], pos[n]) for n in pos if n not in moved))
    return bool(a & b)


def keyframes(names, moves, sort_dist=8, cells=None):
    """Positions de chaque pièce après chaque mouvement du démontage, pour l'affichage.
    Quand un groupe se sépare, on déplace le groupe indiqué ; s'il se rapprocherait du
    centre, on déplace plutôt le reste dans le sens opposé (même mouvement relatif),
    pour que les pièces sorties ne reviennent pas traverser le burr. Si `cells` (cubes
    de chaque pièce assemblée) est fourni, la distance de sortie est allongée tant que
    le groupe sorti chevauche une pièce déjà posée à l'écart.
    Renvoie [(libellé, {pièce: décalage (x, y, z)})], en commençant par l'état assemblé."""
    pos = {n: (0, 0, 0) for n in names}
    blocks = [set(names)]                     # sous-ensembles encore emboîtés
    frames = [("Assemblé", dict(pos))]
    for grp, d, k in compress(moves):
        grp = set(grp)
        block = next(b for b in blocks if grp <= b)
        if k == "SORT":
            rest = block - grp
            moved, dd = grp, d
            if rest and _norm(_shifted(pos, grp, d, sort_dist), grp) < _norm(pos, grp):
                moved, dd = rest, OPP[d]   # le petit groupe reviendrait vers le centre
            dist = sort_dist
            new = _shifted(pos, moved, dd, dist)
            while cells and _overlap(new, moved, cells):
                dist += 2
                new = _shifted(pos, moved, dd, dist)
            pos = new
            blocks.remove(block)
            blocks += [grp, rest]
            label = f"{'+'.join(sorted(moved))} sort en {dd}"
        else:
            for n in grp:
                pos[n] = tuple(a + k * b for a, b in zip(pos[n], DIRS[d]))
            label = f"{'+'.join(sorted(grp))} glisse de {k} en {d}"
        frames.append((label, dict(pos)))
    return frames


def assembly_steps(names, moves, sort_dist=8, cells=None):
    """Étapes du montage = démontage parcouru à l'envers, sens des mouvements inversés.
    Renvoie [(libellé, {pièce: décalage})], de l'état démonté jusqu'au burr assemblé."""
    kf = keyframes(names, moves, sort_dist, cells)
    steps = [("Pièces disposées, prêtes à monter", kf[-1][1])]
    for idx in range(len(kf) - 1, 0, -1):
        label = kf[idx][0]
        who, rest = label.split(" ", 1)
        act, d = rest.rsplit(" en ", 1)
        act = "entre" if act == "sort" else act
        steps.append((f"{who} {act} en {OPP[d]}", kf[idx - 1][1]))
    return steps
