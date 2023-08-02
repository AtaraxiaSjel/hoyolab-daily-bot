# Honkai: Star Rail Hoyolab Daily Check-in Bot 📜🖋
Honkai: Star Rail Hoyolab Daily Check-in Bot is here!

# Prerequisites 🎯
- Login to mihoyo's website at any browser (A login for a year is enough)

# How to use ✨
TBA

# Configuration File
- **COOKIE_BROWSER**: You can target specific browser to be used for login. Please beware that this program doesn't support account chooser yet, so if you have multiple account you may use a browser you rarely use that only contains 1 account information.
Currently supported browsers are: `firefox`, `chrome`, `chromium`, `opera`, and `edge`. The default is `all`.
- **DELAY_MINUTE**: Sometimes, your PC is some minutes earlier than the server time. If you're experiencing reward already claimed whenever the bot started, please add some delay.
- **ACT_ID** and **COOKIE_DOMAIN_NAME** shouldn't need changing. They are present for futureproofing.

# How to update 📈
TBA

# Development Setup
1. `git clone` the repository.
2. `cd hoyolab-daily-bot`
3. Setup Python 3 virtualenv
   ```
   pip install virtualenv
   python -m venv venv
   .\venv\Scripts\activate.bat
   ```
2. Install dependencies
   ```
   pip install -r requirements.txt
   ```
3. Run `python -m hoyolab_daily_bot.claim` to claim today's rewards only.
