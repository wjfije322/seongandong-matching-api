FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run이 PORT를 제공하므로 기본값만 설정해 둔다.
ENV PORT=8080
EXPOSE 8080

# entrypoint 스크립트 사용
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT} main:app"]
