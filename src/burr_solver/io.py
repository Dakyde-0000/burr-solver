"""Lecture, contrôle et code compact de la table des pièces.

Table CSV (séparateur ';'), une ligne par petit cube ENLEVÉ :
    piece;unite;cube
    P1;4;HAV
Voir docs/convention.md.
"""
import csv

from .geometry import CUBES, L

NOTCH_UNITS = range(3, 7)                  # unités (1..8) où une entaille est permise
CODE_ORDER = ["HAV", "HAR", "BAV", "BAR"]  # ordre des 4 chiffres du code compact


class PieceError(ValueError):
    """Table de pièces incohérente (message en clair pour l'utilisateur)."""


# ------------------------------------------------------------------ lecture
def read_table(path):
    """Lit le CSV. Renvoie (ordre des pièces, {pièce: {(unite, cube)} enlevés})."""
    removed, order, errors = {}, [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for line_no, row in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            pid = (row.get("piece") or "").strip()
            if not pid:
                continue
            if pid not in removed:
                removed[pid] = set()
                order.append(pid)
            unit = (row.get("unite") or "").strip()
            cube = (row.get("cube") or "").strip().upper()
            if not unit and not cube:
                continue  # pièce sans entaille
            if not unit.isdigit() or not 1 <= int(unit) <= L:
                errors.append(f"ligne {line_no} : unité '{unit}' invalide (1 à {L})")
                continue
            if cube not in CUBES:
                errors.append(f"ligne {line_no} : cube '{cube}' invalide "
                              f"({', '.join(CODE_ORDER)})")
                continue
            key = (int(unit), cube)
            if key in removed[pid]:
                errors.append(f"ligne {line_no} : doublon {pid} unité {unit} {cube}")
            removed[pid].add(key)
    if errors:
        raise PieceError("Table invalide :\n  " + "\n  ".join(errors))
    return order, removed


# ---------------------------------------------------------------- contrôles
def _connected(cells):
    """Vrai si les cubes forment un seul bloc (contact par une face)."""
    cells = set(cells)
    if not cells:
        return False
    todo = [next(iter(cells))]
    seen = set(todo)
    while todo:
        i, u, v = todo.pop()
        for n in ((i + 1, u, v), (i - 1, u, v), (i, 1 - u, v), (i, u, 1 - v)):
            if n in cells and n not in seen:
                seen.add(n)
                todo.append(n)
    return len(seen) == len(cells)


def check_pieces(order, removed, n_pieces=6):
    """Contrôles physiques. Lève PieceError avec la liste de tous les problèmes."""
    errors = []
    if len(order) != n_pieces:
        errors.append(f"{len(order)} pièces trouvées, il en faut {n_pieces}")
    for pid in order:
        outside = sorted({k for k, _ in removed[pid] if k not in NOTCH_UNITS})
        if outside:
            errors.append(f"{pid} : cube(s) enlevé(s) hors des unités 3 à 6 (unités {outside})")
        if not _connected(to_cells(removed[pid])):
            cut = [k for k in NOTCH_UNITS
                   if all((k, c) in removed[pid] for c in CODE_ORDER)]
            hint = f" (les 4 cubes de l'unité {cut[0]} sont enlevés)" if cut else ""
            errors.append(f"{pid} : la pièce n'est pas d'un seul tenant{hint}")
    if errors:
        raise PieceError("Pièces incohérentes :\n  " + "\n  ".join(errors))


# ------------------------------------------------------------ conversions
def to_cells(removed_keys):
    """{(unite, cube)} enlevés -> cubes présents (i, u, v) dans le repère de la pièce."""
    gone = {(k - 1,) + CUBES[c] for k, c in removed_keys}
    return frozenset((i, u, v) for i in range(L) for u in (0, 1) for v in (0, 1)
                     if (i, u, v) not in gone)


def piece_code(removed_keys):
    """Code compact : 4 chiffres par unité 3..6, ordre HAV HAR BAV BAR, 1 = enlevé.
    Exemple : '0000-0101-0111-0000'."""
    return "-".join("".join("1" if (k, c) in removed_keys else "0" for c in CODE_ORDER)
                    for k in NOTCH_UNITS)


def from_code(code):
    """Inverse de piece_code : '0000-0101-0111-0000' -> {(unite, cube)}."""
    groups = code.strip().split("-")
    if len(groups) != len(NOTCH_UNITS) or any(
            len(g) != 4 or set(g) - {"0", "1"} for g in groups):
        raise PieceError(f"Code compact invalide : '{code}'")
    return {(k, c) for k, g in zip(NOTCH_UNITS, groups)
            for c, bit in zip(CODE_ORDER, g) if bit == "1"}


def load_pieces(path, check=True):
    """Lit et contrôle la table.
    Renvoie ({pièce: cubes présents}, {pièce: {(unite, cube)} enlevés})."""
    order, removed = read_table(path)
    if check:
        check_pieces(order, removed)
    return {p: to_cells(removed[p]) for p in order}, removed
