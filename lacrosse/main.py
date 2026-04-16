import os
import requests
from datetime import date, timedelta
from bs4 import BeautifulSoup


def get_d1_scores():
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/lacrosse"
        f"/mens-college-lacrosse/scoreboard?dates={yesterday}"
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    lines = []
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
                lines.append(f"*{home_name}* {home_score}, {away_name} {away_score}")
            else:
                lines.append(f"*{away_name}* {away_score}, {home_name} {home_score}")

    return "\n".join(lines) if lines else "No NCAA D1 lacrosse games yesterday."


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
        return "No CSU MCLA results found."

    type_label = f" ({last_game['type']})" if last_game["type"] else ""
    return (
        f"{last_game['date']}: Colorado State *{last_game['outcome']}* "
        f"{last_game['score']} vs {last_game['opponent']}{type_label}"
    )


def post_to_slack(message):
    webhook_url = os.environ.get("SLACK_WEBHOOK_ICEMAN")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_ICEMAN environment variable not set")

    resp = requests.post(webhook_url, json={"text": message}, timeout=10)
    resp.raise_for_status()


if __name__ == "__main__":
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%B %-d, %Y")

    d1 = get_d1_scores()
    csu = get_csu_mcla_result()

    message = (
        f"*NCAA D1 Lacrosse \u2014 {yesterday_str}*\n"
        f"{d1}\n\n"
        f"*CSU MCLA \u2014 Latest Result*\n"
        f"{csu}"
    )

    post_to_slack(message)
    print(message)
