import time
import requests
from pathlib import Path
from urllib.parse import urlparse, ParseResult
import logging
from .config import Config
from typing import TypeAlias

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


class HoyoverseAPISession(requests.Session):
    api_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://webstatic-sea.hoyoverse.com',
        'Connection': 'keep-alive',
        'Referer': 'https://webstatic-sea.hoyoverse.com/ys/event/signin-sea/index.html?act_id={act_id}&lang=en-us',
        'Cache-Control': 'max-age=0',
    }

    api_root: ParseResult = urlparse("https://hk4e-api-os.hoyoverse.com/")

    def __init__(self):
        super(HoyoverseAPISession, self).__init__()
        formatted_headers = self.format_headers(HoyoverseAPISession.api_headers)
        self.headers.update(formatted_headers)

    @staticmethod
    def format_headers(headers: dict[str, str]) -> dict[str, str]:
        formatted_headers = {}
        for key, value in headers:
            formatted_headers[key] = value.format(
                act_id=Config["ACT_ID"]
            )
        return formatted_headers

    def api_request(self, method, path, *args, **kwargs) -> JSON:
        target = self.api_root._replace(path=path).geturl()
        try:
            response = self.request(method, target, *args, **kwargs)
        except requests.exceptions.ConnectionError as error:
            logging.error("CONNECTION ERROR: cannot get daily check-in status")
            logging.exception(error)
            raise error

        body = response.json()

        logging.debug("API response: ")
        logging.debug(body)

        if body["retcode"] != 0:
            raise ValueError(f"Hoyoverse API gave non-zero returncode with explanation: '{body['message']}'")

        return body

    def api_get(self, path, *args, **kwargs) -> JSON:
        kwargs.setdefault("allow_redirects", True)
        return self.api_request("GET", path, *args, **kwargs)

    def api_post(self, path, *args, **kwargs) -> JSON:
        return self.api_request("POST", path, *args, **kwargs)

    def get_daily_claim_status(self) -> JSON:
        return self.api_get(
            "event/sol/info",
            params={
                "lang": "en-us",
                "act_id": Config["ACT_ID"]
            }
        )

    def post_daily_claim(self):
        return self.api_post(
            "event/sol/sign",
            params={
                "lang": "en-us"
            },
            json={
                "act_id": Config["ACT_ID"]
            }
        )


class DailyClaimBot:
    max_retries = 10

    def __init__(self) -> None:
        self.session = HoyoverseAPISession()

    def already_claimed_today(self):
        resp = self.session.get_daily_claim_status()
        return resp['data']['is_sign']

    @staticmethod
    def check_for_package_updates():
        res = requests.get(Config.Meta.UPDATE_CHANNEL)
        newest_version = Path(urlparse(res.url).path).name

        if newest_version == "releases":
            return

        newest_version = newest_version[1:]

        if newest_version > Config.Meta.VER:
            logging.info(f'New version ({newest_version}) available!\nPlease go to {Config.Meta.UPDATE_CHANNEL} to download the new version.')

    def attempt_claim(self):
        logging.info("Connecting to Hoyoverse...")
        if self.already_claimed_today():
            logging.info(f'Reward already claimed.')
            return

        logging.info("Reward not claimed yet. Claiming reward...")
        resp = self.session.post_daily_claim()
        logging.info("Reward claimed successfully.")
        logging.info(resp['message'])

    def main(self):
        logging.info("Starting claim loop...")
        for _ in range(self.max_retries):
            try:
                self.attempt_claim()
                break
            except requests.exceptions.ConnectionError:
                logging.info("Failed to claim, waiting before retry...")
                time.sleep(60)
                logging.info("Retrying claim...")
            except Exception as error:
                logging.error("Unexpected error occurred, breaking loop:")
                logging.exception(error)
                break

        self.check_for_package_updates()


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

    bot = DailyClaimBot()
    bot.main()
    time.sleep(2)
