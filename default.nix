{
  lib,
  python3Packages,
  version ? "git",
}:
with python3Packages; buildPythonApplication {
  pname = "hoyolab-daily-bot";
  inherit version;

  src = lib.cleanSource ./.;

  nativeBuildInputs = [
    setuptools
  ];

  propagatedBuildInputs = [
    requests
    browser-cookie3
    tzdata
    typing-extensions
    # dbus-python #FIXME: browser-cookie3 expect kdewallet (dbus)
  ];

  meta = with lib; {
    homepage = "https://github.com/AtaraxiaSjel/hoyolab-daily-bot";
    description = "Hoyolab Daily Check-in Bot.";
    license = licenses.mit;
    platforms = platforms.linux;
  };
}