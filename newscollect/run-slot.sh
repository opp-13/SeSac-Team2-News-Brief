#!/bin/sh
set -eu

# cron이 상속 못 하는 컨테이너 런타임 환경을 여기서 다시 읽는다 (docker-entrypoint.sh 참고).
. /app/container.env

cd /app
exec python3 run_slot.py "$1"
