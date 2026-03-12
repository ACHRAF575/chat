import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import RoomState, load_new_magazine


def test_load_new_magazine_assigns_shells_and_rounds():
    room = RoomState(code="ABCDE", players=["A", "B"], hp={"A": 4, "B": 4})
    load_new_magazine(room)

    assert 4 <= len(room.shells) <= 8
    assert 0 < sum(room.shells) < len(room.shells)
    assert room.rounds_left["A"] == len(room.shells)
    assert room.rounds_left["B"] == len(room.shells)
