# Python 3.11 경량 이미지 사용
FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Cloud Run에서 사용할 포트
# Cloud Run이 기본으로 PORT=8080을 넘겨줌. 이 값을 그대로 사용한다.
ENV PORT=8080
EXPOSE 8080

# gunicorn으로 Flask 앱 실행
# main:app -> main.py의 app 객체
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT} main:app"]
