import argparse
import logging

from .claim import DailyClaimBot
from .cookie import HoyoverseLoginCookieFinder

def main():
    help_text = 'Hoyolab Daily Check-In Bot'
    parser = argparse.ArgumentParser(description=help_text)
    parser.add_argument("-c", "--cookie", help="path to cookie")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    finder = HoyoverseLoginCookieFinder()
    if args.cookie is not None:
        finder.set_cookie_path(args.cookie)
    finder.load()

    bot = DailyClaimBot()
    bot.main()

if __name__ == "__main__":
    main()