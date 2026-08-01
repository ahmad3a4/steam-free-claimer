"""
app.py -- Steam Free Games Claimer Web App
Flask backend that handles Steam API calls server-side (bypassing browser CORS).
Maintained by ahmad3a4 - https://github.com/ahmad3a4/steam-free-claimer
"""

import time
from flask import Flask, render_template, request, jsonify
from steam_client import SteamClient
from steam_auth import SteamAuth, SteamLoginError

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


# ── Routes ───────────────────────────────────────────────────────────────────

# ── Login endpoints ─────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    """
    Step 1: Authenticate with Steam username + password.
    Returns 2FA info if Steam Guard is enabled, or session cookies on success.
    """
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    try:
        result = SteamAuth().begin_login(username, password)
        return jsonify(result)
    except SteamLoginError as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": f"Login error: {exc}"}), 500


@app.route("/api/login/verify", methods=["POST"])
def api_login_verify():
    """
    Step 2 (if 2FA needed): Submit Steam Guard code and finalize login.
    Returns session cookies on success.
    """
    data       = request.get_json(silent=True) or {}
    client_id  = str(data.get("client_id",  ""))
    steamid    = str(data.get("steamid",    ""))
    request_id = str(data.get("request_id", ""))
    code       = data.get("code",      "").strip().upper()
    code_type  = int(data.get("code_type", 3))

    if not code:
        return jsonify({"error": "Please enter your Steam Guard code."}), 400

    try:
        result = SteamAuth().verify_2fa(client_id, steamid, request_id, code, code_type)
        return jsonify(result)
    except SteamLoginError as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": f"2FA error: {exc}"}), 500


# ── Page & game endpoints ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    """
    Authenticate with Steam and find all currently free games.
    Body: { sessionid, loginSecure }
    Returns: { games: [...], count: N }
    """
    data = request.get_json(silent=True) or {}
    session_id   = data.get("sessionid", "").strip()
    login_secure = data.get("loginSecure", "").strip()

    if not session_id or not login_secure:
        return jsonify({"error": "Both sessionid and steamLoginSecure are required."}), 400

    client = SteamClient(session_id, login_secure)

    if not client.is_authenticated():
        return jsonify({
            "error": "Authentication failed. Your cookies may be expired. "
                     "Log out of Steam, log back in, and copy fresh cookies."
        }), 401

    games = client.get_free_games()

    results = []
    for game in games:
        packages = client.get_free_packages(game["appid"])
        results.append({
            "appid":            game["appid"],
            "name":             game["name"],
            "packages":         packages,
            "has_free_packages": len(packages) > 0,
            "store_url":        f"https://store.steampowered.com/app/{game['appid']}/",
        })

    return jsonify({"games": results, "count": len(results)})


@app.route("/api/claim", methods=["POST"])
def api_claim():
    """
    Claim each free package in the provided games list.
    Body: { sessionid, loginSecure, games: [...] }
    Returns: { results: [...], summary: { claimed, already_owned, skipped, failed } }
    """
    data = request.get_json(silent=True) or {}
    session_id   = data.get("sessionid", "").strip()
    login_secure = data.get("loginSecure", "").strip()
    games        = data.get("games", [])

    if not session_id or not login_secure:
        return jsonify({"error": "Missing cookies."}), 400

    client = SteamClient(session_id, login_secure)

    results = []
    summary = {"claimed": 0, "already_owned": 0, "skipped": 0, "failed": 0}

    for game in games:
        game_result = {
            "appid":    game["appid"],
            "name":     game["name"],
            "status":   "skipped",
            "packages": [],
        }

        packages = game.get("packages", [])
        if not packages:
            summary["skipped"] += 1
            results.append(game_result)
            continue

        for pkg_id in packages:
            time.sleep(1.2)
            success, msg = client.claim_package(pkg_id)
            game_result["packages"].append({"packageid": pkg_id, "status": msg})

            if success:
                game_result["status"] = "claimed"
            elif msg == "already_owned" and game_result["status"] != "claimed":
                game_result["status"] = "already_owned"
            elif game_result["status"] not in ("claimed", "already_owned"):
                game_result["status"] = "failed"

        summary[game_result["status"]] = summary.get(game_result["status"], 0) + 1
        results.append(game_result)

    return jsonify({"results": results, "summary": summary})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Steam Free Games Claimer - Web App")
    print("  by ahmad3a4 - github.com/ahmad3a4/steam-free-claimer")
    print("\n  Running at: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
