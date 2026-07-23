import os
import json
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 1. Gemini API 설정
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("환경 변수 GOOGLE_API_KEY가 설정되어 있지 않습니다.")

genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-3.6-flash"
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
    """
    사용자가 입력한 텍스트를 Gemini로 분석해서
    위에서 정의한 JSON 스키마에 맞는 요구사항 딕셔너리로 변환합니다.
    """
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

    # ```json ... ``` 형태로 올 수 있으니 껍질 제거
    if text.startswith("```"):
        text = text.strip("`")
        lines = text.splitlines()
        if lines and lines[0].startswith("json"):
            text = "\n".join(lines[1:])

    requirements = json.loads(text)
    return requirements

# 2. 샘플 빈상가 데이터
SPACES = [
    {
        "id": 1,
        "name": "A상가",
        "monthly_rent": 55,   # 만원 단위
        "area": 18,
        "floor": 2,
        "location_tags": ["성안길", "조용한 골목"],
        "suitable_types": ["디자인 스튜디오", "공방"],
    },
    {
        "id": 2,
        "name": "B상가",
        "monthly_rent": 70,
        "area": 25,
        "floor": 1,
        "location_tags": ["성안길", "유동인구 많은 거리"],
        "suitable_types": ["카페", "음식점"],
    },
    {
        "id": 3,
        "name": "C상가",
        "monthly_rent": 50,
        "area": 15,
        "floor": 3,
        "location_tags": ["조용한 골목"],
        "suitable_types": ["작업실", "디자인 스튜디오"],
    },
]

# 3. 점수 계산 로직
def score_space(space: dict, req: dict) -> int:
    """
    Gemini가 분석한 요구사항(req)을 기준으로
    각 상가(space)에 점수를 매깁니다.
    """
    score = 0

    # 예산
    budget = req.get("budget", {})
    max_rent = budget.get("max_amount")
    if max_rent is not None:
        if space["monthly_rent"] <= max_rent:
            score += 30
        else:
            score -= 10

    # 업종 적합도
    business_type = req.get("business_type")
    if business_type and business_type in space["suitable_types"]:
        score += 30

    # 위치 태그 선호
    preferred_tags = req.get("preferred_location_tags", [])
    for p in preferred_tags:
        for t in space["location_tags"]:
            if t in p or p in t:
                score += 10

    # 층수 선호 (예: "2층이면 좋겠다")
    constraints = req.get("constraints", [])
    wants_second_floor = any("2층" in c for c in constraints)
    if wants_second_floor:
        if space["floor"] == 2:
            score += 20
        else:
            score -= 5

    # 조용한 공간 선호
    keywords = req.get("keywords", [])
    if ("조용한 공간" in keywords or "조용함" in keywords) and "조용한 골목" in space["location_tags"]:
        score += 15

    return score

# 4. Flask 엔드포인트
@app.route("/recommend", methods=["POST"])
def recommend():
    """
    POST /recommend
    Body(JSON): { "text": "사용자 요구 텍스트" }

    반환:
    {
      "requirements": { ...Gemini가 분석한 JSON... },
      "results": [ 상위 3개 상가 + 점수 ]
    }
    """
    data = request.get_json(silent=True) or {}
    user_text = data.get("text")
    if not user_text:
        return jsonify({"error": "text 필드가 필요합니다."}), 400

    try:
        req = parse_requirements(user_text)
    except Exception as e:
        return jsonify({"error": "요구 분석 실패", "detail": str(e)}), 500

    scored_spaces = []
    for space in SPACES:
        s = score_space(space, req)
        item = {**space, "score": s}
        scored_spaces.append(item)

    scored_spaces.sort(key=lambda x: x["score"], reverse=True)
    top_n = scored_spaces[:3]

    return jsonify({
        "requirements": req,
        "results": top_n
    })

@app.route("/")
def index():
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
