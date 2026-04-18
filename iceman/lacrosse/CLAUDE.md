# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the script

The project venv is at `/home/pi/projects/venv` and contains `requests` and `bs4`:

```bash
/home/pi/projects/venv/bin/python3 main.py
```

Test against a specific date (YYYYMMDD):

```bash
/home/pi/projects/venv/bin/python3 main.py --date 20260416
```

`SLACK_WEBHOOK_ICEMAN` must be set in the environment for the Slack post to succeed. Without it the script will raise and exit after printing the preview.

## Architecture

Single file (`main.py`). Data flows in one direction:

1. **`get_d1_scores(for_date)`** — fetches ESPN API, returns a list of game dicts `{status, home, home_score, away, away_score, is_watched}` sorted watched-first, or `(None, message)` when no games found.
2. **`format_scoreboard(games)`** — renders the game list as a monospace code block (two games per row). Watched games get a `*` prefix on their status line.
3. **`get_csu_mcla_result()`** — scrapes `mcla.us` for the CSU MCLA team's most recent completed game.
4. **`build_blocks(date_str, d1_text, csu_text)`** — assembles Slack Block Kit payload. CSU section is first, D1 scoreboard second.
5. **`post_to_slack(blocks, fallback_text)`** — posts to the webhook.

## Standards

- Type hints on all function signatures; Google-style docstrings on public functions.
- Catch specific exceptions — no bare `except:`. Cron swallows all output, so failures must be logged explicitly or they disappear silently.
- External API calls are read-only by default; any write requires an explicit comment justifying it.
- After any working feature, run a simplify pass: remove dead code, redundancy, and unnecessary complexity without changing behaviour.

## Key details

- `WATCHED_TEAMS` at the top controls which teams get highlighted and sorted first.
- Team names use `shortDisplayName` from the ESPN API (e.g. "Maryland" not "Maryland Terrapins"), with `" University"` stripped as a suffix.
- The scoreboard layout constants (`_NAME_W`, `_SCORE_W`, `_COL_W`, `_GAP`) are at the top of `format_scoreboard`'s module scope — adjust these if names overflow columns.
- The script is not currently in cron; the lacrosse season is handled manually or on demand.
