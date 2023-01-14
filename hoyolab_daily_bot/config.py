import json
import logging
from pathlib import Path
from typing import Any, Self


class _Config:

    class Meta:
        VER = "1.3"
        UPDATE_CHANNEL = "https://github.com/Lordfirespeed/hoyolab-daily-bot/releases/latest"

    __instance: Self = None

    filepath = Path("config.json")
    _data: dict[str, Any]

    _defaults = {
        "COOKIE_BROWSER": "all",
        "COOKIE_DOMAIN_NAME": ".hoyoverse.com",
        "DELAY_MINUTE": 10,
        "RANDOM_DELAY_MINUTE": 60,
        "ACT_ID": "e202102251931481",
        "SCHEDULER_NAME": "HoyolabCheckInBot"
    }

    def __init__(self):
        if self.__initialised:
            return
        self._data = {}
        self.load_defaults()
        self.load_from_file()
        self.__initialised = True

    @staticmethod
    def __new__(cls, *args, **kwargs) -> Self:
        if not cls.__instance:
            cls.__instance = super(_Config, cls).__new__(cls, *args, **kwargs)
            cls.__instance.__initialised = False
        return cls.__instance

    def load_defaults(self):
        self._data.update(self._defaults)

    def load_from_file(self) -> None:
        if not self.filepath.is_file():
            logging.info("Couldn't find config file. Loading defaults.")
            self._data = self._defaults.copy()
            return

        with open(self.filepath) as config_file:
            new_data: dict = json.load(config_file)

        self._data.update(new_data)

    def dump_to_file(self) -> None:
        logging.debug("Dumping config...")

        with open(self.filepath, "w") as config_file:
            json.dump(self._data, config_file, indent=4)

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.dump_to_file()


Config = _Config()
