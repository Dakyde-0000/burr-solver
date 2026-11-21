"""Visualisation : pièces saisies, assemblage, animation du démontage (matplotlib + pillow)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from . import geometry as G
from .assembly import unique_assemblies
from .disassembly import assembly_steps, disassemble, keyframes
from .io import load_pieces

COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4"]
SORT_DIST = 8       # distance (unités) dont une pièce/un groupe s'éloigne quand il sort
FRAMES_PER_UNIT = 3  # fluidité de l'animation

NEIGH = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
         ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
         ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
         ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
         ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
         ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]


def faces(cells, off=(0.0, 0.0, 0.0)):
    """Faces extérieures d'un ensemble de cubes unitaires (cube (x,y,z) = [x,x+1]...)."""
    out = []
    for x, y, z in cells:
        for (dx, dy, dz), corners in NEIGH:
            if (x + dx, y + dy, z + dz) not in cells:
                out.append([(x + cx + off[0], y + cy + off[1], z + cz + off[2])
                            for cx, cy, cz in corners])
    return out


def draw(ax, cells, color, off=(0, 0, 0), alpha=1.0):
    pc = Poly3DCollection(faces(set(cells), off), facecolor=color,
                          edgecolor="k", linewidths=0.3, alpha=alpha)
    ax.add_collection3d(pc)


def setup(ax, lim, title=""):
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_zlim(*lim[2])
    ax.set_box_aspect([lim[i][1] - lim[i][0] for i in range(3)])
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
    ax.set_title(title, fontsize=10)


# --------------------------------------------------------------- pièces
def plot_pieces(pieces, path="viz_pieces.png"):
    fig = plt.figure(figsize=(12, 7))
    for k, (name, cells) in enumerate(pieces.items()):
        ax = fig.add_subplot(2, 3, k + 1, projection="3d")
        # repère de saisie : i -> x (A à gauche), u -> y (AV devant), v -> z (H en haut)
        draw(ax, cells, COLORS[k % 6])
        ax.text(-0.8, 0.5, 1, "A", color="k", fontsize=12, weight="bold")
        for i in range(8):
            ax.text(i + 0.4, -0.6, -0.4, str(i + 1), fontsize=7, color="gray")
        setup(ax, [(-1, 9), (0, 2), (0, 2)], f"{name}  (A à gauche, H en haut, AV devant)")
        ax.view_init(elev=28, azim=-70)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
    fig.suptitle("Contrôle de saisie : chaque pièce doit ressembler à la vraie, posée pareil")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("->", path)


# ----------------------------------------------------------- assemblage
def plot_assembly(sol, color_of, path="viz_assemblage.png"):
    fig = plt.figure(figsize=(13, 5))
    views = [(25, -60, "Assemblé"), (25, -60, "Vue éclatée"), (90, -90, "Vue de dessus")]
    for k, (elev, azim, title) in enumerate(views):
        ax = fig.add_subplot(1, 3, k + 1, projection="3d")
        for n, si, _, cs in sol:
            off = (0, 0, 0)
            if title == "Vue éclatée":   # écarte chaque paire le long de sa normale
                ax_, o = G.SLOTS[si]
                s = -2 if o < 0 else 2
                off = {"X": (0, 0, s), "Y": (s, 0, 0), "Z": (0, s, 0)}[ax_]
            draw(ax, cs, color_of[n], off)
        lim = 7 if title == "Vue éclatée" else 5
        setup(ax, [(-lim, lim)] * 3, title)
        ax.view_init(elev=elev, azim=azim)
    handles = [plt.Rectangle((0, 0), 1, 1, color=color_of[n]) for n, *_ in sol]
    labels = [f"{n} : {G.SLOT_NAMES[si]}" for n, si, *_ in sol]
    fig.legend(handles, labels, loc="lower center", ncol=6)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("->", path)


# ------------------------------------------------------------ animation
def _interp(steps, hold=4, final="Terminé"):
    """Images interpolées entre des étapes [(libellé, {pièce: décalage})]."""
    frames = [(steps[0][1], steps[0][0])] * hold
    for (_, a), (label, b) in zip(steps, steps[1:]):
        dist = max(max(abs(x - y) for x, y in zip(a[n], b[n])) for n in a)
        n_img = max(1, int(dist * FRAMES_PER_UNIT))
        for s in range(1, n_img + 1):
            t = s / n_img
            frames.append(({n: tuple(x + t * (y - x) for x, y in zip(a[n], b[n])) for n in a},
                           label))
        frames += [(b, label)] * hold
    frames += [(steps[-1][1], final)] * hold
    return frames


def _film(sol, steps, color_of, path, title, final):
    cells = {n: cs for n, _, _, cs in sol}
    frames = _interp(steps, final=final)
    # cadrage serré : boîte englobante de toutes les pièces sur toutes les étapes
    pts = [(x + o[0], y + o[1], z + o[2]) for _, st in steps for n, o in st.items()
           for x, y, z in cells[n]]
    lims = [(min(p[i] for p in pts) - 1, max(p[i] for p in pts) + 2) for i in range(3)]
    labels = [lab for lab, _ in steps]
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(projection="3d")

    def update(f):
        ax.cla()
        state, label = frames[f]
        for n, off in state.items():
            draw(ax, cells[n], color_of[n], off)
        k = labels.index(label) if label in labels else len(labels) - 1
        setup(ax, lims, f"{title} {k}/{len(labels) - 1} : {label}")
        ax.view_init(elev=25, azim=-60)

    anim = FuncAnimation(fig, update, frames=len(frames))
    anim.save(path, writer=PillowWriter(fps=8))
    plt.close(fig)
    print("->", path, f"({len(frames)} images)")


def animate(sol, moves, color_of, path="viz_demontage.gif"):
    steps = keyframes([n for n, *_ in sol], moves, SORT_DIST, {n: cs for n, _, _, cs in sol})
    _film(sol, steps, color_of, path, "Démontage", "Démonté")


def animate_montage(sol, moves, color_of, path="viz_montage.gif"):
    steps = assembly_steps([n for n, *_ in sol], moves, SORT_DIST, {n: cs for n, _, _, cs in sol})
    _film(sol, steps, color_of, path, "Montage", "Assemblé")


# ------------------------------------------------------------------ main
def run(csv_path, which=1, out_dir="outputs"):
    os.makedirs(out_dir, exist_ok=True)
    pieces, _ = load_pieces(csv_path)
    color_of = {n: COLORS[k % 6] for k, n in enumerate(pieces)}
    plot_pieces(pieces, os.path.join(out_dir, "viz_pieces.png"))
    good = []
    sols, _ = unique_assemblies(pieces)
    for sol in sols:
        res = disassemble({n: cs for n, _, _, cs in sol})
        if res:
            good.append((sol, res))
    print(f"{len(sols)} assemblage(s), dont {len(good)} démontable(s).")
    if not good:
        print("Rien à animer : vérifie la saisie avec viz_pieces.png.")
        return
    sol, (moves, _level) = good[min(which, len(good)) - 1]
    plot_assembly(sol, color_of, os.path.join(out_dir, "viz_assemblage.png"))
    animate(sol, moves, color_of, os.path.join(out_dir, "viz_demontage.gif"))
    animate_montage(sol, moves, color_of, os.path.join(out_dir, "viz_montage.gif"))
