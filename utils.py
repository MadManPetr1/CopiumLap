import os, json, random


def load_lines(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_leaderboard(leaderboard, leaderboard_file):
    with open(leaderboard_file, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f)


def load_leaderboard(leaderboard_file):
    leaderboard = {}
    if os.path.exists(leaderboard_file):
        with open(leaderboard_file, "r", encoding="utf-8") as f:
            try:
                leaderboard.update(json.load(f))
            except Exception:
                leaderboard.clear()
    return leaderboard


def random_gain(mode):
    if mode == "motivation":
        return random.randint(8, 12)
    if mode == "insult":
        return random.randint(4, 16)
    if mode == "excuse":
        return random.randint(-2, 0)
    if mode == "flip":
        return random.randint(-30, 40)
    return 0
