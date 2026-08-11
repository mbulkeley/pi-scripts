# -*- coding: utf-8 -*-
#!/usr/bin/env python3
###############
# DailyBot v3.1
# Updated 2026-04-16 — removed dead code (Twilio, ActiveCampaign), cleaned up structure
#                      switched from Slack token to webhook
#
# v3.0 — 2026-04-14 — replaced AccuWeather with Open-Meteo (free, no key required)
#                      replaced USNO API for moon phase (free, no key required)
# v2.0.1 — 2023-04-24 — corrected Martha's Birthday
# v2.0 — 2022-07-15 — migrated from Flowdock to Slack
# v1.9 — 2022-01-23 — added ActiveCampaign new contact count
###############

import datetime
from datetime import date, timedelta
import dateutil.parser
import holidays
import logging
import os
import pandas as pd
import requests


def get_on_this_day(logger):
    logger.debug(f'Retrieving the event for today: {date.today().strftime("%m/%d")}')
    the_event = "Unable to get today's event from Wikipedia."
    url = f'https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{date.today().strftime("%m/%d")}'
    headers = {
        'User-Agent': 'DailyBot/3.1 (https://github.com/michaelbulkeley; michaelbulkeley@yahoo.com)',
        'accept': 'application/json; charset=utf-8;',
        'accept-encoding': 'gzip,deflate'
    }
    session = requests.Session()
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        the_event = f"An error occurred. Unable to get today's event from Wikipedia:\n{e}"
    except requests.RequestException as e:
        the_event = f"An error occurred. Unable to get today's event from Wikipedia:\n{e}"
    else:
        parsed_json = response.json()
        events_df = pd.DataFrame(parsed_json['events'])
        events_df = events_df[['year', 'text', 'pages']]
        do_not_include = ['killing', 'killed', 'kills', 'murdered', 'murdering', 'dismembered', 'massacre',
                          'deaths', 'die', 'slaughters', 'dead']
        my_lifetime_events_df = events_df[(events_df.year >= 1968)]
        happier_events_df = \
            my_lifetime_events_df[~my_lifetime_events_df['text'].str.contains('|'.join(do_not_include)) == True]
        event_df = happier_events_df.sample(replace=False)
        the_event = \
            f"<{event_df.pages.values[0][0]['content_urls']['desktop']['page']}|On this day in " \
            f"{event_df.year.values[0]}:> " \
            f"{event_df.text.values[0]}"
    finally:
        session.close()
        return the_event


def get_holiday(the_date, logger):
    # NOTE: Adding a holiday/birthday requires updates in TWO places:
    #   1. message_list below — the display string keyed by holiday name
    #   2. holiday_list.append() further down — the date-to-name mapping
    # NOTE: Do NOT set holiday_list.observed after append() — it clears the cache and wipes custom entries.
    #       observed=False is set at construction time instead.
    message_list = {
        'None': 'Today is not a holiday.',
        "New Year's Day, Nieuwjaarsdag": "Happy New Year! :fireworks:",
        'Martin Luther King Jr. Day': 'Today is Martin Luther King Jr. Day',
        "Dad's Birthday": "Today is dad's birthday!",
        "Washington's Birthday": "Happy President's Day!",
        'Goede Vrijdag': "Isn't Friday always good?",
        'Eerste paasdag': 'Happy Easter! :hatched_chick:',
        'Tweede paasdag': 'Another Easter Day...',
        'Koningsdag': "King's Day! Put on the orange! :beer::beers::tropical_drink:",
        'Hemelvaart': 'No idea what Hemelvaart is...',
        'Eerste Pinksterdag': 'Today is Eerste Pinksterdag',
        'Tweede Pinksterdag': 'Today is Tweede Pinksterdag',
        'Memorial Day': 'Memorial Day! Fire up the BBQ!',
        'Your Birthday': 'Happy Birthday to you! :beers:',
        'Independence Day': 'Happy Fourth of July! :fireworks:',
        'Independence Day (Observed)': 'Observed, pffft.',
        'Labor Day': 'Labor Day! Fire up the BBQ!',
        'Columbus Day': 'In 1492 Columbus sailed the ocean blue.',
        'Veterans Day': 'Today is Veterans Day.',
        'Your Anniversary': 'Today is your wedding anniversary! (2020)',
        'Halloween': 'Happy Halloween! :jack_o_lantern::ghost:',
        'Thanksgiving': 'Happy Thanksgiving! :wine_glass::sushi::wink:',
        "Sinterklaas": "Happy Sinterklaas! Who's that knocking on the door?",
        "Andrew's Birthday": "Today is your brother's birthday! (1969)",
        "Edie's Birthday": "Today is Edie's birthday!",
        "Cy's Birthday": "Today is Cy's birthday! (2004)",
        "Martha's Birthday": "Today is Martha's birthday! (2003)",
        "Joost's Birthday": "Today is Joost's birthday!",
        "Michelle's Birthday": "Today is Michelle's birthday!",
        "Lucas & Sabine's Birthday": "Today is Lucas & Sabine's birthday! :birthday:",
        "Sabine's Birthday": "Today is Sabine's birthday! (1971)",
        'Winter Solstice': 'Winter Solstice. Longer days ahead!',
        "Laurie's Birthday": "Today is your wife's birthday! (1979)",
        'Christmas Day(Observed)': 'Observed, pffft...',
        'Christmas Day, Eerste Kerstdag': 'Merry Christmas! :santa::christmas_tree::cocktail:',
        'Tweede Kerstdag': 'Today is Tweede Kerstdag.',
        "New Year's Day(Observed)": "Observed, pffft..."
    }
    holiday_message = message_list.get('None')

    holiday_list = holidays.US(observed=False) + holidays.NL(observed=False)
    holiday_list.append({f'{the_date.year}-02-04': "Dad's Birthday",
                         f'{the_date.year}-04-29': "Martha's Birthday",
                         f'{the_date.year}-06-04': 'Your Birthday',
                         f'{the_date.year}-08-02': "Joost's Birthday",
                         f'{the_date.year}-08-09': "Michelle's Birthday",
                         f'{the_date.year}-08-11': "Lucas & Sabine's Birthday",
                         f'{the_date.year}-08-14': "Cy's Birthday",
                         f'{the_date.year}-10-20': 'Your Anniversary',
                         f'{the_date.year}-10-31': 'Halloween',
                         f'{the_date.year}-12-05': 'Sinterklaas',
                         f'{the_date.year}-12-12': "Andrew's Birthday",
                         f'{the_date.year}-12-18': "Edie's Birthday",
                         f'{the_date.year}-12-21': 'Winter Solstice',
                         f'{the_date.year}-12-24': "Laurie's Birthday"
                         })

    logger.debug(holiday_list.get(the_date))
    if the_date in holiday_list:
        holiday_message = message_list.get(holiday_list.get(the_date))

    return holiday_message


