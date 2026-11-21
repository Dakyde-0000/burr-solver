"""Visionneuse 3D interactive (page HTML autonome, three.js chargé depuis un CDN).

    burr-solver vue3d data/pieces.csv  ->  outputs/vue3d.html (à ouvrir dans un navigateur)

Vues : toutes les pièces du lot (repère de saisie), burr assemblé, vue éclatée.
Souris : clic gauche = tourner, molette = zoom, clic droit = déplacer.
"""
import json
import os

from .assembly import unique_assemblies
from .disassembly import assembly_steps, disassemble
from .geometry import SLOT_NAMES, SLOTS
from .io import load_pieces, piece_code

COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4"]


def _to_three(x, y, z):
    """Repère du projet (x droite, y vers l'arrière, z haut) -> three.js (y haut, z vers l'écran)."""
    return [x, z, -y]


def build_data(pieces, removed, solution=None, moves=None):
    data = {"pieces": [], "assembly": None, "montage": None}
    for k, (name, cells) in enumerate(pieces.items()):
        data["pieces"].append({
            "name": name,
            "code": piece_code(removed[name]),
            "color": COLORS[k % len(COLORS)],
            "cells": [_to_three(i, u, v) for i, u, v in sorted(cells)],
        })
    if solution:
        asm = []
        for name, si, _, cs in solution:
            ax, o = SLOTS[si]
            s = -3 if o < 0 else 3
            explode = {"X": (0, 0, s), "Y": (s, 0, 0), "Z": (0, s, 0)}[ax]
            asm.append({"name": name, "slot": SLOT_NAMES[si],
                        "cells": [_to_three(*c) for c in sorted(cs)],
                        "explode": _to_three(*explode)})
        data["assembly"] = asm
    if solution and moves is not None:
        cells = {n: cs for n, _, _, cs in solution}
        data["montage"] = [{"label": lab, "pos": {n: _to_three(*o) for n, o in st.items()}}
                           for lab, st in assembly_steps(list(cells), moves, 8, cells)]
    return data


HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>burr-solver : vue 3D</title>
<style>
body{margin:0;font-family:system-ui,sans-serif;background:#f6f5f2;color:#222}
#bar{position:absolute;top:0;left:0;right:0;padding:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:rgba(246,245,242,.92)}
button{padding:6px 12px;border:1px solid #999;border-radius:6px;background:#fff;cursor:pointer}
button.on{background:#222;color:#fff}
#legend{display:flex;flex-wrap:wrap;gap:10px;font-size:13px}
#legend label{display:flex;align-items:center;gap:4px;cursor:pointer}
.sw{width:12px;height:12px;border-radius:2px;display:inline-block}
#help{position:absolute;bottom:8px;left:10px;font-size:12px;color:#666}
#steps{position:absolute;bottom:30px;left:10px;right:10px;display:none;flex-wrap:wrap;gap:6px;align-items:center;background:rgba(246,245,242,.92);padding:6px;border-radius:6px}
#s-label{font-size:14px;font-weight:600;margin-left:6px}
canvas{display:block}
</style></head><body>
<div id="bar"><button id="b-pieces" class="on">Pièces du lot</button>
<button id="b-asm">Assemblé</button><button id="b-exp">Éclaté</button><button id="b-mon">Montage</button>
<div id="legend"></div></div>
<div id="steps"><button id="s-first" title="Début">&#9198;</button><button id="s-prev" title="Étape précédente">&#9664;</button><button id="s-play" title="Lecture">&#9654;&#65038; Lecture</button><button id="s-next" title="Étape suivante">&#9654;</button><span id="s-label"></span></div>
<div id="help">Clic gauche : tourner · molette : zoom · clic droit : déplacer. Pièces : A à gauche, face H en haut, AV vers vous.</div>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
const DATA = __DATA__;
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xf6f5f2);
const camera = new THREE.PerspectiveCamera(40, innerWidth/innerHeight, 0.1, 500);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(devicePixelRatio); renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 0.75); sun.position.set(5, 12, 9); scene.add(sun);

const box = new THREE.BoxGeometry(1, 1, 1), edges = new THREE.EdgesGeometry(box);
const lineMat = new THREE.LineBasicMaterial({color: 0x333333});
function block(cells, color) {
  const g = new THREE.Group(), mat = new THREE.MeshLambertMaterial({color});
  for (const [x, y, z] of cells) {
    const m = new THREE.Mesh(box, mat); m.position.set(x + .5, y + .5, z - .5); g.add(m);
    const l = new THREE.LineSegments(edges, lineMat); l.position.copy(m.position); g.add(l);
  }
  return g;
}
function label(text, size) {
  const c = document.createElement("canvas"), ctx = c.getContext("2d");
  ctx.font = "bold 44px system-ui"; c.width = ctx.measureText(text).width + 20; c.height = 60;
  ctx.font = "bold 44px system-ui"; ctx.fillStyle = "#222"; ctx.fillText(text, 10, 46);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({map: new THREE.CanvasTexture(c), depthTest:false}));
  s.scale.set(size * c.width / c.height, size, 1); return s;
}

