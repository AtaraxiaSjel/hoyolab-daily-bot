import platform
import logging
import sys
from pathlib import Path
import subprocess
from random import randint
from datetime import datetime, timedelta
from config import Config

# INITIALIZE PROGRAM ENVIRONMENT
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # if running a frozen executable, that is the execute target
    execute_target = Path(sys.executable)
    app_path = Path(sys.executable).parent
else:
    # if running python source, that is the execute target
    app_path = Path(__file__).resolve().parent
    execute_target = "run.bat"


# SCHEDULER CONFIGURATION
def request_admin_escalation_or_exit():
    if platform.system() != "Windows":
        return

    # https://stackoverflow.com/a/72732324/11045433 BaiJiFeiLong
    from ctypes import windll
    if windll.shell32.IsUserAnAdmin():
        return

    if sys.argv[0].endswith("exe"):
        logging.fatal("This script is not intended to be built as a portable executable. It should be distributed as python source code.")
        sys.exit()

    returncode = windll.shell32.ShellExecuteW(None, "runas", sys.executable, "-m catdv_resolve " + " ".join(sys.argv[1:]) + " --uac_escalated", None, 1)
    success = returncode > 32

    if not success:
        logging.fatal("UAC escalation was declined. Admin privileges are needed to install globally.")

    sys.exit()


def configScheduler():
    logging.info("Running scheduler...")
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

    logging.error("PERMISSION ERROR: please run as administrator to enable task scheduling")
    input()
    sys.exit(1)
