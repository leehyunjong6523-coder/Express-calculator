import os
import io
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 폰트 경로 — 멀티플랫폼 자동탐색
# ═══════════════════════════════════════════════════
def _find_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansCJK-Regular.ttc"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "malgun.ttf"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def _find_bold_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/NanumGothicBold.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansCJK-Bold.ttc"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "malgunbd.ttf"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return _find_font()

_FONT_REG_PATH  = _find_font()
_FONT_BOLD_PATH = _find_bold_font()
_USE_PIL_DEFAULT = (_FONT_REG_PATH is None)

# ═══════════════════════════════════════════════════
# PDF 생성 함수 (Pillow)
# ═══════════════════════════════════════════════════
def _generate_pdf_core(quote_num, customer, dest_country, zone_label, ct_count,
                 total_chargeable, fuel_dhl, fuel_fedex, fuel_ups, selected, results, disc_map,
                 notes="", layout="table",
                 our_company="", our_contact="", our_phone="", our_email="",
                 ct_data=None, total_actual_wt=0, is_doc=False, mode="수출"):
    """Pillow A4 견적서 PDF — 300dpi 고해상도, 대형 폰트, UPS 단일 표기"""
    W, H = 2481, 3508   # A4 300dpi
    PAD  = 105          # 여백 비례 확대

    img = Image.new('RGB', (W, H), '#FFFFFF')
    d   = ImageDraw.Draw(img)

    def fnt(size, bold=False):
        path = _FONT_BOLD_PATH if bold else _FONT_REG_PATH
        if path and os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: pass
        return ImageFont.load_default()

    def tw(text, font):
        try:
            b = font.getbbox(text); return b[2]-b[0]
        except: return len(text)*10

    def ra(text, font, rx, y, fill):
        d.text((rx - tw(text, font), y), text, font=font, fill=fill)

    def draw_section_bar(y, title, bg='#1e3a8a'):
        d.rectangle([PAD, y, W-PAD, y+58], fill=bg)
        d.text((PAD+24, y+12), title, font=fnt(32, bold=True), fill='white')
        return y + 72

    # ── PDF 내 UPS 표시명: 계정 구분 없이 "UPS" 로만 표기 ──
    PDF_NAME_MAP = {
        # 소문자 키 (generate_pdf 래퍼에서 넘어오는 경우)
        "dhl":          "DHL EXPRESS",
        "fedex":        "FEDEX EXPRESS",
        "fedex_e":      "FEDEX ECONOMY",
        "ups2f":        "UPS SAVER",
        "upsb8":        "UPS SAVER",
        # 풀네임 (직접 호출하는 경우)
        "DHL Express":  "DHL EXPRESS",
        "FedEx IP":     "FEDEX EXPRESS",
        "FedEx Economy":"FEDEX ECONOMY",
        "UPS 2F94A8":   "UPS SAVER",
        "UPS B8733R":   "UPS SAVER",
    }
    def pdf_disp(name):
        return PDF_NAME_MAP.get(name, name.upper())

    def fmt(v):
        """숫자를 원화 포맷으로 변환"""
        try:
            return f"₩{int(round(v)):,}"
        except:
            return str(v)

    # ─────────────────────────────────
    # 헤더
    # ─────────────────────────────────
    HEADER_H = 240
    d.rectangle([0, 0, W, HEADER_H], fill='#1e3a8a')
    d.rectangle([0, HEADER_H, W, HEADER_H+6], fill='#3b82f6')

    base_dir   = os.path.dirname(os.path.abspath(__file__))
    logo_en_p  = os.path.join(base_dir, "logo_en.jpg")
    logo_end_x = PAD + 16
    if os.path.exists(logo_en_p):
        try:
            logo = Image.open(logo_en_p).convert("RGB")
            lw, lh = logo.size
            th = 150; tw_l = int(lw*th/lh)
            logo = logo.resize((tw_l, th), Image.LANCZOS)
            img.paste(logo, (PAD, (HEADER_H-th)//2))
            logo_end_x = PAD + tw_l + 36
        except: pass

    d.text((logo_end_x, 20),  "에어브리지 국제 특송 운임견적서",  font=fnt(68, bold=True), fill='#ffffff')
    d.text((logo_end_x, 120), "AIRBRIDGE EXPRESS FREIGHT RATE QUOTATION", font=fnt(24), fill='#bfdbfe')

    ra(f"No. {quote_num}",                           fnt(34, bold=True), W-PAD,  42, '#e0f2fe')
    ra(datetime.now().strftime("%Y년 %m월 %d일"),   fnt(28),            W-PAD,  94, '#7788aa')
    _contact_str = our_contact if our_contact else (our_company if our_company else "")
    if _contact_str: ra(_contact_str, fnt(28, bold=True), W-PAD, 148, '#fef3c7')
    _phone_str = our_phone if our_phone else ""
    if _phone_str:   ra(_phone_str,   fnt(26),            W-PAD, 190, '#aabbcc')

    y = HEADER_H + 20

    # ─────────────────────────────────
    # 기본 정보 + 화물 상세 (풍성한 2블록)
    # ─────────────────────────────────
    y = draw_section_bar(y, "  견적 기본 정보")

    # selected는 list(['dhl','fedex','ups2f',...]) 또는 dict 모두 허용
    if isinstance(selected, dict):
        sel_names_raw = [n for n, v in selected.items() if v]
    else:
        sel_names_raw = list(selected) if selected else list(results.keys())

    # UPS는 무조건 단일 출력 (ups2f/upsb8 또는 "UPS..." 모두 처리)
    def _is_ups(n): return "UPS" in n.upper() or n.lower().startswith("ups")

    seen_ups = False
    sel_names = []
    for n in sel_names_raw:
        if _is_ups(n):
            if not seen_ups:
                sel_names.append(n)
                seen_ups = True
            # else: skip — UPS 두 번째는 버림
        else:
            sel_names.append(n)
    ups_both = seen_ups and sum(1 for n in sel_names_raw if _is_ups(n)) >= 2

    fuel_items = []
    for nm in sel_names_raw:
        nm_up = nm.upper()
        if "DHL"   in nm_up and f"DHL {fuel_dhl}%"     not in fuel_items: fuel_items.append(f"DHL {fuel_dhl:.2f}%")
        if "FEDEX" in nm_up and f"FedEx {fuel_fedex}%" not in fuel_items: fuel_items.append(f"FedEx {fuel_fedex:.2f}%")
        if _is_ups(nm)       and f"UPS {fuel_ups}%"    not in fuel_items: fuel_items.append(f"UPS {fuel_ups:.2f}%")

    # ── 좌/우 2단 구성 ──
    col2   = W // 2
    ROW_H  = 52
    LBL_X  = PAD + 24
    VAL_X  = PAD + 230
    RLBL_X = col2 + 24
    RVAL_X = col2 + 230

    # 좌: 수신·목적지·화물구분·발신
    _cargo_type_str = "서류 (Document)" if is_doc else "물품 (Non-Document)"
    _mode_str       = "수입 (Import)" if mode == "수입" else "수출 (Export)"
    _zone_short     = zone_label  # "DHL Z3 / FedEx ZC / UPS Z6"
    _carrier_str    = ", ".join(pdf_disp(n) for n in sel_names) if sel_names else "-"

    info_L = [
        ("수    신", customer or "-"),
        ("담 당 자", our_contact or "-"),
        ("목 적 지", dest_country),
        ("운송 구분", _mode_str),
        ("화물 구분", _cargo_type_str),
    ]
    info_R = [
        ("견적번호", quote_num),
        ("견적일자", datetime.now().strftime("%Y년 %m월 %d일")),
        ("유효기간", "발행일로부터 7일"),
        ("유류할증료", " / ".join(fuel_items) if fuel_items else "-"),
    ]

    # 발신정보 (하단 가로줄 위)
    _sender_parts = []
    if our_company: _sender_parts.append(our_company)
    if our_contact: _sender_parts.append(f"담당: {our_contact}")
    if our_phone:   _sender_parts.append(f"☎ {our_phone}")
    if our_email:   _sender_parts.append(f"✉ {our_email}")

    INFO_ROWS = len(info_L)  # 5
    INFO_H    = INFO_ROWS * ROW_H + (ROW_H + 10 if _sender_parts else 0) + 24

    d.rectangle([PAD, y, W-PAD, y+INFO_H], fill='#f8faff', outline='#dbe7ff', width=2)
    # 중앙 세로 구분선
    d.line([col2, y+10, col2, y+INFO_H-10], fill='#d8e4f5', width=2)

    for i, (lbl, val) in enumerate(info_L):
        iy = y + 14 + i * ROW_H
        d.text((LBL_X,  iy), lbl, font=fnt(28, bold=True), fill='#445566')
        d.text((VAL_X,  iy), val, font=fnt(28),            fill='#1e293b')
        if i < INFO_ROWS - 1:
            d.line([PAD+12, iy+ROW_H-2, col2-12, iy+ROW_H-2], fill='#e8eef8', width=1)

    for i, (lbl, val) in enumerate(info_R):
        iy = y + 14 + i * ROW_H
        d.text((RLBL_X, iy), lbl, font=fnt(28, bold=True), fill='#445566')
        d.text((RVAL_X, iy), val, font=fnt(28),            fill='#1e293b')
        if i < INFO_ROWS - 1:
            d.line([col2+12, iy+ROW_H-2, W-PAD-12, iy+ROW_H-2], fill='#e8eef8', width=1)

    if _sender_parts:
        sy = y + INFO_H - ROW_H - 4
        d.line([PAD, sy-2, W-PAD, sy-2], fill='#c5d5ea', width=2)
        d.rectangle([PAD, sy-2, PAD+8, sy-2+ROW_H+8], fill='#2563eb')
        d.text((LBL_X,   sy+6), "발    신", font=fnt(28, bold=True), fill='#1e3a8a')
        d.text((PAD+210, sy+6), "  |  ".join(_sender_parts), font=fnt(27), fill='#1e293b')

    y += INFO_H + 14

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 화물 상세 테이블 (C/T별)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    y = draw_section_bar(y, "  화물 명세 (Cargo Details)", bg='#1d4775')

    _ct_list = ct_data if ct_data else []
    CT_ROW   = 52
    CT_HDR   = 62

    # 컬럼 정의: [라벨, 너비, 정렬('l'/'r')]
    CT_COLS = [
        ("No.",           130, 'c'),
        ("실중량 (kg)",   260, 'r'),
        ("가로 (cm)",     240, 'r'),
        ("세로 (cm)",     240, 'r'),
        ("높이 (cm)",     240, 'r'),
        ("부피중량 (kg)", 290, 'r'),
        ("청구중량 (kg)", 290, 'r'),
        ("청구기준",      280, 'c'),
    ]
    _ct_total_w = sum(c[1] for c in CT_COLS)
    _ct_scale   = (W - PAD*2) / _ct_total_w
    CT_COLS_S   = [(lbl, int(w*_ct_scale), a) for lbl, w, a in CT_COLS]

    CT_H = CT_HDR + CT_ROW * (len(_ct_list) + 1) + 16
    d.rectangle([PAD, y, W-PAD, y+CT_H], fill='#ffffff', outline='#dbe7ff', width=2)

    # 헤더행
    _cx = PAD
    for lbl, cw, _ in CT_COLS_S:
        d.rectangle([_cx, y, _cx+cw, y+CT_HDR], fill='#1e3a8a')
        _cx += cw
    _cx = PAD
    for lbl, cw, align in CT_COLS_S:
        _tw = tw(lbl, fnt(28, bold=True))
        _tx = _cx + (cw - _tw)//2
        d.text((_tx, y+14), lbl, font=fnt(28, bold=True), fill='#bfdbfe')
        _cx += cw

    # 데이터행
    from math import ceil as _ceil
    def _vwt(ct):
        return round(ct["L"] * ct["W"] * ct["H"] / 5000, 2)
    def _cwt(ct):
        vw = _vwt(ct)
        rw = max(ct["wt"], vw)
        return round(_ceil(rw * 2) / 2, 1)
    def _basis(ct):
        return "부피" if _vwt(ct) > ct["wt"] else "실중량"

    _total_act = 0; _total_vol = 0; _total_chg = 0
    ry = y + CT_HDR
    for i, ct in enumerate(_ct_list):
        vw  = _vwt(ct)
        cw2 = _cwt(ct)
        bas = _basis(ct)
        _total_act += ct["wt"]; _total_vol += vw; _total_chg += cw2
        bg = '#f5f8ff' if i % 2 == 0 else '#ffffff'
        d.rectangle([PAD, ry, W-PAD, ry+CT_ROW], fill=bg)
        row_vals = [
            f"C/T {i+1}",
            f"{ct['wt']:.1f}",
            f"{ct['L']:.0f}",
            f"{ct['W']:.0f}",
            f"{ct['H']:.0f}",
            f"{vw:.2f}",
            f"{cw2:.1f}",
            bas,
        ]
        _cx = PAD
        for j, (val, (_, cw3, align)) in enumerate(zip(row_vals, CT_COLS_S)):
            _tf = fnt(28)
            _tw2 = tw(val, _tf)
            if align == 'r':   _tx = _cx + cw3 - _tw2 - 16
            elif align == 'c': _tx = _cx + (cw3 - _tw2)//2
            else:              _tx = _cx + 16
            fc = '#1e293b' if j not in (5,6,7) else ('#2563eb' if bas == "부피" and j in (5,6) else '#334155')
            d.text((_tx, ry+12), val, font=_tf, fill=fc)
            _cx += cw3
        d.line([PAD+8, ry+CT_ROW-1, W-PAD-8, ry+CT_ROW-1], fill='#e8eef8', width=1)
        ry += CT_ROW

    # 합계행
    d.rectangle([PAD, ry, W-PAD, ry+CT_ROW], fill='#e8f0fe')
    _sum_vals = [
        "합 계",
        f"{_total_act:.1f}",
        "-", "-", "-",
        f"{round(_total_vol,2):.2f}",
        f"{_total_chg:.1f}",
        "",
    ]
    _cx = PAD
    for val, (_, cw3, align) in zip(_sum_vals, CT_COLS_S):
        _tf = fnt(30, bold=True)
        _tw3 = tw(val, _tf)
        if align == 'r':   _tx = _cx + cw3 - _tw3 - 16
        elif align == 'c': _tx = _cx + (cw3 - _tw3)//2
        else:              _tx = _cx + 16
        d.text((_tx, ry+10), val, font=_tf, fill='#1e3a8a')
        _cx += cw3

    y += CT_H + 18

    # ─────────────────────────────────
    # 운임 비교
    # ─────────────────────────────────
    n_cols = len(sel_names)
    if n_cols == 0:
        d.text((PAD, y), "선택된 운송사가 없습니다.", font=fnt(30), fill='#cc0000')

    elif layout == "card":
        y = draw_section_bar(y, "  운임 견적 (운송사별)")

        CC = {
            "DHL Express":   '#C00010', "FedEx IP":      '#4D148C',
            "FedEx Economy": '#5510a0', "UPS 2F94A8":    '#6b3320',
            "UPS B8733R":    '#8a4a28',
        }
        TT = {
            "DHL Express":"1~3 영업일","FedEx IP":"1~3 영업일",
            "FedEx Economy":"7~8 영업일","UPS 2F94A8":"2~5 영업일","UPS B8733R":"2~5 영업일",
        }

        cols_per_row = min(2, n_cols)
        GAP    = 42
        cw     = (W - PAD*2 - GAP*(cols_per_row-1)) // cols_per_row
        HDR_H  = 108
        ITEM_H = 56

        for idx, name in enumerate(sel_names):
            r         = results.get(name, {})
            cc        = CC.get(name, '#333')
            disp_name = pdf_disp(name)
            is_nsvc   = r.get("no_service", False)
            is_freight_pdf = "__freight__" in r.get("surs_detail", {})

            # CARD_H를 is_nsvc 여부와 관계없이 먼저 계산
            if is_nsvc or is_freight_pdf:
                CARD_H = HDR_H + 34 + 32 + 92 + 28 + 2*ITEM_H + 24 + 58 + 42  # 서비스불가 고정 높이
            else:
                _ri_pdf = r.get("rate_info", {})
                _drpk_p = _ri_pdf.get("disc_rpk")
                _tw_p   = _ri_pdf.get("total_w", total_chargeable)
                if _drpk_p:
                    _air_lbl = f"항공운임  ({_drpk_p:,}원/kg)"
                else:
                    _air_lbl = "항공운임"
                det = [(_air_lbl, r.get("pub_disc",0), False)]
                surs_d = r.get("surs_detail", {})
                sur    = r.get("sur_total", 0)
                if sur > 0:
                    for s_nm, s_val in surs_d.items():
                        det.append((f"  └ {s_nm}", s_val, False))
                    if len(surs_d) >= 2:
                        det.append(("부가서비스 소계", sur, True))
                fuel = r.get("pub_fuel", 0) + r.get("sur_fuel_pub", 0)
                det.append(("유류할증료", fuel, False))
                CARD_H = HDR_H + 34 + 32 + 92 + 28 + len(det)*ITEM_H + 24 + 58 + 42

            ci = idx % cols_per_row
            ri = idx // cols_per_row
            cx = PAD + ci*(cw+GAP)
            cy = y  + ri*(CARD_H+GAP)

            if is_nsvc:
                # ── 서비스불가 카드 ──
                d.rectangle([cx, cy, cx+cw, cy+CARD_H], fill='#fef2f2', outline='#fca5a5', width=4)
                d.rectangle([cx, cy, cx+cw, cy+HDR_H],  fill='#fca5a5')
                d.text((cx+30, cy+30), disp_name, font=fnt(40, bold=True), fill='#7f1d1d')
                nsvc_mid = cy + HDR_H + (CARD_H - HDR_H)//2 - 100
                d.text((cx+30, nsvc_mid),      "서비스 불가 국가", font=fnt(44, bold=True), fill='#b91c1c')
                d.text((cx+30, nsvc_mid+70),   "2026년 기준 해당 운송사의", font=fnt(30), fill='#94a3b8')
                d.text((cx+30, nsvc_mid+110),  "서비스 미제공 지역입니다.", font=fnt(30), fill='#94a3b8')
                continue

            if is_freight_pdf:
                # ── Freight 전환 카드 ──
                d.rectangle([cx, cy, cx+cw, cy+CARD_H], fill='#fff7ed', outline='#fb923c', width=4)
                d.rectangle([cx, cy, cx+cw, cy+HDR_H],  fill='#7c2d12')
                d.text((cx+30, cy+30), disp_name, font=fnt(40, bold=True), fill='#ffffff')
                frt_mid = cy + HDR_H + (CARD_H - HDR_H)//2 - 110
                d.text((cx+30, frt_mid),      "Express Freight 진행 화물", font=fnt(40, bold=True), fill='#92400e')
                d.text((cx+30, frt_mid+70),   "Express Saver 진행 불가",   font=fnt(40, bold=True), fill='#c2410c')
                d.text((cx+30, frt_mid+130),  "C/T당 실중량 70kg 초과",     font=fnt(28), fill='#94a3b8')
                d.text((cx+30, frt_mid+168),  "WW Express Freight 별도 문의", font=fnt(28), fill='#94a3b8')
                continue

            d.rectangle([cx, cy, cx+cw, cy+CARD_H], fill='#ffffff', outline=cc, width=4)
            d.rectangle([cx, cy, cx+cw, cy+HDR_H],  fill=cc)
            d.text((cx+30, cy+30), disp_name, font=fnt(40, bold=True), fill='white')

            iy = cy + HDR_H + 34
            tt  = TT.get(name, "")
            d.text((cx+30, iy), f"T/T  {tt}", font=fnt(30), fill='#2563eb')
            iy += 62

            d.text((cx+30, iy), fmt(r.get("total_quote", 0)), font=fnt(60, bold=True), fill=cc)
            iy += 102

            d.line([cx+24, iy, cx+cw-24, iy], fill='#dbeafe', width=3)
            iy += 28

            for lbl, val, is_sub in det:
                is_indent = lbl.startswith("  ")
                fill_c = '#aabbcc' if is_indent else ('#445566' if is_sub else '#556677')
                fs = 26 if is_indent else 30
                d.text((cx+30 + (30 if is_indent else 0), iy), lbl.strip(),
                       font=fnt(fs, bold=is_sub), fill=fill_c)
                ra(fmt(val), fnt(fs, bold=is_sub), cx+cw-30, iy,
                   '#99aabb' if is_indent else '#334455')
                iy += ITEM_H

            d.line([cx+24, iy, cx+cw-24, iy], fill='#93c5fd', width=3)
            iy += 18
            d.text((cx+30, iy), "합    계", font=fnt(36, bold=True), fill='#1e3a8a')
            ra(fmt(r.get("total_quote",0)), fnt(36, bold=True), cx+cw-30, iy, cc)

        rows_used = ((n_cols-1)//cols_per_row + 1)
        last_row_names = sel_names[-(n_cols - (rows_used-1)*cols_per_row):]
        max_card_h = 0
        for name in last_row_names:
            r2 = results.get(name, {})
            if r2.get("no_service"):
                ch = HDR_H + 34 + 32 + 92 + 28 + 2*56 + 24 + 58 + 42
            else:
                surs_d2 = r2.get("surs_detail", {})
                det2 = [None]
                if r2.get("sur_total",0) > 0:
                    det2 += [None]*len(surs_d2)
                    if len(surs_d2) >= 2: det2.append(None)
                det2.append(None)
                ch = HDR_H + 34 + 32 + 92 + 28 + len(det2)*56 + 24 + 58 + 42
            max_card_h = max(max_card_h, ch)
        y += rows_used*(max_card_h+GAP) + 18

    else:
        # ── 표형 ──
        CC_TBL = {
            "DHL Express":   ('#C00010','#fff5f5'), "FedEx IP":      ('#4D148C','#f8f5ff'),
            "FedEx Economy": ('#5510a0','#f5f0ff'), "UPS 2F94A8":    ('#6b3320','#fffaf5'),
            "UPS B8733R":    ('#8a4a28','#fff8f2'),
        }
        TT = {
            "DHL Express":"1~3 영업일","FedEx IP":"1~3 영업일",
            "FedEx Economy":"7~8 영업일","UPS 2F94A8":"2~5 영업일","UPS B8733R":"2~5 영업일",
        }
        LBL_W = 340
        RH    = 62
        BDR   = '#c8d0e0'

        name_groups = [sel_names[i:i+2] for i in range(0, len(sel_names), 2)]
        for gi, group in enumerate(name_groups):
            nc = len(group)
            col_w = (W - PAD*2 - LBL_W) // nc
            if gi > 0: y += 16
            y = draw_section_bar(y, f"  운임 비교표 ({gi+1}/{len(name_groups)})" if len(name_groups)>1 else "  운임 비교표")

            d.rectangle([PAD, y, W-PAD, y+RH+10], fill='#1e3a8a')
            d.rectangle([PAD, y, W-PAD, y+RH+10], outline=BDR, width=1)
            d.text((PAD+20, y+18), "구분", font=fnt(32, bold=True), fill='#aabbdd')
            for i, name in enumerate(group):
                cx = PAD+LBL_W+i*col_w
                color, _ = CC_TBL.get(name, ('#333','#fff'))
                d.rectangle([cx, y, cx+col_w-1, y+RH+10], fill=color)
                d.rectangle([cx, y, cx+col_w-1, y+RH+10], outline=BDR, width=1)
                d.text((cx+18, y+18), pdf_disp(name), font=fnt(32, bold=True), fill='white')
            y += RH+10

            all_pdf_sur_names = []
            for pn in group:
                for s_nm in results.get(pn,{}).get("surs_detail",{}).keys():
                    if s_nm not in all_pdf_sur_names:
                        all_pdf_sur_names.append(s_nm)

            rdefs = [
                ("항공운임", lambda r: r.get("pub_disc",0), False, False),
                ("  └ 단가/kg", lambda r: r.get("disc_rpk") or r.get("rpk") or 0, False, True),
            ]
            for s_nm in all_pdf_sur_names:
                rdefs.append((f"  {s_nm}", lambda r, n=s_nm: r.get("surs_detail",{}).get(n,0), False, True))
            if len(all_pdf_sur_names) >= 2:
                rdefs.append(("부가서비스 소계", lambda r: r.get("sur_total",0), False, False))
            rdefs += [
                ("유류할증료",  lambda r: r.get("pub_fuel",0)+r.get("sur_fuel_pub",0), False, False),
                ("청구가 합계", lambda r: r.get("total_quote",0), True, False),
            ]
            for ri2, (label, vfn, is_hl, is_indent) in enumerate(rdefs):
                rh_row = RH-14 if is_indent else RH
                bg = '#dbeafe' if is_hl else ('#f4f6fb' if is_indent else ('#f0f4fa' if ri2%2==0 else '#ffffff'))
                d.rectangle([PAD, y, W-PAD, y+rh_row], fill=bg)
                d.rectangle([PAD, y, W-PAD, y+rh_row], outline=BDR, width=1)
                lpad = PAD+46 if is_indent else PAD+20
                fs   = 26 if is_indent else 32
                fc   = '#94a3b8' if is_indent else ('#334155' if not is_hl else '#1e40af')
                d.text((lpad, y+(10 if is_indent else 16)), label.strip(), font=fnt(fs, bold=is_hl), fill=fc)
                for i, name in enumerate(group):
                    r = results.get(name, {})
                    color, _ = CC_TBL.get(name, ('#333','#fff'))
                    cx = PAD+LBL_W+i*col_w
                    d.line([cx, y, cx, y+rh_row], fill=BDR, width=1)
                    if r.get("no_service"):
                        ra("서비스불가", fnt(26, bold=False), cx+col_w-18, y+(10 if is_indent else 16), '#b91c1c')
                        continue
                    if "__freight__" in r.get("surs_detail",{}):
                        ra("Freight전환", fnt(26, bold=False), cx+col_w-18, y+(10 if is_indent else 16), '#c2410c')
                        continue
                    v = vfn(r)
                    _is_rpk_lbl = label.strip().startswith("└ 단가/kg")
                    if _is_rpk_lbl:
                        val_str = (f"{int(v):,}원/kg" if v and v > 0 else "-")
                    else:
                        val_str = fmt(v) if v != 0 else "-"
                    txt_c = '#aabbcc' if is_indent and v==0 else (color if is_hl else ('#99aabb' if is_indent else '#2a3a4a'))
                    ra(val_str, fnt(fs, bold=is_hl), cx+col_w-18, y+(10 if is_indent else 16), txt_c)
                y += rh_row

            d.rectangle([PAD, y, W-PAD, y+RH], fill='#dbeafe')
            d.rectangle([PAD, y, W-PAD, y+RH], outline=BDR, width=1)
            d.text((PAD+20, y+16), "T/T (예상)", font=fnt(32, bold=True), fill='#1e40af')
            for i, name in enumerate(group):
                cx = PAD+LBL_W+i*col_w
                d.line([cx, y, cx, y+RH], fill=BDR, width=1)
                d.text((cx+18, y+16), TT.get(name,"-"), font=fnt(32), fill='#2563eb')
            y += RH + 18

        # 최저 견적 추천 생략 (요청에 따라 제거)
        pass

    # ─────────────────────────────────
    # REMARK
    # ─────────────────────────────────
    y += 10
    y = draw_section_bar(y, "  REMARK")

    remarks = [
        "■ 상기 견적 외에 발생되는 추가 비용(관세, 부가세, 수입제세금, 통관비, 현지 제반 비용 등)은 실비로 청구됩니다.",
        "■ 항공사 스케줄 변동 및 통관 지연으로 인해 예상 도착일보다 추가 지연이 발생될 수 있으며,",
        "   이에 따른 책임은 당사가 부담하지 않습니다.",
        "■ 현지 통관 및 세관 이슈(금지품목, 서류 미비 등)로 인해 자동 반송이 발생할 수 있으며,",
        "   반송 시 수입운임 및 현지 발생 비용은 전적으로 발송자 부담입니다.",
        "■ 유류할증료는 항공사 및 운송사 정책에 따라 매주/매월 변동되며, 실제 발송일 기준으로 적용됩니다.",
        "■ 외곽지역(도서·산간) 배송 시 지역 추가요금(RAS/ODA)이 별도 부과될 수 있습니다.",
        "■ C/T당 실중량 25kg 초과 시 비규격 화물로 분류되어 추가비용이 발생될 수 있습니다.",
        "■ 본 견적서의 유효기간은 발행일로부터 7일입니다.",
    ]
    if notes.strip():
        remarks.append(f"■ 특이사항: {notes.strip()}")

    REM_LINE_H = 46
    rem_box_h  = len(remarks)*REM_LINE_H + 30
    d.rectangle([PAD, y, W-PAD, y+rem_box_h], fill='#f8faff', outline='#dbeafe', width=2)
    for note in remarks:
        d.text((PAD+28, y+14), note, font=fnt(26), fill='#445566')
        y += REM_LINE_H
    y += 42

    # ─────────────────────────────────
    # 푸터
    # ─────────────────────────────────
    footer_top = max(y + 16, H - 150)
    d.rectangle([0, footer_top, W, H], fill='#1e3a8a')
    d.line([0, footer_top, W, footer_top], fill='#3b82f6', width=4)

    kr_logo_p = os.path.join(base_dir, "logo_kr.png")
    if os.path.exists(kr_logo_p):
        try:
            kr = Image.open(kr_logo_p).convert("RGBA")
            lw, lh = kr.size
            th2 = 54; tw2 = int(lw*th2/lh)
            kr  = kr.resize((tw2, th2), Image.LANCZOS)
            bg2 = Image.new("RGBA", kr.size, (26,26,62,255))
            kr_rgb = Image.alpha_composite(bg2, kr).convert("RGB")
            paste_y = footer_top + (H - footer_top - th2)//2
            img.paste(kr_rgb, (PAD, paste_y))
        except: pass

    ra("본 견적서는 에어브리지 운임계산기에서 자동 생성되었습니다.", fnt(26), W-PAD, footer_top+30,  '#93c5fd')
    ra(f"발행일: {datetime.now().strftime('%Y.%m.%d  %H:%M')}",     fnt(26), W-PAD, footer_top+72, '#445577')

    buf = io.BytesIO()
    img.save(buf, format='PDF', resolution=200)
    buf.seek(0)
    return buf.read()

# ═══════════════════════════════════════════════════


def generate_pdf(quote_num, result, customer, staff, selected, **kwargs):
    """Flask /api/pdf 래퍼 — result dict에서 파라미터 추출 후 _generate_pdf_core 호출"""
    from calculator import COUNTRY_KR
    dest     = result.get('dest_country', 'Germany')
    dest_kr  = result.get('dest_kr', dest)
    dhl_z    = result.get('dhl_zone', '—')
    fx_z     = result.get('fx_zone', '—')
    ups_z    = result.get('ups_zone', '—')
    zone_label = f"Z{dhl_z}/Z{fx_z}/Z{ups_z}"
    carriers   = result.get('carriers', {})

    # selected = ['dhl','fedex','ups2f'] 등 → carriers dict 필터
    sel_results = {k: v for k, v in carriers.items() if k in (selected or list(carriers.keys()))}

    disc_map = {k: v.get('disc_pct', 0) for k, v in carriers.items()}

    ct_data   = kwargs.get('ct_data', result.get('ct_data', []))
    ct_count  = result.get('ct_count', len(ct_data) if ct_data else 1)

    return _generate_pdf_core(
        quote_num     = quote_num,
        customer      = customer,
        dest_country  = dest,
        zone_label    = zone_label,
        ct_count      = ct_count,
        total_chargeable = result.get('total_chargeable', 0),
        fuel_dhl      = kwargs.get('fuel_dhl', 28.75),
        fuel_fedex    = kwargs.get('fuel_fedex', 29.75),
        fuel_ups      = kwargs.get('fuel_ups', 29.50),
        selected      = list(sel_results.keys()),
        results       = sel_results,
        disc_map      = disc_map,
        notes         = kwargs.get('notes', ''),
        our_company   = "(주)에어브리지",
        our_contact   = staff or '—',
        our_phone     = "032-502-1880",
        our_email     = "cs@airos.co.kr",
        ct_data       = ct_data,
        total_actual_wt = result.get('total_actual_wt', 0),
        is_doc        = result.get('is_doc', False),
        mode          = result.get('mode', '수출'),
    )
