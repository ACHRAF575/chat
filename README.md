# Buckshot Arena (Flask Multiplayer)

A lightweight multiplayer Buckshot Roulette-inspired game clone.

## Features
- 2-player room system (create / join by code)
- Turn-based shooting (`self` or `opponent`)
- Randomized magazine with live/blank shells
- Blank self-shot keeps your turn
- Real-time state sync with Socket.IO
- Browser client with a simple Three.js 3D scene

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in two browser tabs.
