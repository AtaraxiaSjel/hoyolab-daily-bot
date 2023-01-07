import platform
import logging
import sys
from pathlib import Path
import subprocess
from random import randint
from datetime import datetime, timedelta
from config import Config


app_path = Path(__file__).resolve().parent
execute_target = "run.bat"


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

    target_args = [str(Path(app_path, "scheduler.py"))]

    returncode = windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(target_args), None, 1)
    success = returncode > 32

    if not success:
        logging.fatal("UAC escalation was declined. Admin privileges are needed to run the scheduler.")


def windows_scheduler():
    if platform.system() != "Windows":
        raise OSError("Windows-only scheduler attempted to run. Platform does not appear to be windows.")

    logging.info("Running Windows scheduler...")
    cur_tz_offset = datetime.now().astimezone().utcoffset()
    target_tz_offset = timedelta(hours=Config['SERVER_UTC'])
    delta = (cur_tz_offset - target_tz_offset)
    delta += timedelta(minutes=int(Config['DELAY_MINUTE']))
    if Config['RANDOMIZE']:
        delta += timedelta(seconds=randint(0, int(Config['RANDOM_RANGE'])))
    target_hour = int((24 + (delta.total_seconds()//3600)) % 24)
    target_minute = int((60 + (delta.total_seconds()//60)) % 60)
    target_seconds = int(delta.total_seconds() % 60)
    ret_code = subprocess.call((
            f'powershell',
            f'$Time = New-ScheduledTaskTrigger -Daily -At {target_hour}:{target_minute}:{target_seconds} \n',
            f'$Action = New-ScheduledTaskAction -Execute \'{str(execute_target)}\' {"" if Config["RANDOMIZE"] else "-Argument -R"} -WorkingDirectory "{str(app_path)}" \n',
            f'$Setting = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -RunOnlyIfNetworkAvailable -MultipleInstances Parallel -Priority 3 -RestartCount 30 -RestartInterval (New-TimeSpan -Minutes 1) \n',
            f'Register-ScheduledTask -Force -TaskName "{Config["SCHEDULER_NAME"]}" -Trigger $Time -Action $Action -Settings $Setting -Description "Genshin Hoyolab Daily Check-In Bot {Config.Meta.VER}" -RunLevel Highest'
        ),
        creationflags=0x08000000
    )

    if ret_code == 0:
        logging.info("Program scheduled successfully! (frequency: daily)")
        return

    request_admin_escalation()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    windows_scheduler()
    input()
