from flask import Flask, render_template, request, session
import random, time, json, os

app = Flask(__name__)
app.secret_key = 'ADC-diff'

# --- File Paths ---
LEADERBOARD_FILE = "leaderboard.json"
INSULTS_FILE = "insults.txt"
MOTIVATIONS_FILE = "motivations.txt"
EXCUSES_FILE = "excuses.txt"
SUGGESTIONS_FILE = "suggestions.txt"

# --- Content Loaders ---
def load_lines(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

INSULTS = load_lines(INSULTS_FILE)
MOTIVATIONS = load_lines(MOTIVATIONS_FILE)
EXCUSES = load_lines(EXCUSES_FILE)

# --- Leaderboard Persistence ---
leaderboard = {}
def save_leaderboard():
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f)
def load_leaderboard():
    global leaderboard
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            try:
                leaderboard.update(json.load(f))
            except Exception:
                leaderboard.clear()
load_leaderboard()

# --- Session/Points/History Helpers ---
def add_history(key, msg):
    if key not in session or not isinstance(session.get(key), list):
        session[key] = []
    hist = session[key]
    hist = [msg] + hist
    session[key] = hist[:2]
def get_history(key):
    if key not in session or not isinstance(session.get(key), list):
        session[key] = []
    return session.get(key, [])
def get_points():
    if "points" not in session or not isinstance(session.get("points"), int):
        session["points"] = 0
    return session.get("points", 0)
def set_points(val):
    session["points"] = max(int(val), 0)

def add_points_history(new_points):
    if "points_history" not in session or not isinstance(session["points_history"], list):
        session["points_history"] = []
    hist = session["points_history"]
    hist.append(new_points)
    session["points_history"] = hist[-20:]

def update_leaderboard(name, pts, timer):
    if not name:
        return
    leaderboard[name] = {
        "points": pts,
        "timer": timer,
        "last_update": int(time.time())
    }
    save_leaderboard()
def get_sorted_leaderboard():
    return sorted(leaderboard.items(), key=lambda x: (-x[1]['points'], -x[1]['timer'], x[0]))

# --- Cooldown Helpers ---
def get_cooldown(key):
    expires = session.get(f"cd_{key}", 0)
    left = expires - time.time()
    return max(int(left + 0.99), 0)
def set_cooldown(key, seconds):
    session[f"cd_{key}"] = time.time() + seconds

# --- Gain/Loss (Single Last Only) ---
def set_last_gain(source, value):
    session["last_gain"] = (source, value)
def get_last_gain():
    lg = session.get("last_gain")
    if isinstance(lg, (list, tuple)) and len(lg) == 2:
        return lg
    return None, None

@app.route("/", methods=["GET", "POST"])
def index():
    if 'timer_start' not in session or not isinstance(session.get('timer_start'), int):
        session['timer_start'] = int(time.time())
    timer = session['timer_start']
    username = session.get("username", "")
    points = get_points()

    cd_main = get_cooldown("main")
    cd_excuse = get_cooldown("excuse")
    cd_flip = get_cooldown("flip")

    # Suggestion logic
    suggest_feedback = ""
    if request.method == "POST" and "suggestion" in request.form:
        suggestion = request.form.get("suggestion", "").strip()[:160]
        category = request.form.get("category", "")
        if suggestion and category in ("insult", "motivation"):
            with open(SUGGESTIONS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{category.upper()}: {suggestion}\n")
            suggest_feedback = "Thanks for your suggestion! Pending review."
        else:
            suggest_feedback = "Invalid suggestion."

    # Username input/leaderboard update
    if request.method == "POST" and "username" in request.form:
        username = request.form["username"].strip()[:18]
        session["username"] = username
        update_leaderboard(username, points, int(time.time()) - timer)

    # Mode (motivation/insult)
    mode = request.form.get("mode", session.get("mode", "motivation"))
    session["mode"] = mode

    # Motivation/Insult reroll
    if request.method == "POST" and (("reroll" in request.form) or ("mode" in request.form)):
        if cd_main == 0:
            set_cooldown("main", 1)
            if mode == "motivation":
                msg = random.choice(MOTIVATIONS) if MOTIVATIONS else "No Motivations Loaded."
                gain = random.randint(8, 12)
                set_last_gain("Motivation", gain)
            else:
                msg = random.choice(INSULTS) if INSULTS else "No Insults Loaded."
                gain = random.randint(4, 16)
                set_last_gain("Insult", gain)
            session["main_msg"] = msg
            add_history(f"{mode}_history", msg)
            points = get_points() + gain
            set_points(points)
            add_points_history(get_points())
            if username:
                update_leaderboard(username, points, int(time.time()) - timer)

    # Excuse reroll
    if request.method == "POST" and "excuse_reroll" in request.form:
        if cd_excuse == 0:
            set_cooldown("excuse", 1)
            excuse = random.choice(EXCUSES) if EXCUSES else "No Excuses Loaded."
            pts = random.randint(-2, 0)
            set_last_gain("Excuse", pts)
            session["excuse_msg"] = excuse
            add_history("excuse_history", excuse)
            points = get_points() + pts
            set_points(points)
            add_points_history(get_points())
            if username:
                update_leaderboard(username, points, int(time.time()) - timer)

    # Flip
    if request.method == "POST" and "flip" in request.form:
        if cd_flip == 0:
            set_cooldown("flip", 5)
            flip = random.randint(-30, 40)
            set_last_gain("Flip", flip)
            points = get_points() + flip
            set_points(points)
            add_points_history(get_points())
            if username:
                update_leaderboard(username, points, int(time.time()) - timer)

    # On first load, set main_msg/excuse_msg if not present
    if "main_msg" not in session:
        msg = random.choice(MOTIVATIONS if mode == "motivation" else INSULTS) if (MOTIVATIONS or INSULTS) else "No Content Loaded."
        session["main_msg"] = msg
        add_history(f"{mode}_history", msg)
    if "excuse_msg" not in session:
        excuse = random.choice(EXCUSES) if EXCUSES else "No Excuses Loaded."
        session["excuse_msg"] = excuse
        add_history("excuse_history", excuse)

    main_history = get_history(f"{mode}_history")
    excuse_history = get_history("excuse_history")
    last_gain_source, last_gain_value = get_last_gain()
    points_history = session.get("points_history", [])
    if username:
        update_leaderboard(username, get_points(), int(time.time()) - timer)
    leader = get_sorted_leaderboard()[:8]

    return render_template(
        "main.html",
        msg=session["main_msg"],
        mode=mode,
        points=get_points(),
        timer=timer,
        excuse=session["excuse_msg"],
        main_history=main_history,
        excuse_history=excuse_history,
        leader=leader,
        username=username,
        cd_main=cd_main if cd_main else None,
        cd_excuse=cd_excuse if cd_excuse else None,
        cd_flip=cd_flip if cd_flip else None,
        gains_source=last_gain_source,
        gains_value=last_gain_value,
        points_history=points_history,
        suggest_feedback=suggest_feedback,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)