def lacrosse_scores(division):
    import requests as req
    from datetime import date
    from bs4 import BeautifulSoup
    from datetime import timedelta

    yesterday = (date.today() - timedelta(days=1)).strftime("%Y/%m/%d")
    # yesterday = "2021/04/03"
    header = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/89.0.4389.90 Safari/537.36",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
    }
    url = f"https://www.ncaa.com/scoreboard/lacrosse-men/{division}/{yesterday}/all-conf"

    resp = req.get(url, headers=header)
    soup = BeautifulSoup(resp.text, "lxml")
    games = soup.find_all(class_=["gamePod-status", "gamePod-game-team-name", "gamePod-game-team-score"])

    if division == 'd1':
        scores = '*** Division I ***'
        division = 'Division I'
    else:
        scores = '*** Division III ***'
        division = 'Division III'

    if len(games) > 0:
        index = 0
        while index < len(games):
            if index == 0:
                scores += '\n'
            else:
                scores += '\n\n'
            scores += f"{games[index].text.rjust(25)}\n{games[index + 1].text}" \
                      f"{games[index + 2].text.rjust(25 - len(games[index + 1].text))}\n" \
                      f"{games[index + 3].text}{games[index + 4].text.rjust(25 - len(games[index + 3].text))}"
            index += 5
    else:
        scores = f"No NCAA {division} Lacrosse games yesterday."
    return scores


def post_to_flowdock(message, about):
    import os
    import json
    import requests
    from requests.auth import HTTPBasicAuth

    flowdock_api_key = os.environ.get('FLOWDOCK_API_KEY')
    flowdock_org = os.environ.get('FLOWDOCK_ORG')
    flowdock_flow = os.environ.get('FLOWDOCK_FLOW')
    url = f'https://api.flowdock.com/flows/{flowdock_org}/{flowdock_flow}/messages'
    flowdock_message = message
    payload = {'content': flowdock_message, 'event': 'message'}
    headers = {'X-flowdock-wait-for-message': 'true', 'content-type': 'application/json'}

    try:
        session = requests.Session()
        response = session.post(url, data=json.dumps(payload), headers=headers,
                                auth=HTTPBasicAuth(flowdock_api_key, 'DUMMY'))
        session.close()
    except requests.exceptions.HTTPError as e:
        print(f'An HTTPError occurred posting to Flowdock: {e}')
        print.error('*** ERROR ***')
        session.close()
    except requests.RequestException as e:
        print.error(f'A general error occurred posting to Flowdock: {e}')
        print.error('*** ERROR ***')
        session.close()


if __name__ == '__main__':
    # Get Division I & Division III scores
    division_1 = lacrosse_scores('d1')
    division_3 = lacrosse_scores('d3')
    # Concatenate the scores
    yesterdays_scores = division_1 + '\n\n' + division_3
    # Post the scores to Flowdock
    post_to_flowdock(f"Yesterday's Lacrosse Scores\n```\n{yesterdays_scores}\n```", "NCAA Lacrosse Scores")


