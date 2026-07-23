import os
import json
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("환경 변수 GOOGLE_API_KEY가 설정되어 있지 않습니다.")

genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-1.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

SYSTEM_INSTRUCTION = """
당신은 성안동 도시재생 사업을 위한 빈집·빈상가 매칭 서비스의 백엔드 AI 어시스턴트입니다.

역할:
- 사용자가 자연어로 작성한 공간 요구 텍스트를 분석해서,
  업종, 키워드, 요구조건을 구조화된 JSON으로 반환합니다.
- 분석 결과를 바탕으로, 추천될 수 있는 공간 유형과 그 이유를 한국어 문장으로 설명합니다.

주의사항:
- 항상 아래 JSON 스키마를 정확히 따르십시오.
- JSON 외에 불필요한 설명이나 텍스트를 JSON 바깥에 추가하지 마십시오.
- 출력은 한국어 기반이지만, JSON의 key는 영문으로 유지하십시오.

JSON 스키마:
{
  "business_type": string,
  "keywords": [string],
  "constraints": [string],
  "preferred_location_tags": [string],
  "budget": {
    "type": string,
    "max_amount": number|null
  },
  "space_size": {
    "min_area": number|null,
    "max_area": number|null
  }
}
"""

def parse_requirements(user_text: str) -> dict:
    prompt = f"""
다음은 성안동 빈집·빈상가 매칭 서비스에서 사용자가 입력한 요구 텍스트입니다.

해야 할 일:
1. 입력 텍스트를 분석해서 위 JSON 스키마를 따르는 JSON만 출력하십시오.
2. JSON 이외의 추가 텍스트는 출력하지 마십시오.

사용자 요구 텍스트:
\"\"\"{user_text}\"\"\"
"""
    response = model.generate_content(SYSTEM_INSTRUCTION + "\n\n" + prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        lines = text.splitlines()
        if lines and lines[0].startswith("json"):
            text = "\n".join(lines[1:])

    return json.loads(text)
