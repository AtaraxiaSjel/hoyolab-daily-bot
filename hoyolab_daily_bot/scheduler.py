import platform
import logging
import sys
from pathlib import Path
import subprocess
from datetime import time, date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import Config

app_path = Path(__file__).resolve().parent.parent

asia_tz = ZoneInfo("Etc/GMT-8")
reset_time_in_local_tz = datetime.combine(date.today(), time(hour=0, tzinfo=asia_tz)).astimezone()


# SCHEDULER CONFIGURATION
def request_admin_escalation():
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


def windows_scheduler():
    if platform.system() != "Windows":
        raise OSError("Windows-only scheduler attempted to run. Platform does not appear to be windows.")

    logging.info("Running Windows scheduler...")

    target_time = (reset_time_in_local_tz + timedelta(minutes=Config["DELAY_MINUTE"])).time()

    def format_params(params: [str]) -> str:
        return " ".join("-" + param for param in params)

    trigger_params = [
        "Daily",
        f"RandomDelay (New-TimeSpan -Minutes {Config['RANDOM_DELAY_MINUTE']})",
        f"At {target_time.isoformat()}"
    ]

    action_params = [
        "Execute 'run.bat'",
        f"WorkingDirectory '{str(app_path)}'"
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
            f"$Time = New-ScheduledTaskTrigger {format_params(trigger_params)} \n",
            f"$Action = New-ScheduledTaskAction {format_params(action_params)} \n",
            f"$Settings = New-ScheduledTaskSettingsSet {format_params(settings_params)} \n",
            f"$Principal = New-ScheduledTaskPrincipal -UserID 'NT AUTHORITY\\SYSTEM' -LogonType ServiceAccount -RunLevel Highest \n",
            f"Register-ScheduledTask {format_params(task_params)}"
        ),
        creationflags=0x08000000,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode == 0:
        logging.info("Program scheduled successfully! (frequency: daily)")
        return

    request_admin_escalation()

    logging.fatal("Scheduler failed.")
    logging.fatal(result.stderr)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    windows_scheduler()
    input()
