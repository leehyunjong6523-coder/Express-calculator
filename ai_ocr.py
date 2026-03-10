"""Claude Haiku AI OCR — 화물 정보 추출"""
import os
import json
import base64
import re
import requests

CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def _get_api_key():
    """키를 호출 시점에 읽음 — dotenv 로드 후에도 정상 동작"""
    return os.environ.get("ANTHROPIC_API_KEY", "") or CLAUDE_API_KEY

_EXTRACT_SCHEMA = """
다음 JSON 형식으로만 응답:
{
  "country": "국가명(영문)",
  "postal_code": "우편번호(없으면 빈 문자열)",
  "city": "도시명(없으면 빈 문자열)",
  "ct_count": 박스/C.T 수(정수),
  "weight_kg": 총중량(kg 단위. g이면 1000으로 나눠 변환. 예: 400g→0.4),
  "length_cm": 가로(cm, 정수),
  "width_cm": 세로(cm, 정수),
  "height_cm": 높이(cm, 정수),
  "is_document": true/false
}
모든 값이 없으면 null. 반드시 JSON만 출력.

[국가 추론 규칙 - 텍스트에 국가명 없어도 주소/우편번호/도시명으로 반드시 추론]
- 인도 우편번호: 6자리 숫자(예:603204). 주명 TN/MH/KA/DL/UP/AP/TS/GJ/RJ/WB/PB 포함시 → India
- 인도 도시: Chennai, Mumbai, Delhi, Bangalore, Hyderabad, Kolkata, Chengalpattu, Coimbatore, Pune, Maraimalai, Nagar, Ahmedabad 등 → India
- England/Britain/UK → United Kingdom
- USA/US + 미국 주명(CA/NY/TX/FL 등) 또는 5자리 ZIP → United States of America
- Turkey/Turkiye → Turkiye
- China/PRC → China (People's Republic)
- HongKong/HK → Hong Kong SAR China
- Taiwan/ROC → Taiwan China
- Vietnam/Viet Nam → Vietnam
- Korea/South Korea → South Korea
- UAE/Dubai/Abu Dhabi → United Arab Emirates
- Laos → Lao P.D.R.
- Iran → Iran Islamic Rep. of
- Russia → Russia
- Czech/Czechia → Czech Republic
- 일본: 〒 또는 xxx-xxxx 우편번호 형식 → Japan
- 호주: 4자리 우편번호 + 호주 주명(NSW/VIC/QLD/WA 등) → Australia
- 캐나다: A1A 1A1 형식 우편번호 → Canada
"""


def _validate(r: dict) -> dict:
    defaults = {
        "country": "", "postal_code": "", "city": "",
        "ct_count": 1, "weight_kg": 1.0,
        "length_cm": 10, "width_cm": 10, "height_cm": 10,
        "is_document": False
    }
    for k, v in defaults.items():
        if k not in r or r[k] is None:
            r[k] = v
    r["ct_count"]   = max(1, int(r["ct_count"] or 1))
    r["weight_kg"]  = max(0.1, float(r["weight_kg"] or 0.5))
    r["length_cm"]  = max(1, int(r["length_cm"] or 10))
    r["width_cm"]   = max(1, int(r["width_cm"] or 10))
    r["height_cm"]  = max(1, int(r["height_cm"] or 10))
    return r


def _parse_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


def call_claude_image(image_bytes: bytes, mime_type: str) -> dict:
    key = _get_api_key()
    if not key:
        return {"error": "ANTHROPIC_API_KEY 환경변수 미설정"}
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                {"type": "text", "text": f"이 운송장/패킹리스트에서 화물 정보를 추출하세요.\n{_EXTRACT_SCHEMA}"}
            ]
        }]
    }
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=payload, timeout=30
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        return _validate(_parse_json(text))
    except Exception as e:
        return {"error": str(e)[:200]}


def call_claude_text(text: str) -> dict:
    key = _get_api_key()
    if not key:
        return {"error": "ANTHROPIC_API_KEY 환경변수 미설정"}
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": f"다음 텍스트에서 화물 정보를 추출하세요.\n{_EXTRACT_SCHEMA}\n\n텍스트:\n{text}"
        }]
    }
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=payload, timeout=30
        )
        resp.raise_for_status()
        text_out = resp.json()["content"][0]["text"]
        return _validate(_parse_json(text_out))
    except Exception as e:
        return {"error": str(e)[:200]}
