"""Géométrie d'un burr à 6 pièces 2x2x8 : repères, orientations, emplacements, symétries."""
import itertools

L = 8  # longueur en unités
CUBES = {"HAV": (0, 1), "HAR": (1, 1), "BAV": (0, 0), "BAR": (1, 0)}  # (u, v)

# Emplacements : (axe, décalage). Le cœur assemblé est un cube 4x4x4 (coord. -2..1)
SLOTS = [("X", -2), ("X", 0), ("Y", -2), ("Y", 0), ("Z", -2), ("Z", 0)]
SLOT_NAMES = ["X-bas", "X-haut", "Y-bas", "Y-haut", "Z-bas", "Z-haut"]
OPP = {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y", "+z": "-z", "-z": "+z"}
DIRS = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0),
        "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}



def orientations(cells):
    """8 orientations propres : 4 rotations autour de l'axe x retournement bout à bout."""
    seen, out = set(), []
    for flip in (False, True):
        for r in range(4):
            s = set()
            for i, u, v in cells:
                if flip:
                    i, u = L - 1 - i, 1 - u          # rotation 180° autour de v
                for _ in range(r):
                    u, v = 1 - v, u                  # rotation 90° autour de i
                s.add((i, u, v))
            fs = frozenset(s)
            if fs not in seen:
                seen.add(fs)
                out.append(((flip, r), fs))
    return out


def place(cells, slot):
    ax, o = slot
    out = set()
    for i, u, v in cells:
        a, b, c = i - 4, u - 1, v + o
        out.add((a, b, c) if ax == "X" else (c, a, b) if ax == "Y" else (b, c, a))
    return frozenset(out)


def orientation_text(slot, flip, r):
    """Où pointe l'extrémité A et la face H, dans le repère global."""
    ax = slot[0]
    vec_u, vec_v = 0, 1  # normale de la face H (le retournement ne la change pas)
    for _ in range(r):
        vec_u, vec_v = -vec_v, vec_u
    end_a = 1 if flip else -1  # extrémité A (i=0) : côté -axe, ou +axe si retournée
    perm = {"X": ("x", "y", "z"), "Y": ("y", "z", "x"), "Z": ("z", "x", "y")}[ax]
    a_txt = ("+" if end_a > 0 else "-") + perm[0]
    if vec_u:
        h_txt = ("+" if vec_u > 0 else "-") + perm[1]
    else:
        h_txt = ("+" if vec_v > 0 else "-") + perm[2]
    return f"extrémité A côté {a_txt}, face H vers {h_txt}"



def rotations():
    rs = []
    for perm in itertools.permutations(range(3)):
        inv = sum(1 for a, b in itertools.combinations(perm, 2) if a > b)
        for signs in itertools.product((1, -1), repeat=3):
            if (-1) ** inv * signs[0] * signs[1] * signs[2] == 1:
                rs.append((perm, signs))
    return rs


ROTS = rotations()


def shape_classes(pieces):
    """Pièces identiques (à une rotation près) -> même classe."""
    cls, reps = {}, []
    for n, cs in pieces.items():
        forms = {fs for _, fs in orientations(cs)}
        for k, rep in enumerate(reps):
            if rep in forms:
                cls[n] = k
                break
        else:
            cls[n] = len(reps)
            reps.append(cs)
    return cls


def canonical(sol, cls):
    best = None
    for perm, signs in ROTS:
        key = []
        for n, _, _, cs in sol:
            for c in cs:
                d = [2 * x + 1 for x in c]
                key.append((cls[n], tuple(signs[r] * d[perm[r]] for r in range(3))))
        key = tuple(sorted(key))
        if best is None or key < best:
            best = key
    return best

