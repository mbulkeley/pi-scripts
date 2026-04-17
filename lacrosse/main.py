import os
import requests
from datetime import date, timedelta
from bs4 import BeautifulSoup

WATCHED_TEAMS = ["Delaware", "Denver", "Air Force"]

def format_scoreboard(games):
    """Format a list of game dicts into a monospace scoreboard code block.

    Each game dict: {status, home, home_score, away, away_score, is_watched}
    """
    lines = []
    for i in range(0, len(games), 2):
        left = games[i]
        right = games[i + 1] if i + 1 < len(games) else None

        marker = "* " if left["is_watched"] else "  "
        if right:
            r_marker = "* " if right["is_watched"] else "  "
            lines.append(f"{marker}{left['status']:<28}{r_marker}{right['status']}")
            lines.append(f"  {left['home']:<22}{left['home_score']:<8}  {right['home']:<22}{right['home_score']}")
            lines.append(f"  {left['away']:<22}{left['away_score']:<8}  {right['away']:<22}{right['away_score']}")
        else:
            lines.append(f"{marker}{left['status']}")
            lines.append(f"  {left['home']:<22}{left['home_score']}")
            lines.append(f"  {left['away']:<22}{left['away_score']}")

        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    return "```\n" + "\n".join(lines) + "\n```"


def get_d1_scores(for_date=None):
    yesterday = for_date or (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/lacrosse"
        f"/mens-college-lacrosse/scoreboard?dates={yesterday}"
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    games = []

    for event in data.get("events", []):
        for competition in event.get("competitions", []):
            status = competition.get("status", {}).get("type", {}).get("name", "")
            if status != "STATUS_FINAL":
                continue

            competitors = competition.get("competitors", [])
            home = next((c for c in competitors if c["homeAway"] == "home"), None)
            away = next((c for c in competitors if c["homeAway"] == "away"), None)
            if not home or not away:
                continue

            home_name = (home["team"].get("shortDisplayName") or home["team"]["displayName"]).removesuffix(" University")
            away_name = (away["team"].get("shortDisplayName") or away["team"]["displayName"]).removesuffix(" University")
            home_score = int(home.get("score", 0))
            away_score = int(away.get("score", 0))

            is_watched = any(
                t.lower() in home_name.lower() or t.lower() in away_name.lower()
                for t in WATCHED_TEAMS
            )

            games.append({
                "status": "FINAL",
                "home": home_name, "home_score": home_score,
                "away": away_name, "away_score": away_score,
                "is_watched": is_watched,
            })

    if not games:
        return None, "No NCAA D1 lacrosse games yesterday."

    # Watched games first, then others
    games.sort(key=lambda g: (0 if g["is_watched"] else 1))

    return games, None


def get_csu_mcla_result():
    url = "https://mcla.us/teams/colorado-state/2026"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tiles = soup.find_all("div", class_="game-opponent-tile")

    last_game = None
    for tile in tiles:
        outcome_span = tile.find("span", class_="outcome")
        if not outcome_span:
            continue

        date_div = tile.find("div", class_="game-opponent-tile__date")
        date_parts = [p.get_text(strip=True) for p in date_div.find_all("p")] if date_div else []
        game_date = " ".join(date_parts)

        name_p = tile.find("p", class_="opponent__name")
        opponent = name_p.get_text(separator=" ", strip=True) if name_p else "Unknown"

        outcome = outcome_span.get_text(strip=True)
        score_span = tile.find("span", class_="score")
        score = score_span.get_text(strip=True) if score_span else "?"

        type_div = tile.find("div", class_="game-opponent-tile__type")
        game_type = type_div.get_text(strip=True) if type_div else ""

        last_game = {
            "date": game_date,
            "opponent": opponent,
            "outcome": outcome,
            "score": score,
            "type": game_type,
        }

    if not last_game:
        return "_No CSU MCLA results found._"

    outcome = last_game["outcome"]
    type_label = f"  _{last_game['type']}_" if last_game["type"] else ""
    return (
        f"*{outcome}* {last_game['score']}  vs {last_game['opponent']}"
        f"   _{last_game['date']}_{type_label}"
    )


def build_blocks(date_str, d1_text, csu_text):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*CSU MCLA — Latest Result*\n{csu_text}",
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"NCAA D1 Lacrosse — {date_str}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": d1_text},
        },
    ]
    return blocks


def post_to_slack(blocks, fallback_text):
    webhook_url = os.environ.get("SLACK_WEBHOOK_ICEMAN")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_ICEMAN environment variable not set")

    payload = {"text": fallback_text, "blocks": blocks}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Date to fetch D1 scores for (YYYYMMDD), defaults to yesterday")
    args = parser.parse_args()

    if args.date:
        date_str = datetime.strptime(args.date, "%Y%m%d").strftime("%B %-d, %Y")
    else:
        date_str = (date.today() - timedelta(days=1)).strftime("%B %-d, %Y")

    d1_games, no_games_msg = get_d1_scores(args.date)
    d1_text = format_scoreboard(d1_games) if d1_games else no_games_msg
    csu_text = get_csu_mcla_result()

    blocks = build_blocks(date_str, d1_text, csu_text)

    # Print preview
    print(f"--- CSU MCLA — Latest Result ---\n{csu_text}\n")
    print(f"=== NCAA D1 Lacrosse — {date_str} ===\n")
    print(d1_text)

    post_to_slack(blocks, f"NCAA D1 Lacrosse — {date_str}")
