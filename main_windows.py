import argparse
import time
import sys
import requests
from pathlib import Path
from urllib import parse as urlparsing
import browser_cookie3
import logging
from config import Config

run_scheduler = True


def cookies_not_found():
    logging.info("Login information not found! Please login first to hoyolab once in Chrome/Firefox/Opera/Edge/Chromium before using the bot.")
    logging.info("You only need to login once for a year to https://www.hoyolab.com/genshin/ for this bot to work.")
    logging.error("LOGIN ERROR: cookies not found")
    time.sleep(5)
    sys.exit(1)


def get_cookies():
    domain_name = Config["DOMAIN_NAME"]
    selected_brower = Config["BROWSER"].lower()

    try:
        if selected_brower == "all":
            return browser_cookie3.load(domain_name=domain_name)

        if selected_brower in ("firefox", "chrome", "opera", "edge", "chromium"):
            return getattr(browser_cookie3, selected_brower)(domain_name=domain_name)

    except Exception as error:
        logging.error("Unexpected error while getting cookies:")
        logging.exception(error)

    cookies_not_found()


def check_for_token_cookie(cookies):
    token_cookies = filter(lambda cookie: cookie.name == "cookie_token", cookies)

    if not token_cookies:
        cookies_not_found()


# GET COOKIES
cookies = get_cookies()
check_for_token_cookie(cookies)

# ARGPARSE
help_text = 'Genshin Hoyolab Daily Check-In Bot\nWritten by darkGrimoire and Lordfirespeed'
parser = argparse.ArgumentParser(description=help_text)
parser.add_argument("-v", "--version",
                    help="show program version", action="store_true")
parser.add_argument("-R", "--runascron",
                    help="run program without scheduler", action="store_true")

args = parser.parse_args()
if args.version:
    logging.info(f"Bot ver. {Config.Meta.VER}")
    sys.exit(0)
if args.runascron:
    run_scheduler = False


# API FUNCTIONS
def getDailyStatus():
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://webstatic-sea.hoyoverse.com',
        'Connection': 'keep-alive',
        'Referer': f'https://webstatic-sea.hoyoverse.com/ys/event/signin-sea/index.html?act_id={Config["ACT_ID"]}&lang=en-us',
        'Cache-Control': 'max-age=0',
    }

    params = (
        ('lang', 'en-us'),
        ('act_id', Config['ACT_ID']),
    )

    try:
        response = requests.get(
            'https://hk4e-api-os.hoyoverse.com/event/sol/info',
            headers=headers,
            params=params,
            cookies=cookies
        )
    except requests.exceptions.ConnectionError as error:
        logging.error("CONNECTION ERROR: cannot get daily check-in status")
        logging.exception(error)
        raise error

    logging.debug(response)
    body = response.json()

    if body["retcode"] != 0:
        raise ValueError(f"Hoyoverse API gave non-zero returncode with explanation: '{body['message']}'")

    return body


def isClaimed():
    resp = getDailyStatus()
    return resp['data']['is_sign']


def claimReward():
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/json;charset=utf-8',
        'Origin': 'https://webstatic-sea.hoyoverse.com',
        'Connection': 'keep-alive',
        'Referer': f'https://webstatic-sea.hoyoverse.com/ys/event/signin- sea/index.html?act_id={Config["ACT_ID"]}&lang=en-us',
    }

    params = (
        ('lang', 'en-us'),
    )

    data = {'act_id': Config['ACT_ID']}

    try:
        response = requests.post(
            'https://hk4e-api-os.hoyoverse.com/event/sol/sign',
            headers=headers,
            params=params,
            cookies=cookies,
            json=data
        )
    except requests.exceptions.ConnectionError as error:
        logging.error("CONNECTION ERROR: cannot claim daily check-in reward")
        logging.exception(error)
        raise error

    logging.debug(response)
    body = response.json()

    if body["retcode"] != 0:
        raise ValueError(f"Hoyoverse API gave non-zero returncode with explanation: '{body['message']}'")

    return body


# UPDATE CHECKER
def checkUpdates():
    res = requests.get(Config.Meta.UPDATE_CHANNEL)
    newest_version = Path(urlparsing.urlparse(res.url).path).name

    if newest_version == "releases":
        return

    newest_version = newest_version[1:]

    if newest_version > Config.Meta.VER:
        logging.info(f'New version ({newest_version}) available!\nPlease go to {Config.Meta.UPDATE_CHANNEL} to download the new version.')
        time.sleep(60)


# MAIN PROGRAM
def main():
    logging.info("Starting claim loop...")

    def attempt_claim():
        logging.info("Connecting to Hoyoverse...")
        if isClaimed():
            logging.info(f'Reward already claimed.')
            return

        logging.info("Reward not claimed yet. Claiming reward...")
        resp = claimReward()
        logging.info("Reward claimed successfully.")
        logging.info(resp['message'])

    while True:
        try:
            attempt_claim()
        except requests.exceptions.ConnectionError:
            logging.info("Failed to claim, waiting before retry...")
            time.sleep(60)
            logging.info("Retrying claim...")
        except Exception as error:
            logging.error("Unknown error occurred, breaking loop:")
            logging.exception(error)
            break

        break

    checkUpdates()


if __name__ == "__main__":
    # SETUP LOGGING
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("botlog.log", "a+"),
            logging.StreamHandler()
        ]
    )

    if run_scheduler or Config["RANDOMIZE"]:
        import scheduler
        scheduler.windows_scheduler()

    main()
    time.sleep(2)
