#!/bin/sh
set -eu

# cron은 `docker run -e`로 넘긴 컨테이너 런타임 환경변수를 상속하지 않는다 (컨테이너+cron
# 조합에서 흔히 걸리는 함정). 컨테이너가 뜬 시점의 환경을 파일로 한 번 떠 두고,
# run-slot.sh가 매 실행마다 이 파일을 source한다.
printenv | grep -v '^HOSTNAME=' | sed 's/^\(.*\)$/export \1/' > /app/container.env
chmod 600 /app/container.env

# cron 작업의 stdout/stderr가 `docker logs`에 보이게 PID 1로 리다이렉트한다.
exec cron -f
