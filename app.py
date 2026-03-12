from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from typing import Any

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room


app = Flask(__name__)
app.config["SECRET_KEY"] = "buckshot-clone-secret"
socketio = SocketIO(app, cors_allowed_origins="*")


def make_room_code(length: int = 5) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


@dataclass
class RoomState:
    code: str
    players: list[str] = field(default_factory=list)
    hp: dict[str, int] = field(default_factory=dict)
    turn_index: int = 0
    shells: list[bool] = field(default_factory=list)  # True = live round, False = blank
    rounds_left: dict[str, int] = field(default_factory=dict)
    winner: str | None = None

    @property
    def current_player(self) -> str:
        return self.players[self.turn_index] if self.players else ""

    def public_state(self) -> dict[str, Any]:
        return {
            "players": self.players,
            "hp": self.hp,
            "turn": self.current_player,
            "shells_total": len(self.shells),
            "live_count": sum(1 for s in self.shells if s),
            "blank_count": sum(1 for s in self.shells if not s),
            "rounds_left": self.rounds_left,
            "winner": self.winner,
        }


ROOMS: dict[str, RoomState] = {}
SID_TO_NAME: dict[str, str] = {}
SID_TO_ROOM: dict[str, str] = {}


def load_new_magazine(room: RoomState) -> None:
    chamber_size = random.randint(4, 8)
    live = random.randint(1, chamber_size - 1)
    blank = chamber_size - live
    room.shells = [True] * live + [False] * blank
    random.shuffle(room.shells)
    for player in room.players:
        room.rounds_left[player] = len(room.shells)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@socketio.on("create_room")
def create_room(payload: dict[str, Any]) -> None:
    name = (payload.get("name") or "").strip()
    if not name:
        emit("error_message", {"message": "Name is required."})
        return

    code = make_room_code()
    while code in ROOMS:
        code = make_room_code()

    room = RoomState(code=code)
    room.players.append(name)
    room.hp[name] = 4
    ROOMS[code] = room

    join_room(code)
    SID_TO_NAME[request.sid] = name
    SID_TO_ROOM[request.sid] = code

    emit("room_joined", {"room": code, "you": name, "is_host": True, "state": room.public_state()})


@socketio.on("join_room")
def join_existing(payload: dict[str, Any]) -> None:
    name = (payload.get("name") or "").strip()
    code = (payload.get("room") or "").strip().upper()
    if not name or not code:
        emit("error_message", {"message": "Name and room are required."})
        return

    room = ROOMS.get(code)
    if room is None:
        emit("error_message", {"message": "Room not found."})
        return

    if len(room.players) >= 2:
        emit("error_message", {"message": "Room is full."})
        return

    if name in room.players:
        emit("error_message", {"message": "Name is already in use in this room."})
        return

    room.players.append(name)
    room.hp[name] = 4
    join_room(code)
    SID_TO_NAME[request.sid] = name
    SID_TO_ROOM[request.sid] = code

    emit("room_joined", {"room": code, "you": name, "is_host": False, "state": room.public_state()})
    emit("state_update", {"state": room.public_state(), "message": f"{name} joined the room."}, room=code)


@socketio.on("start_game")
def start_game() -> None:
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code:
        return

    room = ROOMS.get(room_code)
    if room is None or len(room.players) != 2:
        emit("error_message", {"message": "Need exactly 2 players."})
        return

    room.turn_index = random.randint(0, 1)
    room.winner = None
    load_new_magazine(room)

    emit(
        "state_update",
        {
            "state": room.public_state(),
            "message": f"Game started. {room.current_player} takes the first turn.",
        },
        room=room_code,
    )


@socketio.on("shoot")
def shoot(payload: dict[str, Any]) -> None:
    target_mode = payload.get("target")

    sid = request.sid
    shooter = SID_TO_NAME.get(sid)
    room_code = SID_TO_ROOM.get(sid)
    if not shooter or not room_code:
        return

    room = ROOMS.get(room_code)
    if room is None or room.winner is not None:
        return

    if room.current_player != shooter:
        emit("error_message", {"message": "It is not your turn."})
        return

    if len(room.players) != 2:
        emit("error_message", {"message": "Waiting for opponent."})
        return

    opponent = room.players[1] if room.players[0] == shooter else room.players[0]

    if not room.shells:
        load_new_magazine(room)

    shell = room.shells.pop(0)

    if target_mode == "self":
        target = shooter
    else:
        target = opponent

    msg = f"{shooter} fires at {target}. "
    switch_turn = True

    if shell:
        room.hp[target] = max(0, room.hp[target] - 1)
        msg += "💥 Live round!"
    else:
        msg += "click... blank shell."
        if target == shooter:
            switch_turn = False
            msg += " Shooter keeps the turn."

    for player in room.players:
        room.rounds_left[player] = len(room.shells)

    if room.hp[target] <= 0:
        room.winner = shooter
        msg += f" {shooter} wins the match!"
    elif switch_turn:
        room.turn_index = 1 - room.turn_index

    if not room.shells and room.winner is None:
        load_new_magazine(room)
        msg += " New magazine loaded."

    emit("state_update", {"state": room.public_state(), "message": msg}, room=room_code)


@socketio.on("disconnect")
def on_disconnect() -> None:
    sid = request.sid
    room_code = SID_TO_ROOM.pop(sid, None)
    name = SID_TO_NAME.pop(sid, None)
    if not room_code or not name:
        return

    room = ROOMS.get(room_code)
    if room is None:
        return

    if name in room.players:
        room.players.remove(name)
        room.hp.pop(name, None)
        room.rounds_left.pop(name, None)

    if not room.players:
        ROOMS.pop(room_code, None)
    else:
        emit(
            "state_update",
            {
                "state": room.public_state(),
                "message": f"{name} disconnected.",
            },
            room=room_code,
        )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