def get_approximate_moon_phase(today):
    known_new_moon = date(2024, 1, 11)
    lunar_cycle = 29.53058867
    days_since = (today - known_new_moon).days
    position = days_since % lunar_cycle

    if position < 1.85:
        return 'New Moon'
    elif position < 7.38:
        return 'Waxing Crescent'
    elif position < 9.22:
        return 'First Quarter'
    elif position < 14.77:
        return 'Waxing Gibbous'
    elif position < 16.61:
        return 'Full Moon'
    elif position < 22.15:
        return 'Waning Gibbous'
    elif position < 23.99:
        return 'Last Quarter'
    elif position < 29.53:
        return 'Waning Crescent'
    else:
        return 'New Moon'


def degrees_to_compass(degrees):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(degrees / 45) % 8
    return directions[index]


def get_weather(logger):
    degree = u'°'
    weather_array = ["Unable to get weather for today."]
    session = requests.Session()

    wmo_codes = {
        0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
        45: 'Foggy', 48: 'Icy fog',
        51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
        61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
        71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
        80: 'Slight showers', 81: 'Moderate showers', 82: 'Violent showers',
        85: 'Slight snow showers', 86: 'Heavy snow showers',
        95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Thunderstorm with heavy hail'
    }

    try:
        url = (
            'https://api.open-meteo.com/v1/forecast'
            '?latitude=52.37&longitude=4.89'
            '&current=temperature_2m,weathercode'
            '&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,weathercode,'
            'wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant'
            '&hourly=wind_gusts_10m'
            '&timezone=Europe%2FAmsterdam'
        )
        response = session.get(url)
        logger.debug(f'Status Code from Open-Meteo: {response.status_code}')
        response.raise_for_status()
        parsed_json = response.json()

        curr_temp = parsed_json['current']['temperature_2m']
        forecast_high = parsed_json['daily']['temperature_2m_max'][0]
        forecast_low = parsed_json['daily']['temperature_2m_min'][0]
        weather_code = parsed_json['daily']['weathercode'][0]
        forecast_text = wmo_codes.get(weather_code, f'Weather code {weather_code}')

        sun_rise_raw = parsed_json['daily']['sunrise'][0]
        sun_set_raw = parsed_json['daily']['sunset'][0]
        sun_rise = sun_rise_raw[11:16]
        sun_set = sun_set_raw[11:16]

        rise_dt = dateutil.parser.parse(sun_rise_raw)
        set_dt = dateutil.parser.parse(sun_set_raw)
        day_length = str(set_dt - rise_dt)
        day_length = day_length[0:5] if len(day_length) == 8 else day_length[0:4]

        moon_phase = "Unknown"
        try:
            today = date.today()
            usno_url = (
                f'https://aa.usno.navy.mil/api/moon/phases/date'
                f'?date={today.strftime("%Y-%m-%d")}&nump=1'
            )
            moon_response = session.get(usno_url, timeout=10)
            moon_response.raise_for_status()
            moon_json = moon_response.json()
            logger.debug(f'USNO moon response: {moon_json}')

            phases = moon_json.get('phasedata', [])
            if phases:
                next_phase = phases[0]
                phase_date = datetime.datetime.strptime(
                    f"{next_phase['year']}-{next_phase['month']:02d}-{next_phase['day']:02d}",
                    "%Y-%m-%d"
                ).date()
                moon_phase = next_phase['phase'] if phase_date == today else get_approximate_moon_phase(today)
            else:
                moon_phase = get_approximate_moon_phase(today)
        except Exception as e:
            logger.error(f'Error getting moon phase: {e}')
            moon_phase = get_approximate_moon_phase(today)

        wind_speed_max = parsed_json['daily']['wind_speed_10m_max'][0]
        wind_gusts_max = parsed_json['daily']['wind_gusts_10m_max'][0]
        wind_dir_deg = parsed_json['daily']['wind_direction_10m_dominant'][0]
        wind_dir = degrees_to_compass(wind_dir_deg)

        hourly_gusts = parsed_json['hourly']['wind_gusts_10m'][:24]
        peak_gust_hour = hourly_gusts.index(max(hourly_gusts))
        wind_line = (
            f'Wind: {wind_dir} {wind_speed_max} km/h max '
            f'(gusts up to {wind_gusts_max} km/h, worst around {peak_gust_hour:02d}:00)'
        )

        weather_post = (
            f'It is: {curr_temp}{degree}C\n'
            f'Low: {forecast_low}{degree}C / High: {forecast_high}{degree}C\n'
            f'Forecast: {forecast_text}\n'
            f'{wind_line}\n\n'
            f'Sunrise: {sun_rise} / Sunset: {sun_set}\n'
            f'Day length: {day_length}\n\n'
            f'Moon Phase: {moon_phase}'
        )

        weather_array = [weather_post]

    except requests.exceptions.HTTPError as e:
        logger.error(f'An HTTPError occurred getting weather: {e}')
    except requests.RequestException as e:
        logger.error(f'A general error occurred getting weather: {e}')
    finally:
        session.close()
        return weather_array


