# Python 3.11 경량 이미지 사용
FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

ENV PORT=8080
EXPOSE 8080

# main:app -> main.py의 app 객체
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT} main:app"]
