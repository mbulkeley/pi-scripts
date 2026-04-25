import logging
import os
from datetime import date, timedelta
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

WATCHED_TEAMS = ["Delaware", "Denver", "Air Force"]


def _make_session(
    allowed_methods: list[str],
    total: int = 3,
    backoff_factor: float = 1.0,
) -> requests.Session:
    """Build a requests Session with retry and exponential backoff.

    Args:
        allowed_methods: HTTP methods eligible for retry (e.g. ["GET"]).
        total: Maximum retry attempts.
        backoff_factor: Multiplier for exponential backoff between retries.
            Delays will be 0s, backoff_factor, 2*backoff_factor, ...

    Returns:
        Configured requests.Session.
    """
    retry = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(m.upper() for m in allowed_methods),
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Module-level sessions — reused across calls within a single run
_GET_SESSION = _make_session(["GET"])
_POST_SESSION = _make_session(["POST"], total=2, backoff_factor=0.5)


def format_scoreboard(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Render a list of game dicts as mobile-friendly Slack Block Kit blocks.

    Each game gets its own section block with a single-column layout:
        _FINAL_
        Home Team — 13
        Away Team — 2

    Watched games are marked with a 🥍 emoji.

    Args:
        games: List of dicts with keys: status, home, home_score, away,
            away_score, is_watched. Watched games should be sorted first.

    Returns:
        List of Slack Block Kit block dicts.
    """
    blocks = []
    for game in games:
        marker = "🥍 " if game["is_watched"] else ""
        text = (
            f"{marker}_{game['status']}_\n"
            f"{game['home']} — {game['home_score']}\n"
            f"{game['away']} — {game['away_score']}"
        )
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        )
    return blocks


def get_d1_scores(
    for_date: str | None = None,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Fetch completed NCAA D1 men's lacrosse scores from the ESPN API.

    Args:
        for_date: Date string in YYYYMMDD format. Defaults to yesterday.

    Returns:
        Tuple of (games, error_message). On success, games is a non-empty
        list sorted with watched teams first and error_message is None.
        On failure or no games, games is None and error_message is set.
    """
    target = for_date or (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/lacrosse"
        f"/mens-college-lacrosse/scoreboard?dates={target}"
    )

    try:
        resp = _GET_SESSION.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        logger.exception("Failed to fetch ESPN scores for %s", target)
        return None, "Could not retrieve D1 scores (ESPN API error)."

    games: list[dict[str, Any]] = []

    for event in data.get("events", []):
        for competition in event.get("competitions", []):
            status = competition.get("status", {}).get("type", {}).get("name", "")
            if status != "STATUS_FINAL":
                continue

            competitors = competition.get("competitors", [])
            home = next((c for c in competitors if c["homeAway"] == "home"), None)
            away = next((c for c in competitors if c["homeAway"] == "away"), None)
            if not home or not away:
                logger.warning("Skipping competition with missing home/away data")
                continue

            home_name = (
                home["team"].get("shortDisplayName") or home["team"]["displayName"]
            ).removesuffix(" University")
            away_name = (
                away["team"].get("shortDisplayName") or away["team"]["displayName"]
            ).removesuffix(" University")

            is_watched = any(
                t.lower() in home_name.lower() or t.lower() in away_name.lower()
                for t in WATCHED_TEAMS
            )

            games.append(
                {
                    "status": "FINAL",
                    "home": home_name,
                    "home_score": int(home.get("score", 0)),
                    "away": away_name,
                    "away_score": int(away.get("score", 0)),
                    "is_watched": is_watched,
                }
            )

    if not games:
        logger.info("No completed D1 games found for %s", target)
        return None, "No NCAA D1 lacrosse games yesterday."

    games.sort(key=lambda g: 0 if g["is_watched"] else 1)
    logger.info("Fetched %d D1 games for %s", len(games), target)
    return games, None


def get_csu_mcla_result() -> str:
    """Scrape the most recent CSU MCLA result from mcla.us.

    Returns:
        Formatted Slack mrkdwn string for the latest result, or an
        italicised error message if no result is found or the request fails.
    """
    url = "https://mcla.us/teams/colorado-state/2026"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = _GET_SESSION.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch CSU MCLA page")
        return "_Could not retrieve CSU MCLA result._"

    soup = BeautifulSoup(resp.text, "html.parser")
    tiles = soup.find_all("div", class_="game-opponent-tile")

    last_game: dict[str, str] | None = None
    for tile in tiles:
        outcome_span = tile.find("span", class_="outcome")
        if not outcome_span:
            continue

        date_div = tile.find("div", class_="game-opponent-tile__date")
        date_parts = (
            [p.get_text(strip=True) for p in date_div.find_all("p")] if date_div else []
        )

        name_p = tile.find("p", class_="opponent__name")
        score_span = tile.find("span", class_="score")
        type_div = tile.find("div", class_="game-opponent-tile__type")

        last_game = {
            "date": " ".join(date_parts),
            "opponent": (
                name_p.get_text(separator=" ", strip=True) if name_p else "Unknown"
            ),
            "outcome": outcome_span.get_text(strip=True),
            "score": score_span.get_text(strip=True) if score_span else "?",
            "type": type_div.get_text(strip=True) if type_div else "",
        }

    if not last_game:
        logger.warning("No completed CSU MCLA games found on mcla.us")
        return "_No CSU MCLA results found._"

    logger.info(
        "CSU MCLA last game: %s %s vs %s",
        last_game["outcome"],
        last_game["score"],
        last_game["opponent"],
    )
    type_label = f"  _{last_game['type']}_" if last_game["type"] else ""
    return (
        f"*{last_game['outcome']}* {last_game['score']}"
        f"  vs {last_game['opponent']}"
        f"   _{last_game['date']}_{type_label}"
    )


def build_blocks(
    date_str: str,
    d1_game_blocks: list[dict[str, Any]] | None,
    no_games_msg: str | None,
    csu_text: str,
) -> list[dict[str, Any]]:
    """Assemble the Slack Block Kit payload.

    Args:
        date_str: Human-readable date string (e.g. "April 16, 2026").
        d1_game_blocks: List of Block Kit blocks from format_scoreboard,
            or None if there are no games.
        no_games_msg: Message to display when there are no games, or None.
        csu_text: Formatted CSU MCLA result string.

    Returns:
        List of Slack Block Kit block dicts.
    """
    blocks: list[dict[str, Any]] = [
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
            "text": {
                "type": "plain_text",
                "text": f"NCAA D1 Lacrosse — {date_str}",
            },
        },
    ]

    if d1_game_blocks:
        blocks.extend(d1_game_blocks)
    else:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"_{no_games_msg}_"},
            }
        )

    return blocks


