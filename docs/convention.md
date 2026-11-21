# Convention de saisie des pièces

Chaque pièce est vue comme un bloc de **2 × 2 × 8 petits cubes**
(unité = moitié de la section de la pièce). On ne décrit que les cubes **enlevés**.

## Poser la pièce

1. Marque une extrémité au crayon : c'est l'**extrémité A**.
2. Pose la pièce à plat devant toi, **A à gauche**.
3. Tourne-la pour que la face portant la plus grande entaille soit **en haut** (face H).
4. **AV** = la moitié côté toi, **AR** = la moitié opposée.

Ce repère est direct : il évite de décrire par erreur la version *miroir* d'une
pièce, qui n'est pas la même pièce.

## Coder les cubes

| colonne | valeurs | sens |
|---|---|---|
| `piece` | `P1` … `P6` | identifiant libre |
| `unite` | `1` … `8` | position le long de la pièce, comptée depuis A |
| `cube` | `HAV`, `HAR`, `BAV`, `BAR` | Haut/Bas × Avant/Arrière |

Les entailles d'un burr classique se trouvent dans les unités 3 à 6.
Une pièce sans entaille s'écrit sur une seule ligne : `P6;;`.

```
piece;unite;cube
P1;3;HAV
P1;3;HAR
```

## Code compact

`burr-solver pieces` affiche pour chaque pièce un code de 16 chiffres :
4 chiffres par unité 3 à 6, dans l'ordre `HAV HAR BAV BAR`, `1` = cube enlevé.

| code | lecture |
|---|---|
| `0000-0101-0111-0000` | unité 4 : moitié arrière creusée sur toute la hauteur ; unité 5 : seul le cube haut-avant reste |

Un groupe `1111` signifie que les 4 cubes d'une unité sont enlevés : la pièce
serait coupée en deux, la table est alors refusée.

## Vérifier sa saisie

`burr-solver vue3d data/mes_pieces.csv` produit `outputs/vue3d.html` :
chaque pièce y est dessinée en 3D dans ce même repère (A à gauche, H en haut,
AV vers soi). Pose la vraie pièce de la
même façon et compare.

## Repère global du burr assemblé

Le cœur assemblé est un cube 4 × 4 × 4. Les 6 emplacements sont nommés
`X-bas`, `X-haut`, `Y-bas`, `Y-haut`, `Z-bas`, `Z-haut` (axe de la pièce,
puis position de la paire). Pour chaque pièce, le solveur indique de quel
côté pointe l'extrémité A et vers où regarde la face H.
