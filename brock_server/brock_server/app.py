"""
Morehouse Ultimate roster API
A small Flask server with one real read endpoint.

Author: Brock Caston Jr.
"""

from flask import Flask, jsonify, abort

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Data
# The roster is hard-coded for now (that is allowed for this assignment).
# In a later week this is exactly the kind of data that moves into a database.
# ---------------------------------------------------------------------------
PLAYERS = [
    {"id": 1, "name": "Brock Caston Jr.", "number": 7,  "position": "handler", "class_year": "Junior",    "captain": True},
    {"id": 2, "name": "Marcus Ellison",   "number": 3,  "position": "cutter",  "class_year": "Senior",    "captain": True},
    {"id": 3, "name": "Devon Pierce",     "number": 11, "position": "handler", "class_year": "Sophomore", "captain": False},
    {"id": 4, "name": "Isaiah Grant",     "number": 22, "position": "cutter",  "class_year": "Freshman",  "captain": False},
    {"id": 5, "name": "Terrence Hobbs",   "number": 5,  "position": "cutter",  "class_year": "Junior",    "captain": False},
    {"id": 6, "name": "Andre Whitfield",  "number": 14, "position": "handler", "class_year": "Senior",    "captain": False},
    {"id": 7, "name": "Julian Reeves",    "number": 9,  "position": "cutter",  "class_year": "Sophomore", "captain": False},
    {"id": 8, "name": "Cameron Boyd",     "number": 18, "position": "cutter",  "class_year": "Freshman",  "captain": False},
]


@app.route("/")
def index():
    """API index. Describes what this server offers (not a 'hello world' route)."""
    return jsonify({
        "service": "Morehouse Ultimate roster API",
        "version": "1.0",
        "endpoints": {
            "GET /api/players": "Return the full team roster",
            "GET /api/players/<id>": "Return one player by id",
        },
    })


@app.route("/api/players")
def get_players():
    """The main read endpoint: return the full roster as JSON."""
    return jsonify({"count": len(PLAYERS), "players": PLAYERS})


@app.route("/api/players/<int:player_id>")
def get_player(player_id):
    """Return a single player by id, or 404 if there is no such player."""
    for player in PLAYERS:
        if player["id"] == player_id:
            return jsonify(player)
    abort(404, description=f"No player with id {player_id}")


if __name__ == "__main__":
    # Listen on 0.0.0.0 so the server is reachable when run on another machine,
    # not only from the laptop it was written on.
    app.run(host="0.0.0.0", port=5000, debug=True)