const views = {pieces: new THREE.Group(), asm: new THREE.Group(), exp: new THREE.Group(), mon: new THREE.Group()};
const byName = {pieces:{}, asm:{}, exp:{}, mon:{}};
DATA.pieces.forEach((p, k) => {
  const g = new THREE.Group();
  g.add(block(p.cells, p.color));
  const t = label(p.name + "   " + p.code, 0.8); t.position.set(4, 3.2, 0); g.add(t);
  const a = label("A", 0.9); a.position.set(-0.8, 1, -0.5); g.add(a);
  g.position.set((k % 2) * 12, -Math.floor(k / 2) * 5, 0);
  views.pieces.add(g); byName.pieces[p.name] = g;
});
const color = Object.fromEntries(DATA.pieces.map(p => [p.name, p.color]));
if (DATA.assembly) for (const a of DATA.assembly) {
  const g1 = block(a.cells, color[a.name]); views.asm.add(g1); byName.asm[a.name] = g1;
  const g2 = block(a.cells, color[a.name]); g2.position.set(...a.explode);
  views.exp.add(g2); byName.exp[a.name] = g2;
  const g3 = block(a.cells, color[a.name]); views.mon.add(g3); byName.mon[a.name] = g3;
}
for (const v of Object.values(views)) scene.add(v);

let current = "pieces";
function show(v) {
  if (v !== "pieces" && !DATA.assembly) { alert("Aucune solution démontable trouvée pour ce lot."); return; }
  current = v; stop();
  for (const [k, g] of Object.entries(views)) g.visible = (k === v);
  for (const id of ["pieces", "asm", "exp", "mon"]) document.getElementById("b-" + id).classList.toggle("on", id === v);
  document.getElementById("steps").style.display = v === "mon" ? "flex" : "none";
  if (v === "mon") { goTo(0, false); const r = reach(); controls.target.set(0, 0, 0);
    camera.position.set(r * 0.9, r * 0.75, r * 1.2); controls.update(); return; }
  if (v === "pieces") { controls.target.set(10, -4, 0); camera.position.set(10, 2, Math.max(30, 34 / camera.aspect)); }
  else { controls.target.set(0, 0, 0); const d = Math.max(1, 1.2 / camera.aspect); camera.position.set(12 * d, 10 * d, 16 * d); }
  controls.update();
}
const legend = document.getElementById("legend");
for (const p of DATA.pieces) {
  const slot = DATA.assembly ? " (" + DATA.assembly.find(a => a.name === p.name).slot + ")" : "";
  const l = document.createElement("label");
  l.innerHTML = `<input type="checkbox" checked><span class="sw" style="background:${p.color}"></span>${p.name}${slot}`;
  l.querySelector("input").onchange = e => {
    for (const v of ["pieces", "asm", "exp", "mon"]) if (byName[v][p.name]) byName[v][p.name].visible = e.target.checked;
  };
  legend.appendChild(l);
}
document.getElementById("b-pieces").onclick = () => show("pieces");
document.getElementById("b-asm").onclick = () => show("asm");
document.getElementById("b-exp").onclick = () => show("exp");
document.getElementById("b-mon").onclick = () => show("mon");

// ---- montage pas à pas : interpolation entre les étapes calculées par le solveur
const M = DATA.montage || [];
let step = 0, anim = null, playing = null;
function reach() {
  let r = 10;
  for (const s of M) for (const p of Object.values(s.pos)) r = Math.max(r, ...p.map(Math.abs));
  return r + 12;
}
function place(pos) { for (const [n, p] of Object.entries(pos)) byName.mon[n].position.set(...p); }
function stepLabel() {
  document.getElementById("s-label").textContent =
    M.length ? `Étape ${step}/${M.length - 1} : ${M[step].label}` : "Pas de séquence de montage";
}
function goTo(k, animate = true) {
  if (!M.length) { stepLabel(); return; }
  k = Math.max(0, Math.min(M.length - 1, k));
  const from = Object.fromEntries(Object.keys(M[k].pos).map(n => [n, byName.mon[n].position.toArray()]));
  step = k; stepLabel();
  if (!animate) { place(M[k].pos); return; }
  const t0 = performance.now(), dur = 700;
  anim = () => {
    const t = Math.min(1, (performance.now() - t0) / dur), e = t * t * (3 - 2 * t);
    for (const [n, p] of Object.entries(M[k].pos))
      byName.mon[n].position.set(...from[n].map((a, i) => a + e * (p[i] - a)));
    if (t >= 1) anim = null;
  };
}
function stop() { clearInterval(playing); playing = null; document.getElementById("s-play").innerHTML = "&#9654;&#65038; Lecture"; }
document.getElementById("s-first").onclick = () => { stop(); goTo(0, false); };
document.getElementById("s-prev").onclick = () => { stop(); goTo(step - 1); };
document.getElementById("s-next").onclick = () => { stop(); goTo(step + 1); };
document.getElementById("s-play").onclick = () => {
  if (playing) { stop(); return; }
  if (step >= M.length - 1) goTo(0, false);
  document.getElementById("s-play").innerHTML = "&#10074;&#10074; Pause";
  playing = setInterval(() => { if (step >= M.length - 1) stop(); else goTo(step + 1); }, 1200);
};
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
show("pieces");
(function loop() { requestAnimationFrame(loop); if (anim) anim(); controls.update(); renderer.render(scene, camera); })();
</script></body></html>
"""


def run(csv_path, out_dir="outputs", which=1):
    pieces, removed = load_pieces(csv_path)
    solution = moves = None
    good = []
    for s in unique_assemblies(pieces)[0]:
        res = disassemble({n: cs for n, _, _, cs in s})
        if res:
            good.append((s, res[0]))
    if good:
        solution, moves = good[min(which, len(good)) - 1]
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "vue3d.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML.replace("__DATA__", json.dumps(build_data(pieces, removed, solution, moves))))
    print("->", path, "(à ouvrir dans un navigateur)")
    return path
