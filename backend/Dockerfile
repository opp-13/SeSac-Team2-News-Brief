# 백엔드 API 이미지. docker-compose.yml의 api 서비스가 쓴다.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 의존성만 먼저 복사해 레이어 캐시를 살린다 — 소스가 바뀔 때마다 재설치하지 않는다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# --reload는 개발용이라 이미지에 넣지 않는다. compose에서 필요하면 command로 덮어쓴다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
