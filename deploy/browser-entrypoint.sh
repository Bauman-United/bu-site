#!/bin/sh
set -eu
export DISPLAY="${DISPLAY:-:99}"
# Chromium после kill оставляет lock профиля — без очистки следующий старт падает.
rm -f "${BROWSER_PROFILE_DIR:-/data/browser/profile}"/Singleton*
Xvfb "$DISPLAY" -screen 0 1365x900x24 -ac +extension RANDR >/tmp/xvfb.log 2>&1 &
# Xvfb создаёт сокет асинхронно: без паузы x11vnc успевает упасть раньше дисплея.
sleep 1
x11vnc -display "$DISPLAY" -forever -shared -nopw -localhost -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &
exec uvicorn bu_worker.browser.app:app --host 0.0.0.0 --port 8090
