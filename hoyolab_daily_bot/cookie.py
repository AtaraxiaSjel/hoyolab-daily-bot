import logging
from time import sleep
import sys
import browser_cookie3
from datetime import datetime
from requests.cookies import create_cookie
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
import json

from .config import Config


class HoyoverseLoginCookieFinder:
    cookie_path = Path(".cookie")

    def __init__(self):
        self.jar = CookieJar()
        self.load()

    @staticmethod
    def hoyoverse_cookie(key: str, value: str, expiry: datetime) -> Cookie:
        return create_cookie(
            key,
            value,
            expires=int(expiry.timestamp()),
            domain=Config["COOKIE_DOMAIN_NAME"]
        )

    @staticmethod
    def necessary_cookies_not_found():
        logging.info("Login information not found! Please login first to hoyolab once in Chrome/Firefox/Opera/Edge/Chromium before using the bot.")
        logging.info("You only need to login once for a year to https://www.hoyolab.com/genshin/ for this bot to work.")
        logging.error("LOGIN ERROR: cookies not found")
        sleep(5)
        sys.exit(1)

    @staticmethod
    def get_browser_cookiejar():
        domain_name = Config["COOKIE_DOMAIN_NAME"]
        selected_brower = Config["COOKIE_BROWSER"].lower()

        try:
            if selected_brower == "all":
                return browser_cookie3.load(domain_name=domain_name)

            if selected_brower in ("firefox", "chrome", "opera", "edge", "chromium"):
                return getattr(browser_cookie3, selected_brower)(domain_name=domain_name)
        except Exception as error:
            if isinstance(error, browser_cookie3.BrowserCookieError) and error.args and type(error.args[0]) is str and error.args[0].startswith("Failed to find"):
                logging.error("Couldn't get cookies from selected browser (potentially due to execution context)")
            else:
                raise error

        raise ValueError(f"Unable to load cookies from browser '{selected_brower}'.")

    @staticmethod
    def find_cookie_of_name_in_cookiejar(cookies: CookieJar, name: str) -> Cookie:
        now_timestamp = datetime.now()
        filtered_cookies = filter(
            lambda cookie: cookie.name == name and datetime.fromtimestamp(cookie.expires) > now_timestamp,
            cookies
        )

        try:
            found_cookie = next(filtered_cookies)
        except StopIteration:
            raise ValueError(f"Couldn't find a valid required cookie '{name}'.")

        return found_cookie

    def load_cookiejar_from_browser(self) -> None:
        cookies = self.get_browser_cookiejar()
        token_cookie = self.find_cookie_of_name_in_cookiejar(cookies, "cookie_token")
        account_id_cookie = self.find_cookie_of_name_in_cookiejar(cookies, "account_id")
        self.jar.set_cookie(token_cookie)
        self.jar.set_cookie(account_id_cookie)

    def save_cookiejar_to_json(self) -> None:
        with open(self.cookie_path, "w") as save_file:
            json.dump(
                [{
                    "name": cookie.name,
                    "value": cookie.value,
                    "expires": datetime.fromtimestamp(cookie.expires).isoformat()
                } for cookie in self.jar],
                save_file,
                indent=4
            )

    def load_cookiejar_from_json(self) -> None:
        if not self.cookie_path.is_file():
            raise OSError("Token file could not be found.")

        with open(self.cookie_path) as load_file:
            data = json.load(load_file)

        for cookie_data in data:
            expiry_timestamp = datetime.fromisoformat(cookie_data["expires"])
            if expiry_timestamp <= datetime.now():
                raise ValueError("At least one saved cookie is expired.")

            new_cookie = self.hoyoverse_cookie(
                cookie_data["name"],
                cookie_data["value"],
                expiry_timestamp
            )
            self.jar.set_cookie(new_cookie)

    def load(self):
        try:
            logging.info("Loading cookies from browser cookiejar..")
            self.load_cookiejar_from_browser()
            self.save_cookiejar_to_json()
            return
        except (ValueError, browser_cookie3.BrowserCookieError) as error:
            logging.error(error)

        try:
            logging.info("Loading backup cookies from JSON...")
            self.load_cookiejar_from_json()
            return
        except OSError as error:
            logging.error(error)

        self.necessary_cookies_not_found()