def post_to_slack(message, about, logger):
    logger.info('Posting to personal Slack')
    webhook_url = os.environ.get('SLACK_WEBHOOK_ICEMAN')

    session = requests.Session()
    try:
        response = session.post(webhook_url, json={'text': message})
        response.raise_for_status()
        logger.debug(f'Posted {about} to Slack: {response.status_code}')
    except requests.exceptions.HTTPError as e:
        logger.error(f'An HTTPError occurred posting to Slack: {e}')
    except requests.RequestException as e:
        logger.error(f'A general error occurred posting to Slack: {e}')
    finally:
        session.close()


def post_to_slack_work(message, about, logger):
    logger.info('Posting to work Slack')
    webhook_url = os.environ.get('SLACK_WEBHOOK_WORK')

    session = requests.Session()
    try:
        response = session.post(webhook_url, json={'text': message})
        response.raise_for_status()
        logger.debug(f'Posted {about} to work Slack: {response.status_code}')
    except requests.exceptions.HTTPError as e:
        logger.error(f'An HTTPError occurred posting to work Slack: {e}')
    except requests.RequestException as e:
        logger.error(f'A general error occurred posting to work Slack: {e}')
    finally:
        session.close()


def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("/home/pi/projects/iceman/logs/slackbot.log")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info('*** STARTING ***')

    current_time = datetime.datetime.now()
    if current_time.hour < 12:
        logger.info('Good morning! Gathering information.')
    elif 12 <= current_time.hour < 18:
        logger.info('Good afternoon! Gathering information.')
    else:
        logger.info('Good evening! Gathering information.')

    weather_info = get_weather(logger)
    daily_update = f"{weather_info[0]}\n\n"

    on_this_day = get_on_this_day(logger)
    daily_update += f"{on_this_day}\n\n"

    holiday = get_holiday(current_time.date(), logger)
    daily_update += f"{holiday}\n\n"

    daily_update += "https://www.gocomics.com/calvinandhobbes"

    logger.debug(daily_update)
    post_to_slack(daily_update, "Daily Update", logger)
    post_to_slack_work(daily_update, "Daily Update", logger)
    logger.info('*** DONE ***')


if __name__ == '__main__':
    main()
