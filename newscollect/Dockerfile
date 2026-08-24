FROM python:3.11-slim

# 컨테이너 TZ를 고정해야 crontab의 "0 7,12,17 * * *"가 KST 07/12/17과 맞아떨어진다
# (CLAUDE.md의 배치 슬롯은 KST 기준).
ENV TZ=Asia/Seoul
RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY naver_news naver_news
COPY freenews freenews
COPY providers providers
COPY details details
COPY processing processing
COPY main.py run_slot.py ./

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir ".[deploy]"

COPY run-slot.sh docker-entrypoint.sh ./
RUN chmod +x run-slot.sh docker-entrypoint.sh

COPY crontab /etc/cron.d/newscollect
RUN chmod 0644 /etc/cron.d/newscollect && crontab /etc/cron.d/newscollect

CMD ["./docker-entrypoint.sh"]
