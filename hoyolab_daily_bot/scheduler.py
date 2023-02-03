import platform
import logging
import sys
from pathlib import Path
import subprocess
from crontab import CronTab, CronItem
from datetime import time, date, datetime, timedelta
from zoneinfo import ZoneInfo
from abc import ABC, abstractmethod
from typing import Generator

from .config import Config


class SchedulerAbc(ABC):
    app_path = Path(__file__).resolve().parent.parent
    asia_tz = ZoneInfo("Etc/GMT-8")
    reset_time_in_local_tz = datetime.combine(date.today(), time(hour=0, tzinfo=asia_tz)).astimezone()

    def __init__(self):
        if not self.platform_compatible():
            raise OSError(f"This class can only be instantiated on '{self.for_platform}' systems.")

    @property
    def target_time(self) -> time:
        return (self.reset_time_in_local_tz + timedelta(minutes=Config["DELAY_MINUTE"])).time()

    @classmethod
    def platform_compatible(cls) -> bool:
        return platform.system() in cls.compatible_with

    @classmethod
    @property
    @abstractmethod
    def for_platform(cls) -> str: ...

    @classmethod
    @property
    @abstractmethod
    def compatible_with(cls) -> [str]: ...

    @abstractmethod
    def run(self) -> None: ...


class WindowsScheduler(SchedulerAbc):
    for_platform = "Windows"
    compatible_with = ("Windows",)

    @staticmethod
    def request_admin_escalation() -> None:
        if platform.system() != "Windows":
            return

        # https://stackoverflow.com/a/72732324/11045433 BaiJiFeiLong
        from ctypes import windll
        if windll.shell32.IsUserAnAdmin():
            return

        if sys.argv[0].endswith("exe"):
            logging.fatal("This script has not been tested built as an executable. It should be distributed as python source code.")
            return

        target_args = ["-m hoyolab_daily_bot.scheduler"]

        returncode = windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(target_args), None, 1)
        success = returncode > 32

        if not success:
            logging.fatal("UAC escalation was declined. Admin privileges are needed to run the scheduler.")

        sys.exit()

    @staticmethod
    def format_params(params: [str]) -> str:
        return " ".join("-" + param for param in params)

    def run(self) -> None:
        logging.info(f"Running {self.for_platform} scheduler...")

        trigger_params = [
            "Daily",
            f"RandomDelay (New-TimeSpan -Minutes {Config['RANDOM_DELAY_MINUTE']})",
            f"At {self.target_time.isoformat()}"
        ]

        action_params = [
            "Execute 'run.bat'",
            f"WorkingDirectory '{str(self.app_path)}'"
        ]

        settings_params = [
            "StartWhenAvailable",
            "AllowStartIfOnBatteries",
            "DontStopIfGoingOnBatteries",
            "WakeToRun",
            "RunOnlyIfNetworkAvailable",
            "MultipleInstances Parallel",
            "Priority 3",
            "RestartCount 30",
            "RestartInterval (New-TimeSpan -Minutes 1)"
        ]

        task_params = [
            f"TaskName '{Config['SCHEDULER_NAME']}'",
            "Trigger $Time",
            "Action $Action",
            "Settings $Settings",
            "Principal $Principal",
            f"Description 'Genshin Hoyolab Daily Check-In Bot {Config.Meta.VER}'"
        ]

        result = subprocess.run((
                f"powershell",
                f"$Time = New-ScheduledTaskTrigger {self.format_params(trigger_params)} \n",
                f"$Action = New-ScheduledTaskAction {self.format_params(action_params)} \n",
                f"$Settings = New-ScheduledTaskSettingsSet {self.format_params(settings_params)} \n",
                f"$Principal = New-ScheduledTaskPrincipal -UserID 'NT AUTHORITY\\SYSTEM' -LogonType ServiceAccount -RunLevel Highest \n",
                f"Register-ScheduledTask {self.format_params(task_params)}"
            ),
            creationflags=0x08000000,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if result.returncode == 0:
            logging.info("Program scheduled successfully! (frequency: daily)")
            return

        self.request_admin_escalation()

        logging.fatal("Scheduler failed.")
        logging.fatal(result.stderr)


class UnixScheduler(SchedulerAbc):
    for_platform = "Unix"
    compatible_with = ("Darwin", "Linux")

    def __init__(self):
        super(UnixScheduler, self).__init__()
        self.cron = self.get_user_crontab()

    @staticmethod
    def get_user_crontab() -> CronTab:
        return CronTab(user=True)

    def find_existing_jobs(self) -> Generator[CronItem]:
        return self.cron.find_comment(Config["SCHEDULER_NAME"])

    def remove_existing_jobs(self) -> None:
        logging.info("Removing existing hoyolab-daily-bot jobs...")
        self.cron.remove_all(comment=Config["SCHEDULER_NAME"])

    def create_new_job(self) -> None:
        logging.info("Creating new hoyolab-daily-bot job...")
        job = self.cron.new(
            command=f"SLEEP $[($RANDOM % ({Config['RANDOM_DELAY_MINUTE']} * 60))]; cd {str(self.app_path)}; source venv/bin/activate; python -m hoyolab_daily_bot.claim",
            comment=Config["SCHEDULER_NAME"]
        )

        job.day.every()
        job.minute.on(self.target_time.minute)
        job.hour.on(self.target_time.hour)

    def write_back(self) -> None:
        logging.info("Writing back to user crontab...")
        self.cron.write()

    def run(self) -> None:
        logging.info(f"Running {self.for_platform} scheduler...")
        try:
            next(self.find_existing_jobs())
            self.remove_existing_jobs()
        except StopIteration:
            pass

        self.create_new_job()
        self.write_back()
        logging.info("Program scheduled successfully! (frequency: daily)")


schedulers = [WindowsScheduler, UnixScheduler]


def run_platform_scheduler():
    compatible = filter(lambda scheduler_class: scheduler_class.platform_compatible(), schedulers)

    try:
        selected_scheduler_class = next(compatible)
    except StopIteration:
        raise NotImplementedError("Couldn't find a suitable scheduler for your platform.")

    scheduler = selected_scheduler_class()
    scheduler.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_platform_scheduler()
    input()
