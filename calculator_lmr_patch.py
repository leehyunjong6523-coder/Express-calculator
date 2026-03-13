"""
calculator.py 에 추가할 /api/ai-lmr 엔드포인트
기존 /api/ai-ocr 엔드포인트 바로 아래에 붙여넣으세요.
"""

@app.route('/api/ai-lmr', methods=['POST'])
def api_ai_lmr():
    """FedEx LMR 견적 이미지 → 항목별 금액 추출"""
    import anthropic, base64, json, re

    mode = request.form.get('mode', 'lmr')
    file = request.files.get('file')
    if not file:
        return jsonify({'ok': False, 'error': '파일이 없습니다'})

    img_data  = file.read()
    b64_data  = base64.standard_b64encode(img_data).decode('utf-8')
    mime_type = file.content_type or 'image/png'

    PROMPT = """이 이미지는 FedEx 국제특송 견적 확인서입니다.
화면에서 운임 항목별 금액(KRW 기준)을 추출해주세요.

반드시 아래 JSON 형식만 반환하세요 (마크다운, 설명 절대 금지):
{
  "items": [
    {"name": "Freight", "amount": 1167305},
    {"name": "유류할증료", "amount": 388129},
    {"name": "부가서비스명", "amount": 0}
  ],
  "total": 1555434
}

규칙:
- items에는 Freight, 유류할증료(Fuel), 그 외 모든 부가서비스를 포함
- amount는 숫자만 (쉼표, 원, KRW 제거)
- total은 모든 항목 합계
- 항목이 없으면 items를 빈 배열로
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=512,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': mime_type,
                        'data': b64_data,
                    }
                },
                {'type': 'text', 'text': PROMPT}
            ]
        }]
    )

    raw = response.content[0].text.strip()
    # JSON 파싱 (마크다운 펜스 제거)
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)

    try:
        parsed = json.loads(raw)
        items  = parsed.get('items', [])
        total  = parsed.get('total', sum(i.get('amount', 0) for i in items))
        return jsonify({'ok': True, 'items': items, 'total': total})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'파싱 실패: {str(e)}', 'raw': raw})
