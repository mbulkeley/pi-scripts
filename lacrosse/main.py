import os
import requests
from datetime import date, timedelta
from bs4 import BeautifulSoup

WATCHED_TEAMS = ["Delaware", "Denver", "Air Force"]


def get_d1_scores(for_date=None):
    yesterday = for_date or (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/lacrosse"
        f"/mens-college-lacrosse/scoreboard?dates={yesterday}"
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    watched = []
    others = []

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

            home_name = home["team"]["displayName"]
            away_name = away["team"]["displayName"]
            home_score = int(home.get("score", 0))
            away_score = int(away.get("score", 0))

            if home_score > away_score:
                line = f"*{home_name}* {home_score},  {away_name} {away_score}"
            else:
                line = f"*{away_name}* {away_score},  {home_name} {home_score}"

            is_watched = any(
                t.lower() in home_name.lower() or t.lower() in away_name.lower()
                for t in WATCHED_TEAMS
            )
            if is_watched:
                watched.append(f"🔹 {line}")
            else:
                others.append(f"     {line}")

    if not watched and not others:
        return None, "No NCAA D1 lacrosse games yesterday."

    sections = []
    if watched:
        sections.append("\n".join(watched))
    if others:
        sections.append("\n".join(others))

    return "\n\n".join(sections), None


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
        opponent = name_p.get_text(strip=True) if name_p else "Unknown"

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
    emoji = "✅" if outcome == "W" else "❌"
    type_label = f"  _{last_game['type']}_" if last_game["type"] else ""
    return (
        f"{emoji} *{outcome}* {last_game['score']}  vs {last_game['opponent']}"
        f"   _{last_game['date']}_{type_label}"
    )


def build_blocks(date_str, d1_text, csu_text):
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"NCAA D1 Lacrosse — {date_str}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": d1_text},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*CSU MCLA — Latest Result*\n{csu_text}",
            },
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

    d1_text, no_games_msg = get_d1_scores(args.date)
    d1_text = d1_text or no_games_msg
    csu_text = get_csu_mcla_result()

    blocks = build_blocks(date_str, d1_text, csu_text)

    # Print preview
    print(f"=== NCAA D1 Lacrosse — {date_str} ===\n")
    print(d1_text)
    print(f"\n--- CSU MCLA — Latest Result ---\n{csu_text}\n")

    post_to_slack(blocks, f"NCAA D1 Lacrosse — {date_str}")