def post_to_slack(blocks: list[dict[str, Any]], fallback_text: str) -> None:
    """Post the scoreboard to the Slack webhook.

    Args:
        blocks: Slack Block Kit payload blocks.
        fallback_text: Plain-text fallback for notifications.

    Raises:
        ValueError: If SLACK_WEBHOOK_ICEMAN is not set.
        requests.HTTPError: If the Slack API returns a non-2xx response
            after retries are exhausted.
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_ICEMAN")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_ICEMAN environment variable not set")

    try:
        resp = _POST_SESSION.post(
            webhook_url,
            json={"text": fallback_text, "blocks": blocks},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Posted to Slack successfully")
    except requests.RequestException:
        logger.exception("Failed to post to Slack")
        raise


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        help="Date in YYYYMMDD format, defaults to yesterday",
    )
    args = parser.parse_args()

    if args.date:
        date_str = datetime.strptime(args.date, "%Y%m%d").strftime("%B %-d, %Y")
    else:
        date_str = (date.today() - timedelta(days=1)).strftime("%B %-d, %Y")

    try:
        d1_games, no_games_msg = get_d1_scores(args.date)
        d1_game_blocks = format_scoreboard(d1_games) if d1_games else None
        csu_text = get_csu_mcla_result()

        blocks = build_blocks(date_str, d1_game_blocks, no_games_msg, csu_text)

        logger.info("--- CSU MCLA ---\n%s", csu_text)
        logger.info("--- NCAA D1 Lacrosse: %s ---\n%s", date_str, d1_game_blocks)

        post_to_slack(blocks, f"NCAA D1 Lacrosse — {date_str}")
    except Exception:
        logger.exception("Unhandled error — script aborted")
        raise
