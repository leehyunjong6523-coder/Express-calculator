"""
PDF 생성 모듈 — fpdf2 기반 (순수 파이썬, 시스템 의존성 없음)
"""
from datetime import datetime

try:
    from fpdf import FPDF
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

NAV = (0,   51, 102)   # #003366
GRY = (240, 244, 248)  # light gray
RED = (230,  57,  70)  # accent red
BLK = (51,   51,  51)

def _fmt(n):
    return f"W{int(round(n)):,}"


class QuotePDF(FPDF):
    def header(self): pass
    def footer(self): pass


def generate_pdf(quote_num="", customer="", staff="", selected=None,
                 result=None, ct_data=None,
                 fuel_dhl=28.75, fuel_fedex=29.75, fuel_ups=29.50,
                 notes="", **kwargs):
    if not PDF_AVAILABLE:
        raise RuntimeError("fpdf2가 설치되지 않았습니다.")
    if result is None: result = {}
    if selected is None: selected = list(result.get("carriers", {}).keys())
    if ct_data is None: ct_data = []

    carriers  = result.get("carriers", {})
    today     = datetime.now().strftime("%Y-%m-%d")
    dest_kr   = result.get("dest_kr", "")
    dest_en   = result.get("dest_country", "")
    dest      = f"{dest_kr} ({dest_en})" if dest_en else dest_kr
    total_act = result.get("total_actual_wt", 0)
    total_vol = result.get("total_vol_wt", 0)
    total_chg = result.get("total_chargeable", 0)
    chg_basis = "Vol.Weight" if total_vol > total_act else "Act.Weight"
    s_info    = STAFF_MAP.get(staff, {})
    staff_phone = s_info.get("phone", "")
    staff_email = s_info.get("email", "cs@airos.co.kr")

    valid     = [k for k in selected if k in carriers]

    pdf = QuotePDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_margins(15, 10, 15)
    pdf.set_auto_page_break(False)

    # ── 헤더 ──────────────────────────────────────
    pdf.set_fill_color(*NAV)
    pdf.rect(0, 0, 210, 22, 'F')
    pdf.set_xy(15, 5)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(80, 10, "AIRBRIDGE", ln=0)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 215, 230)
    pdf.set_xy(15, 14)
    pdf.cell(80, 5, "INTERNATIONAL EXPRESS", ln=0)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(110, 4)
    pdf.cell(85, 8, "AIRBRIDGE QUOTATION", align="R", ln=1)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(200, 215, 230)
    pdf.set_xy(110, 12)
    pdf.cell(85, 5, f"No: {quote_num}   Date: {today}", align="R", ln=1)

    pdf.set_y(26)

    # ── 기본 정보 + 화물 명세 (2단) ───────────────
    def section_title(txt):
        pdf.set_fill_color(*NAV)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, f"  {txt}", fill=True, ln=1)
        pdf.set_text_color(*BLK)

    def info_row(label, val, w_label=38, w_val=42):
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(w_label, 6, label, border="B", ln=0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*BLK)
        pdf.cell(w_val, 6, val, border="B", ln=0)

    # 왼쪽: 기본 정보
    left_x, top_y = 15, pdf.get_y()
    pdf.set_xy(left_x, top_y)
    pdf.set_fill_color(*NAV)
    pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica","B",9)
    pdf.cell(85, 6, "  QUOTATION INFO", fill=True, ln=0)

    # 오른쪽: 화물 명세
    pdf.set_xy(105, top_y)
    pdf.cell(90, 6, "  CARGO DETAILS", fill=True, ln=1)
    pdf.set_text_color(*BLK)

    row_y = pdf.get_y()
    pdf.set_xy(left_x, row_y)
    info_row("Customer", (customer or "—")[:22])
    pdf.set_xy(105, row_y)
    info_row("Gross Weight", f"{total_act:.1f} kg")
    pdf.ln(6)

    row_y = pdf.get_y()
    pdf.set_xy(left_x, row_y)
    info_row("Destination", dest[:22])
    pdf.set_xy(105, row_y)
    info_row("Vol. Weight", f"{total_vol:.1f} kg")
    pdf.ln(6)

    row_y = pdf.get_y()
    pdf.set_xy(left_x, row_y)
    info_row("Staff", f"{staff}  {staff_phone}"[:22])
    pdf.set_xy(105, row_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*NAV)
    pdf.cell(38, 6, "Chg. Weight", border="B", ln=0)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(42, 6, f"{total_chg:.1f} kg  ({chg_basis})", border="B", ln=1)
    pdf.set_text_color(*BLK)

    row_y = pdf.get_y()
    pdf.set_xy(left_x, row_y)
    info_row("Validity", "7 days from issue date")
    pdf.set_xy(105, row_y)
    pdf.ln(6)
    pdf.ln(4)

    # ── 화물 상세 테이블 ───────────────────────────
    if ct_data:
        section_title("CARGO DETAIL")
        pdf.set_fill_color(*GRY)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*BLK)
        for h, w in [("#",10),("QTY",15),("Act.Wt",25),("Size (cm)",45),("Vol.Wt",25),("Chg.Wt",25)]:
            pdf.cell(w, 6, h, border=1, align="C", fill=True, ln=0)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for i, ct in enumerate(ct_data):
            fill = (i % 2 == 0)
            pdf.set_fill_color(249, 250, 251) if fill else pdf.set_fill_color(255,255,255)
            qty = ct.get("qty",1)
            wt  = ct.get("wt",0)
            L,W,H = ct.get("L",0),ct.get("W",0),ct.get("H",0)
            vol_wt = round(L*W*H/5000, 2)
            chg_wt = max(wt, vol_wt)
            pdf.cell(10, 5.5, str(i+1), border=1, align="C", fill=fill, ln=0)
            pdf.cell(15, 5.5, str(qty), border=1, align="C", fill=fill, ln=0)
            pdf.cell(25, 5.5, f"{wt} kg", border=1, align="C", fill=fill, ln=0)
            pdf.cell(45, 5.5, f"{L}x{W}x{H}", border=1, align="C", fill=fill, ln=0)
            pdf.cell(25, 5.5, f"{vol_wt} kg", border=1, align="C", fill=fill, ln=0)
            pdf.set_text_color(*NAV)
            pdf.set_font("Helvetica","B",8)
            pdf.cell(25, 5.5, f"{chg_wt} kg", border=1, align="C", fill=fill, ln=1)
            pdf.set_text_color(*BLK)
            pdf.set_font("Helvetica","",8)
        pdf.ln(3)

    # ── 운임 비교 테이블 ───────────────────────────
    section_title("RATE COMPARISON")
    col_w = [40, 30, 35, 40, 25, 25]
    hdrs  = ["Carrier", "Base Rate", "Fuel Surcharge", "Add-on Services", "Transit", "Total"]
    pdf.set_fill_color(*NAV)
    pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in zip(hdrs, col_w):
        pdf.cell(w, 6, h, border=1, align="C", fill=True, ln=0)
    pdf.ln()
    pdf.set_text_color(*BLK)

    for i, key in enumerate(valid):
        c        = carriers[key]
        name     = PDF_NAME_MAP.get(key, key.upper())
        tt       = TT_MAP.get(key, "—")
        total    = int(round(c.get("total_quote", 0)))
        fuel_pct = c.get("fuel_pct", 0)
        fuel_amt = int(round(c.get("pub_fuel", 0) + c.get("sur_fuel_pub", 0)))
        base     = int(round(c.get("pub_disc") or c.get("pub_base", 0)))
        surs     = c.get("surs", [])
        sur_str  = " / ".join(f"{s['name']}" for s in surs) if surs else "—"

        fill = (i % 2 == 0)
        pdf.set_fill_color(249,250,251) if fill else pdf.set_fill_color(255,255,255)
        pdf.set_font("Helvetica","B",8)
        pdf.cell(col_w[0], 5.5, name, border=1, align="C", fill=fill, ln=0)
        pdf.set_font("Helvetica","",8)
        pdf.cell(col_w[1], 5.5, _fmt(base), border=1, align="C", fill=fill, ln=0)
        pdf.cell(col_w[2], 5.5, f"{fuel_pct:.1f}% ({_fmt(fuel_amt)})", border=1, align="C", fill=fill, ln=0)
        pdf.set_font("Helvetica","",7)
        pdf.cell(col_w[3], 5.5, sur_str[:28], border=1, align="C", fill=fill, ln=0)
        pdf.set_font("Helvetica","",8)
        pdf.cell(col_w[4], 5.5, tt, border=1, align="C", fill=fill, ln=0)
        pdf.set_text_color(*RED)
        pdf.set_font("Helvetica","B",8)
        pdf.cell(col_w[5], 5.5, _fmt(total), border=1, align="C", fill=fill, ln=1)
        pdf.set_text_color(*BLK)

    pdf.ln(4)

    # ── 유의사항 ───────────────────────────────────
    section_title("REMARKS")
    remarks = [
        "1. Rates are based on the cargo info provided. Actual charges may vary.",
        "2. Vol.Weight = L x W x H / 5,000. Applies if greater than actual weight.",
        "3. Fuel surcharge is subject to monthly change; rate at time of shipment applies.",
        "4. Destination duties/taxes and local charges are not included.",
        "5. Remote area, address correction fees will be charged at cost.",
        "6. This quotation is valid for 7 days from the date of issue.",
    ]
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_fill_color(250, 250, 250)
    pdf.set_text_color(80, 80, 80)
    for r in remarks:
        pdf.cell(0, 5, r, fill=True, ln=1)

    if notes and notes.strip():
        pdf.ln(2)
        section_title("NOTES")
        pdf.set_font("Helvetica","",8)
        pdf.set_text_color(*BLK)
        for line in notes.split("\n"):
            pdf.cell(0, 5, line[:90], ln=1)

    # ── 푸터 ──────────────────────────────────────
    pdf.set_fill_color(*NAV)
    pdf.rect(0, 282, 210, 15, 'F')
    pdf.set_xy(15, 284)
    pdf.set_font("Helvetica","B",9)
    pdf.set_text_color(255,255,255)
    pdf.cell(100, 5, "(Airbridge Co., Ltd.)", ln=0)
    pdf.set_font("Helvetica","",8)
    pdf.set_text_color(200,215,230)
    pdf.set_xy(15, 290)
    pdf.cell(180, 5, f"Tel: 032-502-1880   Email: {staff_email}", align="C", ln=1)

    return bytes(pdf.output())
