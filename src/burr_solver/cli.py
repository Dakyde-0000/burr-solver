"""Interface en ligne de commande.

    burr-solver pieces data/pieces.csv   contrôle de la table + code compact de chaque pièce
    burr-solver solve  data/pieces.csv   assemblages et démontage
    burr-solver vue3d  data/pieces.csv   visionneuse 3D interactive (HTML)
    burr-solver viz    data/pieces.csv   images PNG + GIF du démontage
"""
import argparse

from .assembly import unique_assemblies
from .disassembly import compress, disassemble
from .geometry import SLOT_NAMES, SLOTS, orientation_text
from .io import PieceError, load_pieces, piece_code


def show_pieces(pieces, removed):
    print("Pièces (code : unités 3-6, chiffres HAV HAR BAV BAR, 1 = enlevé)")
    for p in pieces:
        print(f"  {p:4s} {piece_code(removed[p])}   {len(removed[p]):2d} cubes enlevés")
    print()


def check(csv_path):
    pieces, removed = load_pieces(csv_path)
    show_pieces(pieces, removed)
    print("Table cohérente : 6 pièces d'un seul tenant, entailles dans les unités 3 à 6.")
    return 0


def solve(csv_path):
    pieces, removed = load_pieces(csv_path)
    show_pieces(pieces, removed)
    sols, n_raw = unique_assemblies(pieces)
    print(f"Assemblages géométriques distincts : {len(sols)} (bruts avant symétries : {n_raw})\n")
    found = 0
    for idx, sol in enumerate(sols, 1):
        res = disassemble({n: cs for n, _, _, cs in sol})
        status = "DÉMONTABLE" if res else "non démontable (impossible à monter en vrai)"
        print(f"--- Assemblage {idx} : {status}")
        for n, si, (flip, r), _ in sorted(sol, key=lambda t: t[1]):
            print(f"  {SLOT_NAMES[si]:7s} <- {n:4s} {orientation_text(SLOTS[si], flip, r)}")
        if res:
            found += 1
            moves, level = res
            print(f"  Niveau {level} (mouvements avant la sortie de la 1re pièce/groupe)")
            print("  Démontage :")
            for grp, d, k in compress(moves):
                act = "sort" if k == "SORT" else f"glisse de {k}"
                print(f"    {'+'.join(grp)} {act} en {d}")
            print("  Montage = la même liste lue à l'envers, directions inversées.")
        print()
    if not found:
        print("Aucune solution démontable : vérifie la saisie (pièce miroir, AV/AR inversés...).")
    return 0 if found else 2


def main(argv=None):
    p = argparse.ArgumentParser(prog="burr-solver",
                                description="Solveur de burr à 6 pièces (2x2x8).")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("pieces", help="contrôler la table et afficher le code de chaque pièce")
    c.add_argument("csv", help="table des pièces (voir docs/convention.md)")
    s = sub.add_parser("solve", help="chercher les assemblages et le démontage")
    s.add_argument("csv", help="table des pièces (voir docs/convention.md)")
    t = sub.add_parser("vue3d", help="visionneuse 3D interactive des pièces et de la solution (HTML)")
    t.add_argument("csv")
    t.add_argument("--solution", type=int, default=1, help="numéro de la solution affichée")
    t.add_argument("--out", default="outputs", help="dossier de sortie")
    v = sub.add_parser("viz", help="images des pièces, de l'assemblage et GIF du démontage")
    v.add_argument("csv")
    v.add_argument("--solution", type=int, default=1, help="numéro de la solution à animer")
    v.add_argument("--out", default="outputs", help="dossier de sortie")
    a = p.parse_args(argv)
    try:
        if a.cmd == "pieces":
            raise SystemExit(check(a.csv))
        if a.cmd == "solve":
            raise SystemExit(solve(a.csv))
        if a.cmd == "vue3d":
            from .viz3d import run as run3d
            run3d(a.csv, a.out, a.solution)
            return
        from .viz import run  # import tardif : matplotlib seulement si besoin
        run(a.csv, a.solution, a.out)
    except PieceError as e:
        print(e)
        raise SystemExit(1)
