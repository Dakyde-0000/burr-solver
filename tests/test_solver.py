from pathlib import Path

import pytest

from burr_solver import disassemble, load_pieces, unique_assemblies
from burr_solver.geometry import SLOTS, L, orientations, place
from burr_solver.io import PieceError, from_code, piece_code
from burr_solver.viz3d import build_data

DATA = Path(__file__).resolve().parents[1] / "data"
SOLID = frozenset((i, u, v) for i in range(L) for u in (0, 1) for v in (0, 1))


def test_solid_piece_has_one_orientation():
    assert len(orientations(SOLID)) == 1


def test_asymmetric_piece_has_eight_orientations():
    piece = SOLID - {(2, 0, 1)}
    assert len(orientations(piece)) == 8


def test_orientations_keep_volume():
    piece = SOLID - {(2, 0, 1), (3, 1, 0)}
    assert all(len(cs) == len(piece) for _, cs in orientations(piece))


def test_crossing_slots_share_four_cubes():
    cells = [place(SOLID, s) for s in SLOTS]
    assert len(cells[1] & cells[3]) == 4   # X-haut / Y-haut
    assert not cells[0] & cells[1]         # deux pièces parallèles ne se coupent pas


def test_my_burr_is_solved():
    """Mon burr en bois : une seule solution, niveau 1, P6 (pièce pleine) sort en premier."""
    pieces, _ = load_pieces(DATA / "mes_pieces.csv")
    sols, _ = unique_assemblies(pieces)
    assert len(sols) == 1
    res = disassemble({n: cs for n, _, _, cs in sols[0]})
    assert res is not None
    moves, level = res
    assert level == 1
    assert moves[0][0] == ["P6"] and moves[0][2] == "SORT"


def test_invalid_cube_code(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("piece;unite;cube\nP1;3;XYZ\n", encoding="utf-8")
    with pytest.raises(PieceError):
        load_pieces(f)


def _write(tmp_path, rows):
    f = tmp_path / "t.csv"
    f.write_text("piece;unite;cube\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return f


def _five_plain(extra):
    return extra + [f"P{k};;" for k in range(2, 7)]


def test_piece_cut_in_two_is_rejected(tmp_path):
    rows = _five_plain([f"P1;5;{c}" for c in ("HAV", "HAR", "BAV", "BAR")])
    with pytest.raises(PieceError, match="seul tenant"):
        load_pieces(_write(tmp_path, rows))


def test_notch_outside_units_3_to_6_is_rejected(tmp_path):
    with pytest.raises(PieceError, match="hors des unités"):
        load_pieces(_write(tmp_path, _five_plain(["P1;2;HAV"])))


def test_duplicate_line_is_rejected(tmp_path):
    with pytest.raises(PieceError, match="doublon"):
        load_pieces(_write(tmp_path, _five_plain(["P1;4;HAV", "P1;4;HAV"])))


def test_wrong_number_of_pieces_is_rejected(tmp_path):
    with pytest.raises(PieceError, match="il en faut 6"):
        load_pieces(_write(tmp_path, ["P1;4;HAV"]))


def test_compact_code_round_trip():
    removed = {(4, "HAR"), (4, "BAR"), (5, "BAV"), (5, "BAR"), (5, "HAR")}
    assert piece_code(removed) == "0000-0101-0111-0000"
    assert from_code("0000-0101-0111-0000") == removed


def test_viewer_data_contains_all_cubes():
    pieces, removed = load_pieces(DATA / "mes_pieces.csv")
    sol = unique_assemblies(pieces)[0][0]
    data = build_data(pieces, removed, sol)
    assert [len(p["cells"]) for p in data["pieces"]] == [len(c) for c in pieces.values()]
    assert len(data["assembly"]) == 6


def test_assembly_steps_end_assembled_without_overlap():
    name = "mes_pieces.csv"
    from burr_solver.disassembly import assembly_steps, shift
    pieces, _ = load_pieces(DATA / name)
    sol = unique_assemblies(pieces)[0][0]
    cells = {n: cs for n, _, _, cs in sol}
    moves, _ = disassemble(cells)
    steps = assembly_steps(list(cells), moves, 8, cells)
    assert all(off == (0, 0, 0) for off in steps[-1][1].values())
    start = [shift(cells[n], off) for n, off in steps[0][1].items()]
    assert not any(start[i] & start[j] for i in range(6) for j in range(i + 1, 6))
