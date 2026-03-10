"""
PDF 생성 모듈 — HTML → PDF (weasyprint)
첨부 디자인 템플릿 기반 A4 1페이지 견적서
"""
from datetime import datetime

try:
    from weasyprint import HTML as WeasyprintHTML
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

PDF_NAME_MAP = {
    "dhl":     "DHL EXPRESS",
    "fedex":   "FEDEX EXPRESS",
    "fedex_e": "FEDEX ECONOMY",
    "ups2f":   "UPS SAVER",
    "upsb8":   "UPS SAVER",
}
TT_MAP = {
    "dhl":     "3~5 영업일",
    "fedex":   "3~4 영업일",
    "fedex_e": "5~7 영업일",
    "ups2f":   "5~7 영업일",
    "upsb8":   "5~7 영업일",
}
STAFF_MAP = {
    "호영준": {"phone": "010-3767-5413", "email": "cs@airos.co.kr"},
    "양희석": {"phone": "010-4594-0768", "email": "cs@airos.co.kr"},
    "이현종": {"phone": "010-4767-3264", "email": "cs@airos.co.kr"},
}

def _fmt(n):
    return f"₩{int(round(n)):,}"

def _build_html(quote_num, customer, staff, selected, result, ct_data,
                fuel_dhl, fuel_fedex, fuel_ups, notes=""):
    carriers  = result.get("carriers", {})
    today     = datetime.now().strftime("%Y-%m-%d")
    dest_kr   = result.get("dest_kr", "")
    dest_en   = result.get("dest_country", "")
    dest      = f"{dest_kr} ({dest_en})" if dest_en else dest_kr
    total_act = result.get("total_actual_wt", 0)
    total_vol = result.get("total_vol_wt", 0)
    total_chg = result.get("total_chargeable", 0)
    chg_basis = "부피중량" if total_vol > total_act else "실중량"
    s_info    = STAFF_MAP.get(staff, {})
    staff_phone = s_info.get("phone", "")
    staff_email = s_info.get("email", "cs@airos.co.kr")

    valid     = [k for k in selected if k in carriers]
    min_quote = min((carriers[k].get("total_quote", 9e9) for k in valid), default=0)
    best_keys = [k for k in valid if abs(carriers[k].get("total_quote", 9e9) - min_quote) < 1]

    # 화물 행
    cargo_rows = ""
    for i, ct in enumerate(ct_data):
        qty = ct.get("qty", 1)
        wt  = ct.get("wt", 0)
        L, W, H = ct.get("L",0), ct.get("W",0), ct.get("H",0)
        vol_wt = round(L*W*H/5000, 2)
        chg_wt = max(wt, vol_wt)
        bg = "#f9fafb" if i%2==0 else "#ffffff"
        cargo_rows += f'<tr style="background:{bg};"><td>{i+1}</td><td>{qty}</td><td>{wt} kg</td><td>{L}×{W}×{H}</td><td>{vol_wt} kg</td><td style="font-weight:700;color:#003366;">{chg_wt} kg</td></tr>'

    # 운임 행
    rate_rows = ""
    for key in valid:
        c        = carriers[key]
        name     = PDF_NAME_MAP.get(key, key.upper())
        tt       = TT_MAP.get(key, "—")
        total    = c.get("total_quote", 0)
        is_best  = key in best_keys
        hl       = 'style="color:#e63946;font-weight:800;"' if is_best else ""
        star     = " ★" if is_best else ""
        fuel_pct = c.get("fuel_pct", 0)
        surs     = c.get("surs", [])
        sur_str  = (" / ".join(f"{s['name']} {_fmt(s['amount'])}" for s in surs)) if surs else "—"
        fuel_amt = _fmt(c.get("pub_fuel",0) + c.get("sur_fuel_pub",0))
        rate_rows += f'<tr{"  class=\"best-price-row\"" if is_best else ""}><td style="font-weight:800;">{name}</td><td>{_fmt(c.get("pub_disc") or c.get("pub_base",0))}</td><td>{fuel_pct:.2f}%&nbsp;({fuel_amt})</td><td style="font-size:10px;">{sur_str}</td><td>{tt}</td><td {hl}>{_fmt(total)}{star}</td></tr>'

    notes_block = f"""<section><h3>비고 (Notes)</h3>
      <div style="border:1px solid #eee;padding:10px;background:#fafafa;border-radius:4px;font-size:12px;line-height:1.7;">
        {notes.replace(chr(10),"<br>")}</div></section>""" if notes and notes.strip() else ""

    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<style>
  @page {{ size:A4; margin:10mm 15mm; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:'Noto Sans KR','Malgun Gothic',Arial,sans-serif; font-size:12px; color:#333; margin:0; padding:0; background:white; }}
  header {{ border-bottom:3px solid #003366; padding-bottom:10px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:flex-end; }}
  .logo h1 {{ color:#003366; margin:0; font-size:24px; font-weight:800; }}
  .logo .tag {{ font-size:11px; color:#666; letter-spacing:3px; margin-top:3px; text-transform:uppercase; }}
  .doc-meta {{ text-align:right; font-size:12px; color:#555; }}
  .doc-meta h2 {{ margin:0 0 4px; font-size:18px; color:#333; }}
  h3 {{ font-size:13px; color:#003366; border-left:4px solid #003366; padding-left:8px; margin:0 0 8px; font-weight:700; }}
  section {{ margin-bottom:14px; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:14px; }}
  .info-box {{ border:1px solid #dee2e6; padding:10px; border-radius:4px; }}
  .info-row {{ display:flex; justify-content:space-between; margin-bottom:5px; font-size:12px; }}
  .info-row:last-child {{ margin-bottom:0; }}
  .info-label {{ font-weight:600; color:#555; }}
  table {{ width:100%; border-collapse:collapse; font-size:11.5px; }}
  th {{ background:#003366; color:#fff; font-weight:700; padding:7px 8px; text-align:center; border:1px solid #dee2e6; }}
  td {{ padding:6px 8px; border:1px solid #dee2e6; text-align:center; vertical-align:middle; }}
  .best-price-row {{ background:#fff8f8; }}
  .recommendation-box {{ background:#f8f9fa; border:2px solid #003366; padding:12px; text-align:center; border-radius:6px; }}
  .rec-title {{ color:#003366; font-weight:700; font-size:14px; margin-bottom:8px; }}
  .rec-carriers {{ font-size:16px; font-weight:800; margin-bottom:4px; }}
  .rec-price {{ font-size:22px; color:#e63946; font-weight:800; }}
  .remarks-list {{ font-size:11px; color:#666; margin:0; padding-left:18px; line-height:1.7; }}
  footer {{ border-top:1px solid #ddd; padding-top:10px; margin-top:14px; font-size:11px; color:#777; text-align:center; }}
  .company-info {{ font-weight:700; font-size:13px; color:#333; margin-bottom:4px; }}
</style>
</head><body>
<header>
  <div class="logo"><h1>✈ AIRBRIDGE</h1><div class="tag">International Express</div></div>
  <div class="doc-meta"><h2>국제 특송 운임견적서</h2>견적번호: <strong>{quote_num}</strong><br>견적일자: {today}</div>
</header>
<div class="grid-2">
  <section><h3>견적 기본 정보</h3><div class="info-box">
    <div class="info-row"><span class="info-label">고 객 사</span><span>{customer or "—"}</span></div>
    <div class="info-row"><span class="info-label">목 적 지</span><span>{dest}</span></div>
    <div class="info-row"><span class="info-label">담 당 자</span><span>{staff}&nbsp;&nbsp;{staff_phone}</span></div>
    <div class="info-row"><span class="info-label">유효기간</span><span>견적일로부터 7일</span></div>
  </div></section>
  <section><h3>화물 명세</h3><div class="info-box">
    <div class="info-row"><span class="info-label">총 중량 (Gross Weight)</span><span>{total_act:.1f} kg</span></div>
    <div class="info-row"><span class="info-label">부피 중량 (Vol. Weight)</span><span>{total_vol:.1f} kg</span></div>
    <div class="info-row" style="color:#003366;"><span class="info-label" style="color:#003366;">청구 중량 (Chg. Weight)</span><span style="font-weight:700;">{total_chg:.1f} kg</span></div>
    <div class="info-row"><span class="info-label">청구 기준</span><span>{chg_basis}</span></div>
  </div></section>
</div>
<section><h3>화물 상세</h3>
  <table><thead><tr><th>#</th><th>수량</th><th>실중량</th><th>사이즈 (cm)</th><th>부피중량</th><th>적용중량</th></tr></thead>
  <tbody>{cargo_rows}</tbody></table>
</section>
<section><h3>운송사별 운임 비교 (Rate Comparison)</h3>
  <table><thead><tr><th>운송사</th><th>기본운임</th><th>유류할증료</th><th>부가서비스</th><th>소요시간</th><th>총 견적금액</th></tr></thead>
  <tbody>{rate_rows}</tbody></table>
</section>
{notes_block}
<section><h3>유의사항 (Remarks)</h3>
  <div style="border:1px solid #eee;padding:10px;background:#fafafa;border-radius:4px;">
    <ol class="remarks-list">
      <li>상기 견적은 제시된 화물의 중량 및 부피를 기준으로 작성되었으며, 실제 화물 정보가 다를 경우 운임이 변경될 수 있습니다.</li>
      <li>부피중량(가로×세로×높이÷5,000)이 실중량보다 클 경우 부피중량이 청구 중량으로 적용됩니다.</li>
      <li>유류할증료는 매월 변동될 수 있으며, 발송 시점의 요율이 적용됩니다.</li>
      <li>도착지 세금(관세, 부가세 등) 및 현지 발생 비용은 포함되지 않았습니다.</li>
      <li>오지 배송료, 주소 정정료 등 추가 비용 발생 시 실비 청구됩니다.</li>
      <li>본 견적서는 발급일로부터 7일간 유효합니다.</li>
    </ol>
  </div>
</section>
<footer>
  <div class="company-info">(주)에어브리지 (AIRBRIDGE Co., Ltd.)</div>
  <div>Tel: 032-502-1880 &nbsp;|&nbsp; Email: {staff_email}</div>
</footer>
</body></html>"""


def generate_pdf(quote_num="", customer="", staff="", selected=None,
                 result=None, ct_data=None,
                 fuel_dhl=28.75, fuel_fedex=29.75, fuel_ups=29.50,
                 notes="", **kwargs):
    if not PDF_AVAILABLE:
        raise RuntimeError("weasyprint가 설치되지 않았습니다.")
    if result is None: result = {}
    if selected is None: selected = list(result.get("carriers", {}).keys())
    if ct_data is None: ct_data = []
    html_str = _build_html(
        quote_num=quote_num, customer=customer, staff=staff,
        selected=selected, result=result, ct_data=ct_data,
        fuel_dhl=fuel_dhl, fuel_fedex=fuel_fedex, fuel_ups=fuel_ups, notes=notes,
    )
    return WeasyprintHTML(string=html_str).write_pdf()
