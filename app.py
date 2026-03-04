import streamlit as st
import pandas as pd
import math
import io
import os
import base64
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════
# 설정값 영구 저장 / 불러오기
# ═══════════════════════════════════════════════════
# ═══════════════════════════════════════════════════
# [프로그래머A 재작성] 설정 영구 저장 — 안전한 다중 경로 fallback
# ═══════════════════════════════════════════════════
_PERSIST_KEYS = [
    "fuel_dhl", "fuel_fedex", "fuel_ups",
    "disc_dhl", "disc_fedex", "disc_fedex_e", "disc_ups",
    "tgt_margin",
    "imp_disc_ups_b8",   # 수입 전용: UPS B8733R 할인율
]

def _get_settings_path():
    """저장 경로를 3단계 fallback으로 탐색"""
    candidates = []
    # 1순위: 스크립트 파일과 동일 디렉토리
    try:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json"))
    except Exception:
        pass
    # 2순위: 현재 작업 디렉토리
    candidates.append(os.path.join(os.getcwd(), "airbridge_settings.json"))
    # 3순위: 사용자 홈 디렉토리
    candidates.append(os.path.join(os.path.expanduser("~"), "airbridge_settings.json"))
    for path in candidates:
        try:
            dirpath = os.path.dirname(path)
            if os.path.isdir(dirpath) and os.access(dirpath, os.W_OK):
                return path
        except Exception:
            continue
    return candidates[-1]

_SETTINGS_FILE = _get_settings_path()

def _load_settings():
    """저장된 설정 파일 로드 — 실패 시 빈 dict 반환"""
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k: v for k, v in data.items() if k in _PERSIST_KEYS}
    except Exception:
        pass
    return {}

def _save_settings():
    """현재 session_state의 설정값을 즉시 파일에 저장"""
    try:
        data = {k: float(st.session_state[k]) for k in _PERSIST_KEYS if k in st.session_state}
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _save_if_changed():
    """렌더 시점에 값 변경 여부를 확인하여 자동 저장 (on_change 보완)"""
    current = {k: float(st.session_state.get(k, 0)) for k in _PERSIST_KEYS if k in st.session_state}
    if current != st.session_state.get("__last_saved__", {}):
        _save_settings()
        st.session_state["__last_saved__"] = current.copy()

_SAVED = _load_settings()  # 앱 시작 시 1회 로드

st.set_page_config(
    page_title="에어브리지 운임계산기",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 로고 base64 (앱 배너용) ──
def _load_logo_b64(filename, mime="image/jpeg"):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
    return None

_LOGO_EN_B64 = _load_logo_b64("logo_en.jpg", "image/jpeg")
_LOGO_KR_B64 = _load_logo_b64("logo_kr.png",  "image/png")

# ─────────────── CSS ───────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* ── 메인 배경 — 수출: 파랑, 수입: rose (JS로 동적 전환) ── */
.stApp { background: linear-gradient(160deg,#f0f4ff 0%,#e8eeff 40%,#f4f7ff 100%); color:#1e293b; }
.stApp.mode-imp { background: linear-gradient(160deg,#f0fdfa 0%,#d5f5ed 40%,#f0fdf9 100%) !important; }

/* ══════════════════════════════════════════════════════
   Windows 11 Fluent Design — 수출 테마 (딥 네이비 블루)
   ══════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b3e 0%, #112248 50%, #0f1e3d 100%) !important;
    border-right: 2px solid #1e3a8a;
    box-shadow: 4px 0 24px rgba(0,0,0,.35);
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] label {
    color: #93c5fd !important; font-size:0.70rem !important;
    font-weight:700 !important; text-transform:uppercase;
    letter-spacing:.09em; margin-bottom:2px !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid #2d4a8a !important;
    color: #000000 !important; border-radius: 7px !important;
}
section[data-testid="stSidebar"] input:focus,
section[data-testid="stSidebar"] textarea:focus {
    border: 1px solid #60a5fa !important;
    box-shadow: 0 0 0 2px rgba(96,165,250,.25) !important;
    background: rgba(255,255,255,0.95) !important;
    color: #000000 !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid #2d4a8a !important; border-radius: 7px !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] span { color:#e2e8f0 !important; }
section[data-testid="stSidebar"] hr { border-color: #1e3a8a !important; opacity:.6; }
section[data-testid="stSidebar"] strong { color:#93c5fd !important; }
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {
    background: rgba(255,255,255,0.08) !important;
    border-color: #2d4a8a !important; color: #93c5fd !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 { color:#60a5fa !important; }
section[data-testid="stSidebar"] .stMarkdown p { color:#94a3b8 !important; }
section[data-testid="stSidebar"] ::-webkit-scrollbar { width:5px; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-track { background:transparent; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background:#2d4a8a; border-radius:3px; }

/* ══════════════════════════════════════════════════════
   Windows 11 Fluent Design — 수입 테마 Deep Rose/Crimson
   · Acrylic 소재: 반투명 레이어 + 깊이감 (Reveal Highlight)
   · 수출 딥블루(#0d1b3e) <-> 수입 딥로즈(#2d0a14) 색상환 180° 대비
   · Rose-950(#2d0a14) -> Rose-900(#3d1020) -> Rose-600(#e11d48)
   ══════════════════════════════════════════════════════ */

/* 메인 배경 */
.stApp.mode-imp {
    background: linear-gradient(160deg, #fff1f2 0%, #ffe4e6 40%, #fff1f2 100%) !important;
}
/* 배너 헤더 */
.stApp.mode-imp .banner {
    background: linear-gradient(135deg, #4c0519 0%, #9f1239 50%, #e11d48 100%) !important;
    box-shadow: 0 8px 32px rgba(225,29,72,.28) !important;
    border: 1px solid rgba(255,255,255,.20) !important;
}
/* 비교표 헤더 */
.stApp.mode-imp .compare-table th {
    background: linear-gradient(135deg, #4c0519, #9f1239) !important;
}
.stApp.mode-imp .compare-table tr:nth-child(even) td { background: #fff1f2; }
/* 일반 버튼 */
.stApp.mode-imp .stButton > button {
    background: linear-gradient(135deg, #9f1239, #e11d48) !important;
    box-shadow: 0 3px 14px rgba(225,29,72,.28) !important;
}
.stApp.mode-imp .stButton > button:hover {
    background: linear-gradient(135deg, #e11d48, #fb7185) !important;
    box-shadow: 0 6px 22px rgba(225,29,72,.38) !important;
}
.stApp.mode-imp .pdf-btn > button {
    background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
    box-shadow: 0 3px 14px rgba(220,38,38,.3) !important;
}
.stApp.mode-imp .pdf-btn > button:hover {
    background: linear-gradient(135deg, #ef4444, #dc2626) !important;
}
.stApp.mode-imp .mbox { border-color: #fda4af; }

/* ── 수입 사이드바 전체 Windows Fluent Rose 테마 ── */
.stApp.mode-imp section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2d0a14 0%, #3d1020 50%, #2a0916 100%) !important;
    border-right: 2px solid #9f1239 !important;
    box-shadow: 4px 0 24px rgba(159,18,57,.45) !important;
}
/* 레이블 Rose-300 */
.stApp.mode-imp section[data-testid="stSidebar"] label { color: #fda4af !important; }
/* 입력박스 */
.stApp.mode-imp section[data-testid="stSidebar"] input,
.stApp.mode-imp section[data-testid="stSidebar"] textarea {
    border: 1px solid #7f1d3a !important;
}
.stApp.mode-imp section[data-testid="stSidebar"] input:focus,
.stApp.mode-imp section[data-testid="stSidebar"] textarea:focus {
    border: 1px solid #fb7185 !important;
    box-shadow: 0 0 0 2px rgba(251,113,133,.25) !important;
}
/* selectbox */
.stApp.mode-imp section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    border: 1px solid #7f1d3a !important;
}
/* hr / strong / number btn */
.stApp.mode-imp section[data-testid="stSidebar"] hr { border-color: #9f1239 !important; }
.stApp.mode-imp section[data-testid="stSidebar"] strong { color: #fda4af !important; }
.stApp.mode-imp section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {
    border-color: #7f1d3a !important; color: #fda4af !important;
}
/* h3 / scrollbar */
.stApp.mode-imp section[data-testid="stSidebar"] .stMarkdown h3 { color:#fb7185 !important; }
.stApp.mode-imp section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
    background: #7f1d3a !important;
}
/* 사이드바 버튼 전체 Rose */
.stApp.mode-imp section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #9f1239, #e11d48) !important;
    box-shadow: 0 3px 14px rgba(225,29,72,.28) !important;
}
.stApp.mode-imp section[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #e11d48, #fb7185) !important;
    box-shadow: 0 5px 18px rgba(225,29,72,.38) !important;
}

/* ── 배너: 밝은 인디고-블루 그라데이션 ── */
.banner {
    border-radius:16px; padding:28px 36px; margin-bottom:22px;
    background: linear-gradient(135deg,#1e3a8a 0%,#2563eb 60%,#3b82f6 100%);
    border:1px solid rgba(255,255,255,.25);
    box-shadow: 0 8px 32px rgba(37,99,235,.25);
    display:flex; justify-content:space-between; align-items:center;
}
.banner-title { font-size:2.4rem; font-weight:900; color:#ffffff; margin:0; text-shadow: 0 2px 8px rgba(0,0,0,.18); }
.banner-sub { font-size:1.0rem; color:#bfdbfe; margin-top:6px; font-weight:500; }

/* ══════════════════════════════════════════
   방향 B — 운송사 카드: 계층적 시각 강조
   ══════════════════════════════════════════ */
.carrier-card {
    border-radius:18px; padding:26px;
    background: #ffffff;
    box-shadow: 0 2px 12px rgba(37,99,235,.07), 0 1px 4px rgba(0,0,0,.04);
    border: 1px solid #e8eef8;
    position:relative; overflow:hidden;
    height:100%; box-sizing:border-box;
    display:flex; flex-direction:column;
    transition: box-shadow .2s, transform .2s, opacity .2s;
    opacity: 0.82;   /* ← 기본: 약간 후퇴 */
}
.carrier-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:5px;
}
.carrier-card.dhl::before  { background:#D40511; }
.carrier-card.fedex::before{ background:#4D148C; }
.carrier-card.ups::before  { background:#92400e; }
.carrier-card.disabled { opacity:.35; filter:grayscale(.7); pointer-events:none; }



/* Streamlit 컬럼 내부를 stretch로 — 카드 높이 균등 */
[data-testid="column"] > div { height:100%; }
[data-testid="column"] > div > div { height:100%; }
[data-testid="stVerticalBlock"] > div > div { height:100%; }

/* ── 뱃지 ── */
.carrier-badge { font-size:.7rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; padding:2px 10px; border-radius:20px; display:inline-block; margin-bottom:8px; }
.badge-dhl   { background:#fff0f0; color:#b91c1c; border:1px solid #fca5a5; }
.badge-fedex { background:#f3f0ff; color:#6d28d9; border:1px solid #c4b5fd; }
.badge-ups   { background:#fff7ed; color:#92400e; border:1px solid #fdba74; }
.badge-best  {
    background:linear-gradient(135deg,#1d4ed8,#2563eb);
    color:white; float:right; font-size:.68rem; border:none;
    padding:3px 12px; letter-spacing:.06em;
    box-shadow: 0 2px 8px rgba(37,99,235,.35);
}

/* ── 운임 숫자 계층: 3단계 ── */
/* 1단계: 총 청구금액 — 가장 크고 강하게 */
.carrier-quote {
    font-family:'JetBrains Mono',monospace;
    font-size:2.15rem; font-weight:700;
    margin:8px 0 4px; line-height:1.1;
    letter-spacing:-.02em;
}
/* 2단계: 원가 — 중간 */
.carrier-cost  { font-family:'JetBrains Mono',monospace; font-size:.95rem; color:#64748b; }
/* 3단계: 기타 정보 — 작게 */
.carrier-margin{ font-size:1rem; font-weight:700; margin-top:4px; }

.breakdown-row {
    display:flex; justify-content:space-between;
    padding:5px 0; border-bottom:1px solid rgba(0,0,0,.05);
    font-size:.78rem;
}
.breakdown-row:last-child { border:none; }
.bd-label { color:#64748b; }
.bd-cost  { font-family:'JetBrains Mono',monospace; color:#1e293b; }

/* ── 비교 요약 테이블 ── */
.compare-table {
    background:white; border-radius:14px;
    box-shadow: 0 2px 16px rgba(37,99,235,.08);
    overflow:hidden; margin-bottom:16px;
    border: 1px solid #e2e8f8;
}
.compare-table th {
    background: linear-gradient(135deg,#1e3a8a,#2563eb);
    color:white;
    font-size:.72rem; font-weight:700;
    text-transform:uppercase; letter-spacing:.07em;
    padding:11px 14px;
}
.compare-table td { padding:9px 14px; font-size:.82rem; border-bottom:1px solid #eef2ff; color:#334155; }
.compare-table tr:last-child td { border:none; }
.compare-table tr:nth-child(even) td { background:#f8faff; }
.td-label { color:#475569; font-weight:600; }
.td-dhl   { font-family:'JetBrains Mono',monospace; color:#dc2626; font-weight:700; }
.td-fedex { font-family:'JetBrains Mono',monospace; color:#7c3aed; font-weight:700; }
.td-ups   { font-family:'JetBrains Mono',monospace; color:#92400e; font-weight:700; }
.td-hl    { font-weight:700 !important; }

/* ── 알림 ── */
.alert { border-radius:10px; padding:9px 14px; font-size:.8rem; font-weight:600; margin:4px 0; }
.alert-ok   { background:#ecfdf5; border:1px solid #6ee7b7; color:#065f46; }
.alert-warn { background:#fffbeb; border:1px solid #fcd34d; color:#92400e; }
.alert-bad  { background:#fff1f2; border:1px solid #fca5a5; color:#9f1239; }

/* ── 사이드바 수출/수입 버튼: 고대비 특별 스타일 ── */
section[data-testid="stSidebar"] .stButton>button {
    background: rgba(255,255,255,0.08) !important;
    border: 1.5px solid rgba(96,165,250,0.4) !important;
    color: #cbd5e1 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    transition: all 0.15s ease;
}
section[data-testid="stSidebar"] .stButton>button:hover {
    background: rgba(96,165,250,0.2) !important;
    border-color: #60a5fa !important;
    color: #ffffff !important;
}
section[data-testid="stSidebar"] .stButton>button[kind="primary"] {
    background: linear-gradient(135deg,#1d4ed8,#2563eb) !important;
    border-color: #3b82f6 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(37,99,235,.4) !important;
}
/* ── 버튼: 밝은 인디고 블루 ── */
.stButton>button {
    background: linear-gradient(135deg,#1e3a8a,#2563eb) !important;
    color:white !important; border:none !important; border-radius:10px !important;
    font-weight:700 !important; padding:.55rem 1.4rem !important;
    box-shadow: 0 3px 14px rgba(37,99,235,.28) !important;
    transition: all .18s ease !important;
}
.stButton>button:hover {
    background: linear-gradient(135deg,#2563eb,#3b82f6) !important;
    transform:translateY(-1px) !important;
    box-shadow: 0 6px 22px rgba(37,99,235,.38) !important;
}

.pdf-btn>button {
    background: linear-gradient(135deg,#dc2626,#b91c1c) !important;
    box-shadow: 0 3px 14px rgba(220,38,38,.3) !important;
}
.pdf-btn>button:hover {
    background: linear-gradient(135deg,#ef4444,#dc2626) !important;
    box-shadow: 0 6px 22px rgba(220,38,38,.4) !important;
}

/* ══════════════════════════════════════════════════════
   수출/수입 위젯 show/hide — Streamlit 실제 구조 대응
   Streamlit은 label을 포함한 자체 div 구조를 사용하므로
   [data-testid] 부모를 직접 숨겨야 함
   JS가 sidebar 안의 위젯 container에 클래스를 동적으로 부여
   ══════════════════════════════════════════════════════ */
.sb-exp-widget { display:block !important; }
.sb-imp-widget { display:none  !important; }
section[data-testid="stSidebar"].mode-is-imp .sb-exp-widget { display:none  !important; }
section[data-testid="stSidebar"].mode-is-imp .sb-imp-widget { display:block !important; }
section[data-testid="stSidebar"].mode-is-imp .sb-exp-header { display:none  !important; }
section[data-testid="stSidebar"]:not(.mode-is-imp) .sb-imp-header { display:none !important; }

/* ── 상단 요약 카드 (mbox) — 방향 B: 핵심 4개 + 스타일 강화 ── */
.mbox {
    background: #ffffff;
    border: 1px solid #e2e8f8;
    border-radius:14px; padding:16px 14px; text-align:center;
    box-shadow: 0 2px 12px rgba(37,99,235,.07);
    transition: transform .15s;
}
.mbox:hover { transform:translateY(-1px); }
.mbox-lbl { font-size:.72rem; color:#64748b; text-transform:uppercase; letter-spacing:.08em; font-weight:700; margin-bottom:6px; }
.mbox-val { font-family:'JetBrains Mono',monospace; font-size:1.45rem; font-weight:700; }
.mbox-sub { font-size:.75rem; color:#94a3b8; margin-top:5px; }


</style>
<script>
(function() {
  // ── React native input setter ──
  function reactSet(el, val) {
    var ns = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
    if (ns && ns.set) {
      ns.set.call(el, val);
      el.dispatchEvent(new Event('input',  { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  // ── 사이드바 모든 입력값 강제 커밋 (blur) ──
  function flushAllInputs(cb) {
    var sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) { if (cb) cb(); return; }
    var inputs = sidebar.querySelectorAll('input[type="number"], input[type="text"]');
    inputs.forEach(function(inp) {
      if (document.activeElement === inp) {
        inp.blur();
        inp.dispatchEvent(new Event('blur',   { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    // React 처리 대기 후 콜백
    setTimeout(function() { if (cb) cb(); }, 180);
  }

  // ── 모드 버튼 클릭 인터셉트: blur 먼저, 그 다음 버튼 클릭 ──
  function hookModeButtons() {
    var sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) return;
    sidebar.querySelectorAll('button').forEach(function(btn) {
      var txt = btn.textContent.trim();
      if ((txt.includes('수  출') || txt.includes('수출') ||
           txt.includes('수  입') || txt.includes('수입')) &&
          !btn.dataset._hooked) {
        btn.dataset._hooked = '1';
        btn.addEventListener('click', function(e) {
          if (btn.dataset._flushed) {
            delete btn.dataset._flushed;
            return; // 이미 flush 완료, 정상 클릭 처리
          }
          e.preventDefault();
          e.stopImmediatePropagation();
          flushAllInputs(function() {
            btn.dataset._flushed = '1';
            btn.click(); // flush 후 재클릭
          });
        }, true); // capture phase: Streamlit보다 먼저 처리
      }
    });
  }

  // ── 위젯 컨테이너 show/hide (실제 Streamlit div 구조 사용) ──
  function applyModeVisibility() {
    var sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) return;
    var marker = sidebar.querySelector('[data-airbridge-mode]');
    if (!marker) return;
    var isImp = marker.getAttribute('data-airbridge-mode') === 'imp';

    // ── stApp 테마 클래스 토글 (수입: rose, 수출: blue) ──
    var app = document.querySelector('.stApp');
    if (app) {
      if (isImp) { app.classList.add('mode-imp'); }
      else       { app.classList.remove('mode-imp'); }
    }

    // mode-is-imp 클래스 토글
    if (isImp) {
      sidebar.classList.add('mode-is-imp');
    } else {
      sidebar.classList.remove('mode-is-imp');
    }

    // 위젯 컨테이너 찾아서 클래스 부여
    // Streamlit: label 텍스트를 기준으로 부모 block-container 식별
    sidebar.querySelectorAll('[data-testid="stNumberInput"], [data-testid="stMarkdown"]').forEach(function(el) {
      var label = el.querySelector('label, p');
      if (!label) return;
      var txt = label.textContent.trim();
      var parent = el.closest('[data-testid="stVerticalBlock"]') || el.parentElement;
      // data-sb-group 속성으로 이미 표시된 경우 스킵
    });

    // 가장 신뢰할 수 있는 방법: marker 주변 sibling 탐색
    // 수출 섹션 header (span.sb-exp-header 마커)와 수입 섹션 header를 기준으로
    // 해당 영역의 stElement들을 찾아 클래스 부여
    var allBlocks = sidebar.querySelectorAll('[data-testid="stVerticalBlock"] > div');
    var inExpSection = false, inImpSection = false;
    allBlocks.forEach(function(block) {
      var txt = block.textContent;
      if (txt.includes('유류할증료 — 수출') || txt.includes('할인율 — 수출')) {
        inExpSection = true; inImpSection = false;
        block.classList.add('sb-exp-widget');
        block.classList.remove('sb-imp-widget');
      } else if (txt.includes('유류할증료 — 수입') || txt.includes('할인율 — 수입')) {
        inImpSection = true; inExpSection = false;
        block.classList.add('sb-imp-widget');
        block.classList.remove('sb-exp-widget');
      }
    });
  }

  // ── Selectbox 클릭 즉시 내용 지우기 ──
  function hookSelectboxes() {
    document.querySelectorAll('[data-baseweb="select"]').forEach(function(wrap) {
      if (wrap.dataset._sc) return;
      wrap.dataset._sc = '1';
      function clearInput() {
        var inp = wrap.querySelector('input');
        if (!inp) return;
        reactSet(inp, '');
        setTimeout(function() {
          if (inp.value !== '') reactSet(inp, '');
          inp.focus();
        }, 30);
      }
      wrap.addEventListener('mousedown', clearInput, true);
      var inp = wrap.querySelector('input');
      if (inp) {
        inp.addEventListener('focus', function() {
          setTimeout(function() { reactSet(inp, ''); }, 50);
        });
      }
    });
  }

  // ── 일반 input: 포커스 시 전체 선택 ──
  function hookNumberInputs() {
    document.querySelectorAll('input[type="number"]').forEach(function(el) {
      if (el.closest('[data-baseweb="select"]')) return;
      if (el.dataset._sa) return;
      el.dataset._sa = '1';
      el.addEventListener('focus', function() { this.select(); });
      el.addEventListener('mouseup', function(e) { e.preventDefault(); });
    });
  }

  function run() {
    hookModeButtons();
    applyModeVisibility();
    hookSelectboxes();
    hookNumberInputs();
  }

  document.addEventListener('DOMContentLoaded', run);
  var obs = new MutationObserver(run);
  obs.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# 데이터: DHL
# ═══════════════════════════════════════════════════
DHL_ZONE_MAP = {
    "Albania":7,"Algeria":8,"American Samoa":8,"Andorra":6,"Angola":8,"Argentina":8,
    "Armenia":8,"Australia":4,"Austria":6,"Azerbaijan":8,"Bahamas":8,"Bahrain":7,
    "Bangladesh":4,"Belarus":8,"Belgium":6,"Belize":8,"Benin":8,"Bhutan":8,"Bolivia":8,
    "Brazil":8,"Brunei":3,"Bulgaria":6,"Burkina Faso":8,"Burundi":8,"Cambodia":3,
    "Cameroon":8,"Canada":5,"Chile":8,"China (People's Republic)":1,"Colombia":8,
    "Costa Rica":8,"Croatia":6,"Cuba":8,"Cyprus":6,"Czech Republic":6,"Denmark":6,
    "Dominican Republic":8,"Ecuador":8,"Egypt":8,"El Salvador":8,"Estonia":6,
    "Ethiopia":8,"Fiji":8,"Finland":6,"France":6,"Gabon":8,"Georgia":8,"Germany":6,
    "Ghana":8,"Greece":6,"Guatemala":8,"Guinea":8,"Haiti":8,"Honduras":8,
    "Hong Kong SAR China":1,"Hungary":6,"Iceland":8,"India":4,"Indonesia":3,
    "Iran, Islamic Rep. of":8,"Iraq":8,
    "Ireland":6,"Israel":7,"Italy":6,"Jamaica":8,"Japan":2,"Jordan":8,"Kazakhstan":8,
    "Kenya":8,"Kuwait":7,"Lao P.D.R.":3,"Latvia":6,"Lebanon":8,"Liechtenstein":6,
    "Lithuania":6,"Luxembourg":6,"Macau SAR China":1,"Madagascar":8,"Malaysia":3,
    "Maldives":8,"Malta":6,"Martinique":8,"Mauritius":8,"Mexico":5,"Moldova":8,
    "Monaco":6,"Mongolia":8,"Montenegro":7,"Morocco":8,"Mozambique":8,"Myanmar":3,
    "Namibia":8,"Nepal":8,"Netherlands":6,"New Zealand":4,"Nicaragua":8,"Niger":8,
    "Nigeria":8,"Norway":6,"Oman":7,"Pakistan":4,"Panama":8,"Papua New Guinea":4,
    "Paraguay":8,"Peru":8,"Philippines":3,"Poland":6,"Portugal":6,"Puerto Rico":8,
    "Qatar":7,"Romania":6,"Russia":8,"Rwanda":8,"Saudi Arabia":7,"Senegal":8,
    "Serbia":7,"Singapore":1,"Slovakia":6,"Slovenia":6,"South Africa":8,"Spain":6,
    "Sri Lanka":4,"Sudan":8,"Sweden":6,"Switzerland":6,"Syria":8,"Taiwan, China":1,
    "Tanzania":8,"Thailand":3,"Togo":8,"Trinidad and Tobago":8,"Tunisia":8,"Turkiye":7,
    "Uganda":8,"Ukraine":8,"United Arab Emirates":7,"United Kingdom":6,
    "United States of America":5,"Uruguay":8,"Uzbekistan":8,"Venezuela":8,"Vietnam":3,
    "Yemen":8,"Zambia":8,"Zimbabwe":8,
}
DHL_PUB_DOC={0.5:[59000,62200,63100,73300,75700,81900,92000,108100],1.0:[88200,88600,93900,106400,108200,132500,145900,171400],1.5:[116100,121300,128600,140400,142400,176800,197000,236500],2.0:[144000,154000,163300,174400,176600,221100,248100,301600]}
DHL_PUB_NDC={0.5:[140700,147300,148000,153600,155300,166800,175100,226900],1.0:[160300,167600,168300,175200,177100,203800,216900,275100],1.5:[170400,179700,184700,192900,194900,231900,251300,316000],2.0:[180500,191800,201100,210600,212700,260000,285700,356900],2.5:[190300,203900,217000,227200,229600,287400,319500,396100],3.0:[198100,214800,230900,243100,245500,310700,348700,432400],4.0:[213700,236600,258700,274900,277300,357300,407100,505000],5.0:[229300,258400,286500,306700,309100,403900,465500,577600],6.0:[243900,274600,311700,334500,338100,446300,519100,647400],7.0:[258500,290800,336900,362300,367100,488700,572700,717200],8.0:[273100,307000,362100,390100,396100,531100,626300,787000],9.0:[287700,323200,387300,417900,425100,573500,679900,856800],10.0:[302300,339400,412500,445700,454100,615900,733500,926600],12.0:[330300,367000,449300,490500,498100,698300,833500,1056600],14.0:[358300,394600,486100,535300,542100,780700,933500,1186600],15.0:[372300,408400,504500,557700,564100,821900,983500,1251600],16.0:[386300,422200,522900,580100,586100,863100,1033500,1316600],17.0:[400300,436000,541300,602500,608100,904300,1083500,1381600],18.0:[414300,449800,559700,624900,630100,945500,1133500,1446600],19.0:[428300,463600,578100,647300,652100,986700,1183500,1511600],20.0:[442300,477400,596500,669700,674100,1027900,1233500,1576600],22.0:[479900,518600,647700,726900,734900,1119100,1331900,1703800],24.0:[517500,559800,698900,784100,795700,1210300,1430300,1831000],25.0:[536300,580400,724500,812700,826100,1255900,1479500,1894600],27.0:[573900,621600,775700,869900,886900,1347100,1577900,2021800],29.0:[611500,662800,826900,927100,947700,1438300,1676300,2149000],30.0:[630300,683400,852500,955700,978100,1483900,1725500,2212600]}
DHL_PUB_OVER={"30.1-70":[20400,22100,27700,31900,32900,49500,55900,71600]}
DHL_NET_DOC={0.5:[15379,16216,16265,21344,21920,23266,26121,30708],1.0:[26273,26172,27896,33717,31920,39435,43423,51064],1.5:[34553,35833,38247,44364,42070,52597,58606,70486],2.0:[42833,45494,48598,55011,52220,65759,73789,89908]}
DHL_NET_NDC={0.5:[43474,45792,44950,48499,47789,51753,54414,70633],1.0:[48304,50817,50471,54511,53209,61267,65159,82609],1.5:[51065,54268,55154,59934,58038,69303,75065,94240],2.0:[53826,57719,59837,65357,62867,77339,84971,105871],2.5:[56586,61170,64521,70779,67697,85374,94876,117505],3.0:[58903,64277,68563,75660,72278,92078,103503,128250],4.0:[63537,70491,76647,85422,81440,105486,120757,149740],5.0:[68171,76705,84731,95184,90602,118894,138011,171230],6.0:[72409,81633,92125,103366,98974,131414,153979,192028],7.0:[76647,86561,99519,111548,107346,143934,169947,212826],8.0:[80885,91489,106913,119730,115718,156454,185915,233624],9.0:[85123,96417,114307,127912,124090,168974,201883,254422],10.0:[89361,101345,121701,136094,132462,181494,217851,275220],12.0:[97645,110413,132549,148722,145662,205938,248411,315636],14.0:[105929,119481,143397,161350,158862,230382,278971,356052],15.0:[110071,124015,148821,167664,165462,242604,294251,376260],16.0:[114213,128549,154245,173978,172062,254826,309531,396468],17.0:[118355,133083,159669,180292,178662,267048,324811,416676],18.0:[122497,137617,165093,186606,185262,279270,340091,436884],19.0:[126639,142151,170517,192920,191862,291492,355371,457092],20.0:[130781,146685,175941,199234,198462,303714,370651,477300],22.0:[143409,159705,192109,217170,216198,330322,402987,518308],24.0:[156037,172725,208277,235106,233934,356930,435323,559316],25.0:[162351,179235,216361,244074,242802,370234,451491,579820],27.0:[174979,192255,232529,262010,260538,396842,483827,620828],29.0:[187607,205275,248697,279946,278274,423450,516163,661836],30.0:[193921,211785,256781,288914,287142,436754,532331,682340]}
DHL_NET_OVER={"30.1-70":[6076,6524,8149,9513,9425,14425,16181,20324]}

# ── DHL 분쟁지역 배송 수수료 (KRW 50,000/건) ──
# 출처: DHL Express 2026 부가서비스 요금표
DHL_CONFLICT_COUNTRIES = {
    "Afghanistan","Burkina Faso","Congo, Dem. Rep.","Haiti","Iraq","Israel",
    "Lebanon","Libya","Mali","Somalia","Sudan","Syria","Ukraine","Venezuela",
    "Yemen","Bahrain","Kuwait","Qatar",
}
# ── DHL 무역제재국 배송 수수료 (KRW 50,000/건) ──
DHL_SANCTION_COUNTRIES = {
    "Central African Republic","Congo, Dem. Rep.","Iran, Islamic Rep. of","Iraq",
    "Korea, Dem. People's Rep. of","Libya","Somalia","Yemen",
    # 법률 적용 대상국
    "Afghanistan","Belarus","Lebanon","Myanmar","Russia","Zimbabwe",
}
DHL_CONFLICT_SUR  = 50000   # 분쟁지역 수수료 (발송건당)
DHL_SANCTION_SUR  = 50000   # 무역제재국 수수료 (발송건당)

# ═══════════════════════════════════════════════════
# 데이터: FedEx
# ═══════════════════════════════════════════════════
FEDEX_ZONES=["A","B","C","D","E","F","G","H","I","J"]
# ── FedEx 2026 지역구분표 (한국 출발 수출 기준, IP 서비스 영문 국가명 직접 매핑) ──
FEDEX_ZONE_MAP_EN = {
    # Zone A
    "Hong Kong SAR China":"A","Taiwan, China":"A","Macau SAR China":"A","Singapore":"A",
    "China (People's Republic)":"A",  # South: A, others: C — 코드상 단순화: 남부 별도 처리 없음
    # Zone B
    "Japan":"B",
    # Zone C
    "Indonesia":"C","Malaysia":"C","Philippines":"C","Thailand":"C","Vietnam":"C",
    # Zone D
    "Brunei":"D","Cambodia":"D","Guam":"D","India":"D","Lao P.D.R.":"D","Mongolia":"D","Myanmar":"D",
    # Zone E (US West Coast)  — 현재 앱은 US 단일 취급
    # Zone F
    "Australia":"F","Canada":"F","Mexico":"F","New Zealand":"F","Puerto Rico":"F",
    "United States of America":"F",
    # Zone G (서유럽)
    "Andorra":"G","Austria":"G","Belgium":"G","Bulgaria":"G","Canary Islands":"G",
    "Czech Republic":"G","Denmark":"G","Estonia":"G","Faroe Islands":"G","Finland":"G",
    "France":"G","Germany":"G","Greece":"G","Greenland":"G","Hungary":"G","Ireland":"G",
    "Italy":"G","Latvia":"G","Liechtenstein":"G","Lithuania":"G","Luxembourg":"G",
    "Malta":"G","Monaco":"G","Netherlands":"G","Norway":"G","Poland":"G","Portugal":"G",
    "Romania":"G","San Marino":"G","Slovakia":"G","Spain":"G","Sweden":"G","Switzerland":"G",
    "United Kingdom":"G","Vatican City":"G",
    # Zone H (동유럽/중앙아시아/기타 유럽)
    "Albania":"H","Armenia":"H","Azerbaijan":"H","Belarus":"H","Bosnia and Herzegovina":"H",
    "Croatia":"H","Cyprus":"H","Georgia":"H","Gibraltar":"H","Iceland":"H","Israel":"H",
    "Kazakhstan":"H","Kosovo":"H","Kyrgyzstan":"H","Moldova":"H","Montenegro":"H",
    "Russia":"H","Serbia":"H","Slovenia":"H","Turkiye":"H","Ukraine":"H","Uzbekistan":"H",
    # Zone I (중남미/카리브/태평양)
    "American Samoa":"I","Anguilla":"I","Antigua":"I","Argentina":"I","Aruba":"I",
    "Bahamas":"I","Barbados":"I","Belize":"I","Bermuda":"I","Bolivia":"I","Bonaire":"I",
    "Brazil":"I","British Virgin Islands":"I","Cayman Islands":"I","Chile":"I",
    "Colombia":"I","Cook Islands":"I","Costa Rica":"I","Cuba":"I","Curacao":"I",
    "Dominica":"I","Dominican Republic":"I","Ecuador":"I","El Salvador":"I","Fiji":"I",
    "French Guiana":"I","French Polynesia":"I","Grenada":"I","Guadeloupe":"I",
    "Guatemala":"I","Guyana":"I","Haiti":"I","Honduras":"I","Jamaica":"I",
    "Marshall Islands":"I","Martinique":"I","Micronesia":"I","Montserrat":"I",
    "New Caledonia":"I","Nicaragua":"I","Palau":"I","Panama":"I","Papua New Guinea":"I",
    "Paraguay":"I","Peru":"I","Puerto Rico":"I","Reunion":"I","Samoa":"I",
    "Solomon Islands":"I","St. Barthelemy":"I","St. Kitts":"I","St. Lucia":"I",
    "St. Maarten":"I","St. Vincent":"I","Suriname":"I","Tahiti":"I",
    "Timor-Leste":"I","Tonga":"I","Trinidad and Tobago":"I",
    "Turks and Caicos":"I","Uruguay":"I","Vanuatu":"I","Venezuela":"I",
    "Virgin Islands (US)":"I",
    # Zone J (중동/아프리카/남아시아)
    "Afghanistan":"J","Algeria":"J","Angola":"J","Bahrain":"J","Bangladesh":"J",
    "Benin":"J","Bhutan":"J","Botswana":"J","Burkina Faso":"J","Burundi":"J",
    "Cameroon":"J","Cape Verde":"J","Central African Republic":"J","Chad":"J",
    "Djibouti":"J","Egypt":"J","Eritrea":"J","Ethiopia":"J","Gabon":"J","Gambia":"J",
    "Ghana":"J","Guinea":"J","Guinea-Bissau":"J","Iran, Islamic Rep. of":"J",
    "Iraq":"J","Ivory Coast":"J","Jordan":"J","Kenya":"J","Kuwait":"J","Lebanon":"J",
    "Lesotho":"J","Liberia":"J","Libya":"J","Madagascar":"J","Malawi":"J",
    "Maldives":"J","Mali":"J","Mauritania":"J","Mauritius":"J","Morocco":"J",
    "Mozambique":"J","Namibia":"J","Nepal":"J","Niger":"J","Nigeria":"J","Oman":"J",
    "Pakistan":"J","Qatar":"J","Rwanda":"J","Saudi Arabia":"J","Senegal":"J",
    "Seychelles":"J","Sierra Leone":"J","Somalia":"J","South Africa":"J",
    "South Sudan":"J","Sri Lanka":"J","Sudan":"J","Syria":"J","Tajikistan":"J",
    "Tanzania":"J","Togo":"J","Tunisia":"J","Turkmenistan":"J","Uganda":"J",
    "United Arab Emirates":"J","Yemen":"J","Zambia":"J","Zimbabwe":"J",
}
# 하위 호환: 기존 한국어 키 FEDEX_ZONE_MAP 유지 (fallback용)
FEDEX_ZONE_MAP={
    "중국 남부 (광동/푸젠)":"A","홍콩":"A","대만":"A","마카오":"A","싱가포르":"A","일본":"B",
    "중국 (남부 제외)":"C","태국":"C","말레이시아":"C","인도네시아":"C","필리핀":"C","베트남":"C",
    "인도":"D","캄보디아":"D","몽골":"D","괌":"D","라오스":"D","브루나이":"D",
    "미국 (서부: CA/WA/OR/NV/AZ)":"E","미국 (기타 지역)":"F","캐나다":"F","호주":"F",
    "뉴질랜드":"F","멕시코":"F","푸에르토리코":"F","독일":"G","영국":"G","프랑스":"G",
    "이탈리아":"G","스페인":"G","네덜란드":"G","벨기에":"G","오스트리아":"G","스위스":"G",
    "체코":"G","덴마크":"G","핀란드":"G","그리스":"G","헝가리":"G","아일랜드":"G",
    "룩셈부르크":"G","노르웨이":"G","폴란드":"G","포르투갈":"G","스웨덴":"G",
    "러시아":"H","우크라이나":"H","루마니아":"H","터키":"H","불가리아":"H","크로아티아":"H",
    "에스토니아":"H","라트비아":"H","리투아니아":"H","몰도바":"H","세르비아":"H",
    "슬로바키아":"H","슬로베니아":"H","카자흐스탄":"H","벨라루스":"H",
    "브라질":"I","콜롬비아":"I","아르헨티나":"I","칠레":"I","페루":"I","에콰도르":"I",
    "볼리비아":"I","파라과이":"I","우루과이":"I","베네수엘라":"I","코스타리카":"I","파나마":"I",
    "과테말라":"I","온두라스":"I","니카라과":"I","엘살바도르":"I","자메이카":"I","도미니카공화국":"I",
    "아랍에미리트":"J","사우디아라비아":"J","카타르":"J","쿠웨이트":"J","바레인":"J","오만":"J",
    "요르단":"J","이집트":"J","파키스탄":"J","방글라데시":"J","스리랑카":"J","이라크":"J",
    "레바논":"J","나이지리아":"J","케냐":"J","남아프리카":"J","에티오피아":"J","탄자니아":"J",
}
# ── FedEx Envelope — 서류, 0.5kg 고정 요금 ──
FEDEX_PUB_ENV = {
    0.5:[45400,47900,47900,58600,61100,62000,67500,76000,80200,89300],
}
# ── FedEx PAK — 서류 0.5~2.5kg, 0.5단위 (서류가 0.5kg 초과 시 적용) ──
FEDEX_PUB_PAK = {
    0.5:[71600,71700,73600,81100,85000,86300,91800,97200,101700,105100],
    1.0:[89300,89100,91600,100200,110300,110900,128700,139600,145900,150000],
    1.5:[108900,109400,109700,120000,136400,137700,162400,177200,185900,192200],
    2.0:[126300,128600,130900,143600,160300,161600,192900,209300,218600,226600],
    2.5:[144600,149600,150600,165700,185800,187600,224500,243000,254100,262500],
}
# ── FedEx IP NDC — 화물, 0.5~20.5kg 0.5단위 (20.5kg 초과 → 1kg단위) ──
FEDEX_PUB_IP = {
    0.5:[125700,132200,132000,137400,142100,145500,146400,154000,163400,193300],
    1.0:[136700,145100,144700,155600,157900,160800,173300,186500,188800,222300],
    1.5:[147700,158000,157400,173800,173700,176100,200200,219000,214200,251300],
    2.0:[158700,170900,170100,192000,189500,191400,227100,251500,239600,280300],
    2.5:[169700,183800,182800,210200,205300,206700,254000,284000,265000,309300],
    3.0:[176800,193000,192300,225200,219600,221600,273600,309700,292200,341000],
    3.5:[183900,202200,201800,240200,233900,236500,293200,335400,319400,372700],
    4.0:[191000,211400,211300,255200,248200,251400,312800,361100,346600,404400],
    4.5:[198100,220600,220800,270200,262500,266300,332400,386800,373800,436100],
    5.0:[205200,229800,230300,285200,276800,281200,352000,412500,401000,467800],
    5.5:[211800,237700,238200,297400,290300,294300,371100,436100,426300,496900],
    6.0:[218400,245600,246100,309600,303800,307400,390200,459700,451600,526000],
    6.5:[225000,253500,254000,321800,317300,320500,409300,483300,476900,555100],
    7.0:[231600,261400,261900,334000,330800,333600,428400,506900,502200,584200],
    7.5:[238200,269300,269800,346200,344300,346700,447500,530500,527500,613300],
    8.0:[244800,277200,277700,358400,357800,359800,466600,554100,552800,642400],
    8.5:[251400,285100,285600,370600,371300,372900,485700,577700,578100,671500],
    9.0:[258000,293000,293500,382800,384800,386000,504800,601300,603400,700600],
    9.5:[264600,300900,301400,395000,398300,399100,523900,624900,628700,729700],
    10.0:[271200,308800,309300,407200,411800,412200,543000,648500,654000,758800],
    10.5:[276700,314200,316100,415600,421300,422600,560600,668600,671400,778500],
    11.0:[282200,319600,322900,424000,430800,433000,578200,688700,688800,798200],
    11.5:[287700,325000,329700,432400,440300,443400,595800,708800,706200,817900],
    12.0:[293200,330400,336500,440800,449800,453800,613400,728900,723600,837600],
    12.5:[298700,335800,343300,449200,459300,464200,631000,749000,741000,857300],
    13.0:[304200,341200,350100,457600,468800,474600,648600,769100,758400,877000],
    13.5:[309700,346600,356900,466000,478300,485000,666200,789200,775800,896700],
    14.0:[315200,352000,363700,474400,487800,495400,683800,809300,793200,916400],
    14.5:[320700,357400,370500,482800,497300,505800,701400,829400,810600,936100],
    15.0:[326200,362800,377300,491200,506800,516200,719000,849500,828000,955800],
    15.5:[331700,368200,384100,499600,516300,526600,736600,869600,845400,975500],
    16.0:[337200,373600,390900,508000,525800,537000,754200,889700,862800,995200],
    16.5:[342700,379000,397700,516400,535300,547400,771800,909800,880200,1014900],
    17.0:[348200,384400,404500,524800,544800,557800,789400,929900,897600,1034600],
    17.5:[353700,389800,411300,533200,554300,568200,807000,950000,915000,1054300],
    18.0:[359200,395200,418100,541600,563800,578600,824600,970100,932400,1074000],
    18.5:[364700,400600,424900,550000,573300,589000,842200,990200,949800,1093700],
    19.0:[370200,406000,431700,558400,582800,599400,859800,1010300,967200,1113400],
    19.5:[375700,411400,438500,566800,592300,609800,877400,1030400,984600,1133100],
    20.0:[380100,416800,445300,575200,601800,620200,895000,1050500,1002000,1152800],
    20.5:[380100,422200,452100,583600,611300,630600,912600,1070600,1019400,1172500],
}
# ── FedEx IP Over 20.5kg — 1kg당 요금 ──
FEDEX_PUB_OVER = {
    "21-44":  [18100,20500,24100,27800,29200,30100,43500,51700,51100,59900],
    "45-70":  [17900,19300,23600,23900,28600,29500,42600,46700,46600,55300],
    "71-99":  [17700,18600,23600,22800,28300,29100,42200,44300,46000,51100],
    "100-299":[17000,17700,22200,22000,27600,29000,41900,43900,45700,50300],
    "300-499":[16700,17500,21600,21800,26700,28000,40700,42500,44700,48700],
    "500-999":[16600,17200,21500,21800,26400,27400,40700,41900,44700,47700],
    "1000+":  [16600,17100,21500,21800,26400,27400,40700,41800,44700,47700],
}
# ── FedEx Economy IE — 화물 0.5~20.5kg (PAK/ENV 없음) ── 2026년 1월 5일 공식 요금표
FEDEX_PUB_ECON = {
    # Zone:     A        B        C        D        E        F        G        H        I        J
    0.5: [123000,128900,129300,134900,139800,142700,143500,150600,159600,189400],
    1.0: [133500,141300,141800,152800,155400,157900,169700,182700,184700,217700],
    1.5: [144000,153700,154300,170700,171000,173100,195900,214800,209800,246000],
    2.0: [154500,166100,166800,188600,186600,188300,222100,246900,234900,274300],
    2.5: [165000,178500,179300,206500,202200,203500,248300,279000,260000,302600],
    3.0: [171900,187700,188700,220900,215900,218400,267700,304000,286700,333900],
    3.5: [178800,196900,198100,235300,229600,233300,287100,329000,313400,365200],
    4.0: [185700,206100,207500,249700,243300,248200,306500,354000,340100,396500],
    4.5: [192600,215300,216900,264100,257000,263100,325900,379000,366800,427800],
    5.0: [199500,224500,226300,278500,270700,278000,345300,404000,393500,459100],
    5.5: [206100,232400,234100,290900,284100,291000,364000,427100,418300,487700],
    6.0: [212700,240300,241900,303300,297500,304000,382700,450200,443100,516300],
    6.5: [219300,248200,249700,315700,310900,317000,401400,473300,467900,544900],
    7.0: [225900,256100,257500,328100,324300,330000,420100,496400,492700,573500],
    7.5: [232500,264000,265300,340500,337700,343000,438800,519500,517500,602100],
    8.0: [239100,271900,273100,352900,351100,356000,457500,542600,542300,630700],
    8.5: [245700,279800,280900,365300,364500,369000,476200,565700,567100,659300],
    9.0: [252300,287700,288700,377700,377900,382000,494900,588800,591900,687900],
    9.5: [258900,295600,296500,390100,391300,395000,513600,611900,616700,716500],
    10.0:[265500,303500,304300,402500,404700,408000,532300,635000,641500,745100],
    10.5:[268500,307000,309100,407100,410800,414600,544600,648700,652900,758200],
    11.0:[271500,310500,313900,411700,416900,421200,556900,662400,664300,771300],
    11.5:[274500,314000,318700,416300,423000,427800,569200,676100,675700,784400],
    12.0:[277500,317500,323500,420900,429100,434400,581500,689800,687100,797500],
    12.5:[280500,321000,328300,425500,435200,441000,593800,703500,698500,810600],
    13.0:[283500,324500,333100,430100,441300,447600,606100,717200,709900,823700],
    13.5:[286500,328000,337900,434700,447400,454200,618400,730900,721300,836800],
    14.0:[289500,331500,342700,439300,453500,460800,630700,744600,732700,849900],
    14.5:[292500,335000,347500,443900,459600,467400,643000,758300,744100,863000],
    15.0:[295500,338500,352300,448500,465700,474000,655300,772000,755500,876100],
    15.5:[298500,342000,357100,453100,471800,480600,667600,785700,766900,889200],
    16.0:[301500,345500,361900,457700,477900,487200,679900,799400,778300,902300],
    16.5:[304500,349000,366700,462300,484000,493800,692200,813100,789700,915400],
    17.0:[307500,352500,371500,466900,490100,500400,704500,826800,801100,928500],
    17.5:[310500,356000,376300,471500,496200,507000,716800,840500,812500,941600],
    18.0:[313500,359500,381100,476100,502300,513600,729100,854200,823900,954700],
    18.5:[316500,363000,385900,480700,508400,520200,741400,867900,835300,967800],
    19.0:[319500,366500,390700,485300,514500,526800,753700,881600,846700,980900],
    19.5:[322500,370000,395500,489900,520600,533400,766000,895300,858100,994000],
    20.0:[325500,373500,400300,494500,526700,540000,778300,909000,869500,1007100],
    20.5:[328500,377000,405100,499100,532800,546600,790600,922700,880900,1020200],
}
# ── FedEx Economy Over — 1kg당 요금 ── 2026년 1월 5일 공식 요금표
FEDEX_PUB_ECON_OVER = {
    "21-44":  [16100,18200,21300,24100,25500,26100,37800,44700,44500,51900],
    "45-70":  [15900,17300,21000,20900,24600,25300,37000,40300,40500,48200],
    "71-99":  [15800,16600,20900,19700,24400,25100,36700,38900,40000,44300],
    "100-299":[15200,15900,20000,19100,23900,25000,36600,38200,39700,43800],
    "300-499":[15100,15700,19300,18900,23100,24300,35400,36900,38900,42500],
    "500-999":[15000,15400,19200,18900,23100,24000,35400,36500,38900,41400],
    "1000+":  [15000,15300,19200,18900,23100,24000,35400,36400,38900,41400],
}

# ═══════════════════════════════════════════════════
# 데이터: UPS Worldwide Express Saver (계정 2F94A8)
# Zone 1: 중국본토(남부제외)/마카오/싱가포르/대만
# Zone 2: 일본/베트남
# Zone 3: 브루나이/인도네시아/말레이시아/필리핀/태국
# Zone 4: 호주/인도/뉴질랜드
# Zone 5: 캐나다/멕시코/푸에르토리코/미국
# Zone 6: 서유럽(벨기에/체코/프랑스/독일/이탈리아/룩셈부르크/모나코/네덜란드/폴란드/슬로바키아/스페인/스웨덴/스위스/영국 등)
# Zone 7: 오스트리아/덴마크/핀란드/그리스/아일랜드/노르웨이/포르투갈
# Zone 8: 아르헨티나/바레인/브라질/캄보디아/칠레/이집트 등 다수
# Zone 9: 알바니아/알제리/에스토니아/이스라엘/요르단/카자흐스탄/레바논/세르비아 등
# Zone 10: 중국 남부(광동/복건/해남/호남/운남/광서/강서/중경)+홍콩
# ═══════════════════════════════════════════════════
# DHL 국가명 → UPS Zone 매핑 (DHL 드롭다운 공용 사용)
UPS_ZONE_MAP = {
    # Zone 1: 중국본토(남부제외), 마카오, 싱가포르, 대만
    "China (People's Republic)":1,"Macau SAR China":1,"Singapore":1,"Taiwan, China":1,
    # Zone 2: 일본, 베트남
    "Japan":2,"Vietnam":2,
    # Zone 3: 동남아
    "Brunei":3,"Indonesia":3,"Malaysia":3,"Philippines":3,"Thailand":3,
    # Zone 4: 호주권/인도
    "Australia":4,"India":4,"New Zealand":4,
    # Zone 5: 미주 핵심
    "Canada":5,"Mexico":5,"Puerto Rico":5,"United States of America":5,
    # Zone 6: 서유럽
    "Belgium":6,"Czech Republic":6,"France":6,"Germany":6,"Italy":6,
    "Liechtenstein":6,"Luxembourg":6,"Monaco":6,"Netherlands":6,"Poland":6,
    "Slovakia":6,"Spain":6,"Sweden":6,"Switzerland":6,"United Kingdom":6,
    # Zone 7: 북유럽/남유럽 일부
    "Austria":7,"Denmark":7,"Finland":7,"Greece":7,
    "Ireland":7,"Norway":7,"Portugal":7,
    # Zone 8: 동유럽/중동/중남미/기타 아시아
    "Argentina":8,"Armenia":8,"Bahrain":8,"Bangladesh":8,
    "Bolivia":8,"Brazil":8,"Bulgaria":8,"Cambodia":8,"Chile":8,
    "Colombia":8,"Costa Rica":8,"Croatia":8,"Curacao":8,
    "Dominican Republic":8,"Ecuador":8,"Egypt":8,"El Salvador":8,
    "Guatemala":8,"Haiti":8,"Honduras":8,"Hungary":8,"Iceland":8,
    "Jamaica":8,"Kuwait":8,"Lao P.D.R.":8,"Latvia":8,"Lithuania":8,
    "Maldives":8,"Malta":8,"Myanmar":8,"Nicaragua":8,"Oman":8,
    "Pakistan":8,"Panama":8,"Paraguay":8,"Peru":8,"Qatar":8,
    "Romania":8,"Saudi Arabia":8,"Slovenia":8,
    "South Africa":8,"Sri Lanka":8,"Turkiye":8,
    "Ukraine":8,"United Arab Emirates":8,"Uruguay":8,
    "Venezuela":8,"Trinidad and Tobago":8,
    # Zone 9: 아프리카/원격지
    "Afghanistan":9,"Albania":9,"Algeria":9,"Angola":9,"Benin":9,"Burkina Faso":9,
    "Burundi":9,"Cameroon":9,"Congo":9,"Estonia":9,"Ethiopia":9,"Gabon":9,
    "Georgia":9,"Ghana":9,"Guinea":9,"Guyana":9,"Israel":9,"Jordan":9,"Kazakhstan":9,
    "Kenya":9,"Lebanon":9,"Liberia":9,"Madagascar":9,"Malawi":9,
    "Mali":9,"Moldova":9,"Montenegro":9,"Morocco":9,"Mozambique":9,
    "Namibia":9,"Niger":9,"Nigeria":9,
    "Russia":9,"Rwanda":9,"Senegal":9,"Serbia":9,"Sierra Leone":9,"Sudan":9,
    "Tanzania":9,"Togo":9,"Tunisia":9,"Uganda":9,"Zambia":9,"Zimbabwe":9,
    # Zone 10: 중국 남부 + 홍콩
    "Hong Kong SAR China":10,
    # ── UPS PDF 2026 기준 서비스 가능 추가 국가 ──
    "Cyprus":8,"Guam":8,"Mongolia":9,"Nepal":9,"Martinique":8,
    # ── 서비스불가(아래 국가들은 UPS_NO_SERVICE에 별도 관리) ──
    # Bhutan, Fiji, Papua New Guinea, Yemen, Cuba, Syria, Iraq(수출불가), North Korea
}
# ── UPS 서비스 불가 국가 (2026 UPS PDF 기준 — 수출 WW Express Saver 전 서비스 "-") ──
UPS_NO_SERVICE = {
    "Bhutan",                 # 모든 UPS 서비스 "-"
    "Fiji",                   # 수출 WW Express Saver "-"
    "Papua New Guinea",       # 모든 UPS 서비스 "-"
    "Yemen",                  # 모든 UPS 서비스 "-"
    "Cuba",                   # UPS PDF 미등재 (미국 제재 대상)
    "Iran, Islamic Rep. of",  # UPS PDF 미등재 — DHL만 서비스
}
# ── FedEx 서비스 불가 국가 (2026 FedEx PDF 기준) ──
FEDEX_NO_SERVICE = {
    "Iran, Islamic Rep. of",  # FedEx PDF 미등재 — DHL만 서비스
}

# ── UPS Published 요금 (2026 Export WXS, Zone 1~10) ──
UPS_PUB_NDC = {
    0.5:[134200,135800,147200,150600,159400,144900,154500,203300,204900,129800],
    1.0:[144400,146800,157500,163200,176000,165600,179200,232300,239900,139500],
    1.5:[154600,156400,167900,177000,191900,186200,204100,261200,275700,149100],
    2.0:[164800,166500,178100,190200,207700,207000,228300,291100,311400,159100],
    2.5:[174000,176500,188900,203200,223900,227500,252900,320200,346700,168000],
    3.0:[182300,186200,200200,219100,239500,248600,274700,350900,377700,176100],
    3.5:[189800,195900,211000,235500,253900,270300,294800,380900,408700,183000],
    4.0:[196900,205700,222000,251500,268500,291500,314900,411300,439400,190000],
    4.5:[202900,215500,233300,267600,286400,312700,335200,441600,470200,196000],
    5.0:[209400,225200,244600,284300,301200,333900,355100,472200,501000,202300],
    5.5:[215600,236400,255500,296900,316000,356000,375500,505300,532000,208200],
    6.0:[221600,246400,266800,309100,330900,377400,396400,538600,562800,214000],
    6.5:[227300,257500,277600,321800,345600,399500,416300,572600,593800,219400],
    7.0:[232900,267500,288400,334300,359900,421400,437200,605800,624400,224900],
    7.5:[238200,278700,299900,346900,370600,443200,457200,639300,655400,230200],
    8.0:[243900,287800,309800,359300,384800,461300,479700,670100,682300,235300],
    8.5:[248500,296800,319600,371800,398900,478500,501900,701700,709700,240200],
    9.0:[254400,306200,329600,384300,412400,496000,524400,733000,736900,245400],
    9.5:[259600,315100,339800,397000,426600,513600,546900,763800,764200,250600],
    10.0:[264800,324200,349800,409800,440900,531200,568900,795000,799300,255700],
    10.5:[270000,330900,356900,419800,451000,546500,588700,822400,826400,260900],
    11.0:[275300,337600,364100,430100,462300,561800,608700,850600,853600,265900],
    11.5:[280700,344100,371800,440200,473300,577300,628100,879000,880400,271000],
    12.0:[285900,350800,378700,450700,483600,592400,648000,906000,907600,276400],
    12.5:[291200,357500,386000,461200,494900,607800,667500,934600,934600,281400],
    13.0:[296300,363800,392100,471200,506000,621900,687300,959300,961900,285900],
    13.5:[301900,370600,398000,481700,516900,636200,706900,983500,988900,291600],
    14.0:[307300,376800,404400,492000,527200,650600,727100,1008100,1005500,296700],
    14.5:[312300,383700,410300,502600,538500,665100,746800,1033000,1032200,301900],
    15.0:[317600,390100,416400,513000,549500,678900,766700,1057600,1058900,306700],
    15.5:[323000,391000,417400,517000,560000,693300,774700,1085900,1090300,311700],
    16.0:[328400,392500,418600,521700,570400,707200,782200,1113800,1121500,317200],
    16.5:[333300,394000,419300,526700,581000,727800,790400,1141900,1152400,322100],
    17.0:[338600,394900,420400,531100,591800,749300,798100,1169900,1183700,327300],
    17.5:[344000,396300,421800,535100,602700,766700,805700,1197900,1214300,332400],
    18.0:[348300,397400,422100,539500,610400,788100,821200,1215600,1232100,336100],
    18.5:[352000,398600,422500,543700,618400,808100,836800,1232900,1250300,339700],
    19.0:[355700,400000,423400,547800,632700,828400,858500,1250200,1265800,343500],
    19.5:[363100,401100,424100,551600,644200,849400,880100,1270400,1281200,352200],
    20.0:[372000,402800,425200,557900,660000,870100,901700,1302800,1301200,360800],
}
UPS_PUB_LTR = {
    0.5:[49700,51600,53000,64800,71700,68100,74100,87400,108600,46700],
    1.0:[76500,79300,80300,93000,110900,109300,116500,139400,155900,75300],
    1.5:[105100,106400,109100,122100,147800,150800,161300,195900,206800,101400],
    2.0:[130200,133200,137100,152100,180700,184200,203200,247400,255400,125700],
    2.5:[158300,162400,166200,182900,219400,227500,250400,304200,305100,152900],
    3.0:[171300,180500,186200,210400,239500,248600,274700,340400,343700,165500],
    3.5:[182200,194000,204700,233200,253900,270300,294800,377100,384100,175700],
    4.0:[194900,205700,222000,251500,268500,291500,314900,411300,421800,188100],
    4.5:[202900,215500,233300,267600,286400,312700,335200,441600,460800,196000],
    5.0:[209400,225200,244600,284300,301200,333900,355100,472200,501000,202300],
}
UPS_PUB_OVER = {
    "21-44":  [18600,20000,21000,27800,32100,43500,44900,63800,63700,18000],
    "45-70":  [18600,20000,21000,27800,32100,43500,44900,63800,63700,18000],
    "71-99":  [17000,18500,20300,27300,30500,42300,44200,63200,63200,16900],
    "100-299":[17000,18500,20300,27300,30500,42300,44200,63200,63200,16900],
    "300-499":[16400,17300,19400,26500,29200,42000,43300,61600,61700,16500],
    "500+":   [16400,17300,19400,26500,29200,42000,43300,61600,61700,16500],
}

# ── UPS 원가 (계정 2F94A8 실제 계약 요금, Zone 1~10) ──
UPS_NET_PKG = {
    0.5:[40260,40740,44160,48192,47820,43470,46350,60990,81960,38940],
    1.0:[43320,44040,47250,52224,52800,49680,53760,69690,95960,41850],
    1.5:[46380,46920,50370,56640,57570,55860,61230,78360,110280,44730],
    2.0:[49440,49950,53430,60864,62310,62100,68490,87330,124560,47730],
    2.5:[52200,52950,56670,65024,67170,68250,75870,96060,138680,50400],
    3.0:[54690,55860,60060,70112,71850,74580,82410,105270,151080,52830],
    3.5:[56940,58770,63300,75360,76170,81090,88440,114270,163480,54900],
    4.0:[59070,61710,66600,80480,80550,87450,94470,123390,175760,57000],
    4.5:[60870,64650,69990,85632,85920,93810,100560,132480,188080,58800],
    5.0:[62820,67560,73380,90976,90360,100170,106530,141660,200400,60690],
    5.5:[64680,70920,76650,95008,94800,106800,112650,151590,212800,62460],
    6.0:[66480,73920,80040,98912,99270,113220,118920,161580,225120,64200],
    6.5:[68190,77250,83280,102976,103680,119850,124890,171780,237520,65820],
    7.0:[69870,80250,86520,106976,107970,126420,131160,181740,249760,67470],
    7.5:[71460,83610,89970,111008,111180,132960,137160,191790,262160,69060],
    8.0:[73170,86340,92940,114976,115440,138390,143910,201030,272920,70590],
    8.5:[74550,89040,95880,118976,119670,143550,150570,210510,283880,72060],
    9.0:[76320,91860,98880,122976,123720,148800,157320,219900,294760,73620],
    9.5:[77880,94530,101940,127040,127980,154080,164070,229140,305680,75180],
    10.0:[79440,97260,104940,131136,132270,159360,170670,238500,319720,76710],
    10.5:[72900,89343,107070,134336,121770,147555,158949,222048,330560,70443],
    11.0:[74331,91152,109230,137632,124821,151686,164349,229662,341440,71793],
    11.5:[75789,92907,111540,140864,127791,155871,169587,237330,352160,73170],
    12.0:[77193,94716,113610,144224,130572,159948,174960,244620,363040,74628],
    12.5:[78624,96525,115800,147584,133623,164106,180225,252342,373840,75978],
    13.0:[80001,98226,117630,150784,136620,167913,185571,259011,384760,77193],
    13.5:[81513,100062,119400,154144,139563,171774,190863,265545,395560,78732],
    14.0:[82971,101736,121320,157440,142344,175662,196317,272187,402200,80109],
    14.5:[84321,103599,123090,160832,145395,179577,201636,278910,412880,81513],
    15.0:[63520,78020,112428,153900,141331,122202,138006,211520,423560,82809],
    15.5:[64600,78200,112698,155100,144032,124794,139446,217180,436120,84159],
    16.0:[65680,78500,113022,156510,146707,127296,140796,222760,448600,85644],
    16.5:[66660,78800,113211,158010,149433,131004,142272,228380,460960,86967],
    17.0:[67720,78980,113508,159330,152211,134874,143658,233980,473480,88371],
    17.5:[68800,79260,113886,160530,155014,138006,145026,239580,485720,89748],
    18.0:[69660,79480,113967,161850,156995,141858,147816,243120,492840,90747],
    18.5:[70400,79720,114075,163110,159052,145458,150624,246580,500120,91719],
    19.0:[71140,80000,114318,164340,162730,149112,154530,250040,506320,92745],
    19.5:[72620,80220,114507,165480,165688,152892,158418,254080,512480,95094],
    20.0:[74400,80560,114804,167370,169752,156618,162306,260560,520480,97416],
}
UPS_NET_DOC = {
    0.5:[19880,20640,21200,25920,28680,27240,29640,34960,43440,18680],
    1.0:[30600,31720,32120,37200,44360,43720,46600,55760,62360,30120],
    1.5:[42040,42560,43640,48840,59120,60320,64520,78360,82720,40560],
    2.0:[52080,53280,54840,60840,72280,73680,81280,98960,102160,50280],
    2.5:[63320,64960,66480,73160,87760,91000,100160,121680,122040,61160],
    3.0:[68520,72200,74480,84160,95800,99440,109880,136160,137480,66200],
    3.5:[72880,77600,81880,93280,101560,108120,117920,150840,153640,70280],
    4.0:[77960,82280,88800,100600,107400,116600,125960,164520,168720,75240],
    4.5:[81160,86200,93320,107040,114560,125080,134080,176640,184320,78400],
    5.0:[83760,90080,97840,113720,120480,133560,142040,188880,200400,80920],
}
# 20kg 초과: KG당 요금 × 총 중량 (최대 중량 기준 브래킷)
UPS_NET_OVER = {
    44: [3720,4000,5670,8340,8256,7830,8082,12760,25480,4860],    # ~44kg
    70: [5580,6000,8400,11120,8256,7830,8082,19140,25480,7200],   # ~70kg
    99: [5100,5550,8120,10920,7845,7614,7956,18960,25280,6760],   # ~99kg
    299:[5100,5550,8120,10920,7875,7614,7956,18960,25280,6760],   # ~299kg
    499:[4920,5190,7760,10600,7814,7560,7794,18480,24680,6600],   # ~499kg
    999:[4920,5190,7760,10600,7814,7560,7794,18480,24680,6600],   # ~999kg
    9999999:[4920,5190,7760,10600,7814,7560,7794,18480,24680,6600],
}

# ── UPS 원가 계정 B8733R (Bid Q9240598KR, 2026 요율 기준) Zone 1~10 ──
UPS_B8733R_PKG = {
    0.5:[28182,28518,30912,31626,33474,30429,32445,42693,43029,27258],
    1.0:[30324,30828,33075,34272,36960,34776,37632,48783,50379,29295],
    1.5:[32466,32844,35259,37170,40299,39102,42861,54852,57897,31311],
    2.0:[34608,34965,37401,39942,43617,43470,47943,61131,65394,33411],
    2.5:[36540,37065,39669,42672,47019,47775,53109,67242,72807,35280],
    3.0:[38283,39102,42042,46011,50295,52206,57687,73689,79317,36981],
    3.5:[39858,41139,44310,49455,53319,56763,61908,79989,85827,38430],
    4.0:[41349,43197,46620,52815,56385,61215,66129,86373,92274,39900],
    4.5:[42609,45255,48993,56196,60144,65667,70392,92736,98742,41160],
    5.0:[43974,47292,51366,59703,63252,70119,74571,99162,105210,42483],
    5.5:[53900,59100,63875,74225,79000,89000,93875,126325,133000,52050],
    6.0:[55400,61600,66700,77275,82725,94350,99100,134650,140700,53500],
    6.5:[56825,64375,69400,80450,86400,99875,104075,143150,148450,54850],
    7.0:[58225,66875,72100,83575,89975,105350,109300,151450,156100,56225],
    7.5:[59550,69675,74975,86725,92650,110800,114300,159825,163850,57550],
    8.0:[60975,71950,77450,89825,96200,115325,119925,167525,170575,58825],
    8.5:[62125,74200,79900,92950,99725,119625,125475,175425,177425,60050],
    9.0:[63600,76550,82400,96075,103100,124000,131100,183250,184225,61350],
    9.5:[64900,78775,84950,99250,106650,128400,136725,190950,191050,62650],
    10.0:[66200,81050,87450,102450,110225,132800,142225,198750,199825,63925],
    10.5:[67500,82725,89225,104950,112750,136625,147175,205600,206600,65225],
    11.0:[68825,84400,91025,107525,115575,140450,152175,212650,213400,66475],
    11.5:[70175,86025,92950,110050,118325,144325,157025,219750,220100,67750],
    12.0:[71475,87700,94675,112675,120900,148100,162000,226500,226900,69100],
    12.5:[72800,89375,96500,115300,123725,151950,166875,233650,233650,70350],
    13.0:[74075,90950,98025,117800,126500,155475,171825,239825,240475,71475],
    13.5:[75475,92650,99500,120425,129225,159050,176725,245875,247225,72900],
    14.0:[76825,94200,101100,123000,131800,162650,181775,252025,251375,74175],
    14.5:[78075,95925,102575,125650,134625,166275,186700,258250,258050,75475],
    15.0:[79400,97525,104100,128250,137375,169725,191675,264400,264725,76675],
    15.5:[80750,97750,104350,129250,140000,173325,193675,271475,272575,77925],
    16.0:[82100,98125,104650,130425,142600,176800,195550,278450,280375,79300],
    16.5:[83325,98500,104825,131675,145250,181950,197600,285475,288100,80525],
    17.0:[84650,98725,105100,132775,147950,187325,199525,292475,295925,81825],
    17.5:[86000,99075,105450,133775,150675,191675,201425,299475,303575,83100],
    18.0:[87075,99350,105525,134875,152600,197025,205300,303900,308025,84025],
    18.5:[88000,99650,105625,135925,154600,202025,209200,308225,312575,84925],
    19.0:[88925,100000,105850,136950,158175,207100,214625,312550,316450,85875],
    19.5:[90775,100275,106025,137900,161050,212350,220025,317600,320300,88050],
    20.0:[93000,100700,106300,139475,165000,217525,225425,325700,325300,90200],
}
UPS_B8733R_DOC = {
    0.5:[14910,15480,15900,19440,22600,22600,23700,26220,32580,14010],
    1.0:[22950,23790,24090,27900,33270,32790,34950,41820,46770,22590],
    1.5:[31530,31920,32730,36630,44340,45240,48390,58770,62040,30420],
    2.0:[39060,39960,41130,45630,54210,55260,60960,74220,76620,37710],
    2.5:[47490,48720,49860,54870,65820,68250,75120,91260,91530,45870],
    3.0:[51390,54150,55860,63120,71850,74580,82410,102120,103110,49650],
    3.5:[54660,58200,61410,69960,76170,81090,88440,113130,115230,52710],
    4.0:[58470,61710,66600,75450,80550,87450,94470,123390,126540,56430],
    4.5:[60870,64650,69990,80280,85920,93810,100560,132480,138240,58800],
    5.0:[62820,67560,73380,85290,90360,100170,106530,141660,150300,60690],
}
UPS_B8733R_OVER = {
    44: [4650,5000,5250,6950,8205,10875,11225,15950,15925,4500],    # ~44kg
    70: [4650,5000,5250,6950,8391,10875,11225,15950,15925,4500],    # ~70kg
    99: [8500,9250,10150,13650,15250,21150,22100,31600,31600,8450], # ~99kg
    299:[8500,9250,10150,13650,15250,21150,22100,31600,31600,8450], # ~299kg
    499:[8200,8650,9700,13250,14600,21000,21650,30800,30850,8250],  # ~499kg
    999:[8200,8650,9700,13250,14600,21000,21650,30800,30850,8250],  # ~999kg
    9999999:[8200,8650,9700,13250,14600,21000,21650,30800,30850,8250],
}

# 계정별 원가 테이블 딕셔너리
UPS_ACCOUNTS = {
    "2F94A8": {"pkg": UPS_NET_PKG, "doc": UPS_NET_DOC, "over": UPS_NET_OVER},
    "B8733R": {"pkg": UPS_B8733R_PKG, "doc": UPS_B8733R_DOC, "over": UPS_B8733R_OVER},
}

# ═══════════════════════════════════════════════════
# 계산 함수
# ═══════════════════════════════════════════════════
def calc_weight(actual, L, W, H):
    vol = round(L * W * H / 5000, 2)
    chargeable = max(actual, vol)
    rounded = math.ceil(chargeable * 2) / 2 if chargeable <= 30 else math.ceil(chargeable)
    return {"actual": actual, "volume": vol, "rounded": rounded,
            "basis": "부피중량" if vol > actual else "실중량"}

def ceil10(x):
    """1원 단위 올림 → 10원 단위 (예: 123451 → 123460, 123400 → 123400)"""
    return math.ceil(x / 10) * 10

def dhl_lookup(w, zi, is_doc):
    pt = DHL_PUB_DOC if (is_doc and w <= 2.0) else DHL_PUB_NDC
    nt = DHL_NET_DOC if (is_doc and w <= 2.0) else DHL_NET_NDC
    def _get(table, over):
        if w <= 30:
            k = math.ceil(w * 2) / 2
            for key in sorted(table):
                if key >= k: return ceil10(table[key][zi])
            return ceil10(table[max(table)][zi])
        return ceil10(over["30.1-70"][zi] * int(math.ceil(w)))
    return _get(pt, DHL_PUB_OVER), _get(nt, DHL_NET_OVER)

def fedex_lookup(w, zi, is_doc=False, econ=False):
    """FedEx 공시가 반환
    서류(is_doc=True):
      - w=0.5kg       → Envelope 요금 (IP만 해당, Economy는 IE 화물 요금)
      - 0.5 < w ≤ 2.5 → PAK 요금 (IP만 해당)
      - w > 2.5       → IP/IE NDC 화물 요금으로 처리
    화물(is_doc=False): IP 또는 IE NDC 요금
    20.5kg 초과: 1kg 단위 브래킷 (21-44 / 45-70 / 71-99 / 100-299 / 300-499 / 500-999 / 1000+)
    """
    if not econ and is_doc:
        if w <= 0.5:
            return ceil10(FEDEX_PUB_ENV[0.5][zi])
        elif w <= 2.5:
            k = math.ceil(w * 2) / 2
            for key in sorted(FEDEX_PUB_PAK):
                if key >= k: return ceil10(FEDEX_PUB_PAK[key][zi])
            return ceil10(FEDEX_PUB_PAK[max(FEDEX_PUB_PAK)][zi])
        # 2.5kg 초과 서류 → IP NDC 화물 요금으로 낙수

    pub_tbl = FEDEX_PUB_ECON      if econ else FEDEX_PUB_IP
    ovr_tbl = FEDEX_PUB_ECON_OVER if econ else FEDEX_PUB_OVER
    if w <= 20.5:
        k = math.ceil(w * 2) / 2
        for key in sorted(pub_tbl):
            if key >= k: return ceil10(pub_tbl[key][zi])
        return ceil10(pub_tbl[max(pub_tbl)][zi])
    rw = int(math.ceil(w))
    br = ("21-44"   if rw <= 44  else
          "45-70"   if rw <= 70  else
          "71-99"   if rw <= 99  else
          "100-299" if rw <= 299 else
          "300-499" if rw <= 499 else
          "500-999" if rw <= 999 else "1000+")
    return ceil10(ovr_tbl[br][zi] * rw)

def ups_lookup(w, zi, is_doc, acct="2F94A8"):
    """UPS Worldwide Express Saver 요금 조회 → (published, net)"""
    if w <= 20:
        k = math.ceil(w * 2) / 2
        pub_tbl = UPS_PUB_LTR if (is_doc and w <= 5.0) else UPS_PUB_NDC
        pub = ceil10(next(pub_tbl[key][zi] for key in sorted(pub_tbl) if key >= k))
        ac = UPS_ACCOUNTS[acct]
        net_tbl = ac["doc"] if (is_doc and w <= 5.0) else ac["pkg"]
        net = ceil10(next(net_tbl[key][zi] for key in sorted(net_tbl) if key >= k))
    else:
        rw = int(math.ceil(w))
        if rw <= 44:   br = "21-44"
        elif rw <= 70: br = "45-70"
        elif rw <= 99: br = "71-99"
        elif rw <= 299:br = "100-299"
        elif rw <= 499:br = "300-499"
        else:          br = "500+"
        pub = ceil10(UPS_PUB_OVER[br][zi] * rw)
        ac = UPS_ACCOUNTS[acct]
        net = ceil10(next(ac["over"][mw][zi] * rw for mw in sorted(ac["over"]) if rw <= mw))
    return pub, net

def fmt(n): return f"₩{int(n):,}"
def pct(n): return f"{n:.1f}%"

def calc_carrier(carrier_name, total_pub_base, net_base, sur_total, fuel, disc, net_fee=0):
    """운송사 요금 계산 공통 함수 — net_fee: UPS 계정 수수료(3%) 별도 전달"""
    # ── 원가 (유류할증료는 원가+수수료 합산 기준) ──
    net_fuel  = ceil10((net_base + net_fee) * fuel / 100)
    sur_fuel  = ceil10(sur_total * fuel / 100)
    total_cost = net_base + net_fee + net_fuel + sur_total + sur_fuel
    # ── 견적가 ──
    pub_disc      = ceil10(total_pub_base * (1 - disc / 100))
    pub_fuel      = ceil10(pub_disc       * fuel / 100)
    sur_fuel_pub  = ceil10(sur_total      * fuel / 100)
    total_quote   = pub_disc + pub_fuel + sur_total + sur_fuel_pub
    margin_amt  = total_quote - total_cost
    margin_rate = (margin_amt / total_quote * 100) if total_quote > 0 else 0
    return {
        "pub_base":    total_pub_base,
        "net_base":    net_base,
        "net_fee":     net_fee,
        "net_fuel":    net_fuel,
        "sur_total":   sur_total,
        "sur_fuel":    sur_fuel,
        "sur_fuel_pub":sur_fuel_pub,
        "pub_fuel":    pub_fuel,
        "pub_disc":    pub_disc,
        "total_cost":  total_cost,
        "total_quote": total_quote,
        "margin_amt":  margin_amt,
        "margin_rate": margin_rate,
    }

# ═══════════════════════════════════════════════════
# 데이터: 수입 (DHL / FedEx IP / FedEx Economy / UPS)
# ═══════════════════════════════════════════════════

# ── DHL 수입 존 매핑 (수출과 동일 Zone 1~8) ──
# 수출 DHL_ZONE_MAP 재사용

# ── DHL 수입 DOX (서류 2kg 이하, Zone 1~8) ── 2026 DHL Express Worldwide Import 공시가
DHL_IMP_DOX = {
    0.5: [67900, 71600, 72500, 84300, 87000, 94200,105900,124200],
    1.0: [101500,102000,108000,122400,124300,152400,167800,197000],
    1.5: [133600,139500,147900,161400,163700,203500,226600,271800],
    2.0: [165700,177000,187800,200400,203100,254600,285400,346600],
}

# ── DHL 수입 NDC (물품 0.5~30.0kg, Zone 1~8) ── 2026 DHL Express Worldwide Import 공시가
DHL_IMP_NDC = {
    0.5:  [161800,169400,170100,176700,178600,191800,201400,260900],
    1.0:  [184400,192700,193400,201500,203700,234400,249400,316300],
    1.5:  [196000,206700,212300,221700,224100,266700,289000,363300],
    2.0:  [207600,220700,231200,241900,244500,299000,328600,410300],
    2.5:  [219000,234600,249400,261000,263900,330500,367500,455400],
    3.0:  [228000,247000,265500,279300,282300,357300,401100,497100],
    3.5:  [237000,259400,281600,297600,300700,384100,434700,538800],
    4.0:  [246000,271800,297700,315900,319100,410900,468300,580500],
    4.5:  [255000,284200,313800,334200,337500,437700,501900,622200],
    5.0:  [264000,296600,329900,352500,355900,464500,535500,663900],
    5.5:  [272400,305700,344200,368400,372500,488900,566300,703900],
    6.0:  [280800,314800,358500,384300,389100,513300,597100,743900],
    6.5:  [289200,323900,372800,400200,405700,537700,627900,783900],
    7.0:  [297600,333000,387100,416100,422300,562100,658700,823900],
    7.5:  [306000,342100,401400,432000,438900,586500,689500,863900],
    8.0:  [314400,351200,415700,447900,455500,610900,720300,903900],
    8.5:  [322800,360300,430000,463800,472100,635300,751100,943900],
    9.0:  [331200,369400,444300,479700,488700,659700,781900,983900],
    9.5:  [339600,378500,458600,495600,505300,684100,812700,1023900],
    10.0: [348000,387600,472900,511500,521900,708500,843500,1063900],
    10.5: [356100,395900,483600,524400,534500,732200,872400,1101300],
    11.0: [364200,404200,494300,537300,547100,755900,901300,1138700],
    11.5: [372300,412500,505000,550200,559700,779600,930200,1176100],
    12.0: [380400,420800,515700,563100,572300,803300,959100,1213500],
    12.5: [388500,429100,526400,576000,584900,827000,988000,1250900],
    13.0: [396600,437400,537100,588900,597500,850700,1016900,1288300],
    13.5: [404700,445700,547800,601800,610100,874400,1045800,1325700],
    14.0: [412800,454000,558500,614700,622700,898100,1074700,1363100],
    14.5: [420900,462300,569200,627600,635300,921800,1103600,1400500],
    15.0: [429000,470600,579900,640500,647900,945500,1132500,1437900],
    15.5: [437100,478900,590600,653400,660500,969200,1161400,1475300],
    16.0: [445200,487200,601300,666300,673100,992900,1190300,1512700],
    16.5: [453300,495500,612000,679200,685700,1016600,1219200,1550100],
    17.0: [461400,503800,622700,692100,698300,1040300,1248100,1587500],
    17.5: [469500,512100,633400,705000,710900,1064000,1277000,1624900],
    18.0: [477600,520400,644100,717900,723500,1087700,1305900,1662300],
    18.5: [485700,528700,654800,730800,736100,1111400,1334800,1699700],
    19.0: [493800,537000,665500,743700,748700,1135100,1363700,1737100],
    19.5: [501900,545300,676200,756600,761300,1158800,1392600,1774500],
    20.0: [510000,553600,686900,769500,773900,1182500,1421500,1811900],
    20.5: [520800,565200,701700,786100,791500,1208800,1449700,1848500],
    21.0: [531600,576800,716500,802700,809100,1235100,1477900,1885100],
    21.5: [542400,588400,731300,819300,826700,1261400,1506100,1921700],
    22.0: [553200,600000,746100,835900,844300,1287700,1534300,1958300],
    22.5: [564000,611600,760900,852500,861900,1314000,1562500,1994900],
    23.0: [574800,623200,775700,869100,879500,1340300,1590700,2031500],
    23.5: [585600,634800,790500,885700,897100,1366600,1618900,2068100],
    24.0: [596400,646400,805300,902300,914700,1392900,1647100,2104700],
    24.5: [607200,658000,820100,918900,932300,1419200,1675300,2141300],
    25.0: [618000,669600,834900,935500,949900,1445500,1703500,2177900],
    25.5: [628800,681200,849700,952100,967500,1471800,1731700,2214500],
    26.0: [639600,692800,864500,968700,985100,1498100,1759900,2251100],
    26.5: [650400,704400,879300,985300,1002700,1524400,1788100,2287700],
    27.0: [661200,716000,894100,1001900,1020300,1550700,1816300,2324300],
    27.5: [672000,727600,908900,1018500,1037900,1577000,1844500,2360900],
    28.0: [682800,739200,923700,1035100,1055500,1603300,1872700,2397500],
    28.5: [693600,750800,938500,1051700,1073100,1629600,1900900,2434100],
    29.0: [704400,762400,953300,1068300,1090700,1655900,1929100,2470700],
    29.5: [715200,774000,968100,1084900,1108300,1682200,1957300,2507300],
    30.0: [726000,785600,982900,1101500,1125900,1708500,1985500,2543900],
}
# DHL 수입 초과중량 (kg당 요금) — 30.1kg 이상, 3구간 모두 동일 요율
DHL_IMP_OVER = {
    "30-70":  [23700,25500,31800,37100,38000,56900,64300,82300],
    "70-300": [23700,25500,31800,37100,38000,56900,64300,82300],
    "300+":   [23700,25500,31800,37100,38000,56900,64300,82300],
}


# ══════════════════════════════════════════════════════════
# DHL 수입 원가 테이블 (에어브리지 계약 원가 — KRD00PM2X, 2026.01.01)
# Zone 1~8
# ══════════════════════════════════════════════════════════
# DHL 수입 원가 — 서류(Documents up to 2.0 KG)
DHL_IMP_COST_DOX = {
    # Zone:   1       2       3       4       5       6       7       8
    0.5: [ 21176, 22418, 22477, 29454, 27976, 32118, 36020, 42350],
    1.0: [ 36199, 36198, 38506, 46548, 44123, 54417, 59917, 70444],
    1.5: [ 47614, 49506, 52820, 61215, 58143, 72575, 80854, 97236],
    2.0: [ 59029, 62814, 67134, 75882, 72163, 90733,101791,124028],
}
# DHL 수입 원가 — 물품 / 서류 2.5kg+ (Non-documents from 0.5 KG & Documents from 2.5 KG)
DHL_IMP_COST_NDC = {
    # Zone:    1       2       3       4       5       6       7       8
    0.5:  [ 59975, 63229, 62044, 66955, 66009, 71450, 75116, 97474],
    1.0:  [ 66657, 70146, 69675, 75235, 73521, 84582, 89961,113977],
    1.5:  [ 70441, 74938, 76123, 82749, 80085, 95583,103621,130006],
    2.0:  [ 74225, 79730, 82571, 90263, 86649,106584,117281,146035],
    2.5:  [ 78008, 84520, 89019, 97776, 93215,117585,130942,162063],
    3.0:  [ 81201, 88779, 94579,104518, 99546,126813,142830,176908],
    3.5:  [ 84394, 93038,100139,111260,105877,136041,154718,191753],
    4.0:  [ 87587, 97297,105699,118002,112208,145269,166606,206598],
    4.5:  [ 90780,101556,111259,124744,118539,154497,178494,221443],
    5.0:  [ 93973,105815,116819,131486,124870,163725,190382,236288],
    5.5:  [ 96872,109305,121906,137104,130666,172302,201383,250663],
    6.0:  [ 99771,112795,126993,142722,136462,180879,212384,265038],
    6.5:  [102670,116285,132080,148340,142258,189456,223385,279413],
    7.0:  [105569,119775,137167,153958,148054,198033,234386,293788],
    7.5:  [108468,123265,142254,159576,153850,206610,245387,308163],
    8.0:  [111367,126755,147341,165194,159646,215187,256388,322538],
    8.5:  [114266,130245,152428,170812,165442,223764,267389,336913],
    9.0:  [117165,133735,157515,176430,171238,232341,278390,351288],
    9.5:  [120064,137225,162602,182048,177034,240918,289391,365663],
    10.0: [122963,140715,167689,187666,182830,249495,300392,380038],
    10.5: [125802,143792,171474,191986,187383,257955,310918,393997],
    11.0: [128641,146869,175259,196306,191936,266415,321444,407956],
    11.5: [131480,149946,179044,200626,196489,274875,331970,421915],
    12.0: [134319,153023,182829,204946,201042,283335,342496,435874],
    12.5: [137158,156100,186614,209266,205595,291795,353022,449833],
    13.0: [139997,159177,190399,213586,210148,300255,363548,463792],
    13.5: [142836,162254,194184,217906,214701,308715,374074,477751],
    14.0: [145675,165331,197969,222226,219254,317175,384600,491710],
    14.5: [148514,168408,201754,226546,223807,325635,395126,505669],
    15.0: [151353,171485,205539,230866,228360,334095,405652,519628],
    15.5: [154192,174562,209324,235186,232913,342555,416178,533587],
    16.0: [157031,177639,213109,239506,237466,351015,426704,547546],
    16.5: [159870,180716,216894,243826,242019,359475,437230,561505],
    17.0: [162709,183793,220679,248146,246572,367935,447756,575464],
    17.5: [165548,186870,224464,252466,251125,376395,458282,589423],
    18.0: [168387,189947,228249,256786,255678,384855,468808,603382],
    18.5: [171226,193024,232034,261106,260231,393315,479334,617341],
    19.0: [174065,196101,235819,265426,264784,401775,489860,631300],
    19.5: [176904,199178,239604,269746,269337,410235,500386,645259],
    20.0: [179743,202255,243389,274066,273890,418695,510912,659218],
    20.5: [184122,206750,248948,280276,280040,427862,522092,673356],
    21.0: [188501,211245,254507,286486,286190,437029,533272,687494],
    21.5: [192880,215740,260066,292696,292340,446196,544452,701632],
    22.0: [197259,220235,265625,298906,298490,455363,555632,715770],
    22.5: [201638,224730,271184,305116,304640,464530,566812,729908],
    23.0: [206017,229225,276743,311326,310790,473697,577992,744046],
    23.5: [210396,233720,282302,317536,316940,482864,589172,758184],
    24.0: [214775,238215,287861,323746,323090,492031,600352,772322],
    24.5: [219154,242710,293420,329956,329240,501198,611532,786460],
    25.0: [223533,247205,298979,336166,335390,510365,622712,800598],
    25.5: [227912,251700,304538,342376,341540,519532,633892,814736],
    26.0: [232291,256195,310097,348586,347690,528699,645072,828874],
    26.5: [236670,260690,315656,354796,353840,537866,656252,843012],
    27.0: [241049,265185,321215,361006,359990,547033,667432,857150],
    27.5: [245428,269680,326774,367216,366140,556200,678612,871288],
    28.0: [249807,274175,332333,373426,372290,565367,689792,885426],
    28.5: [254186,278670,337892,379636,378440,574534,700972,899564],
    29.0: [258565,283165,343451,385846,384590,583701,712152,913702],
    29.5: [262944,287660,349010,392056,390740,592868,723332,927840],
    30.0: [267323,292155,354569,398266,396890,602035,734512,941978],
}
# DHL 수입 원가 — 초과중량 (30.1kg+, kg당 요금)
DHL_IMP_COST_OVER = {
    # Zone:       1     2      3      4      5      6      7      8
    "30-70":  [ 7328, 7722, 10663, 13193, 12224, 17612, 22329, 28786],
    "70-300": [ 6031, 5668, 10663, 12274, 10319, 10384, 20717, 26796],
    "300+":   [ 6031, 5668, 10531, 11781, 10319, 10384, 20340, 26304],
}

# ── FedEx 수입 존 매핑 (수출과 동일 Zone A~J 사용) ──
# FEDEX_ZONE_MAP 재사용

# ── FedEx IP 수입 Envelope (0.5kg, Zone A~J) ── 2026 IP ImportOne 공시가
FXIMP_ENV = {
    # Zone:      A       B       C       D       E       F       G       H       I       J
    0.5: [ 62800, 65400, 64300, 72300, 76900, 77000,116700,124500,130700,134100],
}
# FedEx IP 수입 PAK (0.5~2.5kg, Zone A~J) ── 2026 IP ImportOne 공시가
FXIMP_PAK = {
    # Zone:      A       B       C       D       E       F       G       H       I       J
    0.5: [ 86300,119400, 93300,115600,137800,141600,141700,142200,149700,151500],
    1.0: [102200,135800,110500,135600,162200,165200,175800,186300,196100,213900],
    1.5: [116900,145300,121700,150400,185200,187600,207400,223100,234400,267200],
    2.0: [129800,160700,134500,167000,207800,213400,240300,263800,278900,322100],
    2.5: [144700,173300,148800,184700,232900,238900,273200,305100,319100,384100],
}
# FedEx IP 수입 NDC (0.5~20.5kg, Zone A~J) ── 2026 IP ImportOne 공시가
FXIMP_IP = {
    # Zone:      A       B       C       D       E       F       G       H       I       J
    0.5:  [ 93700,133600, 97200,117500,154900,159000,187900,206700,228100,242000],
    1.0:  [111700,152100,114800,137400,181000,185300,217200,242500,266800,283100],
    1.5:  [129700,170600,132400,157300,207100,211600,246500,278300,305500,324200],
    2.0:  [147700,189100,150000,177200,233200,237900,275800,314100,344200,365300],
    2.5:  [165700,207600,167600,197100,259300,264200,305100,349900,382900,406400],
    3.0:  [173900,221200,183200,216900,283900,288900,336500,387200,419500,451000],
    3.5:  [182100,234800,198800,236700,308500,313600,367900,424500,456100,495600],
    4.0:  [190300,248400,214400,256500,333100,338300,399300,461800,492700,540200],
    4.5:  [198500,262000,230000,276300,357700,363000,430700,499100,529300,584800],
    5.0:  [206700,275600,245600,296100,382300,387700,462100,536400,565900,629400],
    5.5:  [217700,288600,259000,311900,396900,402400,483500,565100,598300,666200],
    6.0:  [228700,301600,272400,327700,411500,417100,504900,593800,630700,703000],
    6.5:  [239700,314600,285800,343500,426100,431800,526300,622500,663100,739800],
    7.0:  [250700,327600,299200,359300,440700,446500,547700,651200,695500,776600],
    7.5:  [261700,340600,312600,375100,455300,461200,569100,679900,727900,813400],
    8.0:  [272700,353600,326000,390900,469900,475900,590500,708600,760300,850200],
    8.5:  [283700,366600,339400,406700,484500,490600,611900,737300,792700,887000],
    9.0:  [294700,379600,352800,422500,499100,505300,633300,766000,825100,923800],
    9.5:  [305700,392600,366200,438300,513700,520000,654700,794700,857500,960600],
    10.0: [316700,405600,379600,454100,528300,534700,676100,823400,889900,997400],
    10.5: [324300,416900,388600,466300,539200,548000,688700,841800,908400,1021700],
    11.0: [331900,428200,397600,478500,550100,561300,701300,860200,926900,1046000],
    11.5: [339500,439500,406600,490700,561000,574600,713900,878600,945400,1070300],
    12.0: [347100,450800,415600,502900,571900,587900,726500,897000,963900,1094600],
    12.5: [354700,462100,424600,515100,582800,601200,739100,915400,982400,1118900],
    13.0: [362300,473400,433600,527300,593700,614500,751700,933800,1000900,1143200],
    13.5: [369900,484700,442600,539500,604600,627800,764300,952200,1019400,1167500],
    14.0: [377500,496000,451600,551700,615500,641100,776900,970600,1037900,1191800],
    14.5: [385100,507300,460600,563900,626400,654400,789500,989000,1056400,1216100],
    15.0: [392700,518600,469600,576100,637300,667700,802100,1007400,1074900,1240400],
    15.5: [400300,529900,478600,588300,648200,681000,814700,1025800,1093400,1264700],
    16.0: [407900,541200,487600,600500,659100,694300,827300,1044200,1111900,1289000],
    16.5: [415500,552500,496600,612700,670000,707600,839900,1062600,1130400,1313300],
    17.0: [423100,563800,505600,624900,680900,720900,852500,1081000,1148900,1337600],
    17.5: [430700,575100,514600,637100,691800,734200,865100,1099400,1167400,1361900],
    18.0: [438300,586400,523600,649300,702700,747500,877700,1117800,1185900,1386200],
    18.5: [445900,597700,532600,661500,713600,760800,890300,1136200,1204400,1410500],
    19.0: [453500,609000,541600,673700,724500,774100,902900,1154600,1222900,1434800],
    19.5: [461100,620300,550600,685900,735400,787400,915500,1173000,1241400,1459100],
    20.0: [468700,631600,559600,698100,746300,800700,924000,1191400,1259900,1483400],
    20.5: [476300,642900,568600,710300,757200,814000,924000,1209800,1278400,1507700],
}
FXIMP_OVER = {
    # Zone:         A      B      C      D      E      F      G      H      I      J
    "21-44":   [23300,31200,31800,34400,36600,38900,44000,57700,61300,71900],
    "45-70":   [20900,24400,25900,31000,33100,35000,38800,52400,54900,65100],
    "71-99":   [19700,22100,25600,28700,30200,33000,33500,48000,51100,59700],
    "100-299": [18500,20900,23700,26800,29100,30500,31000,45900,49200,56300],
    "300-499": [18100,19700,22200,24800,28300,29700,30000,44400,47600,53300],
    "500-999": [17800,19100,21500,23900,27100,28300,28300,42700,45300,50300],
    "1000+":   [17700,18900,21400,23900,27000,28300,28300,42700,45200,50300],
}

# FedEx Economy 수입 NDC (0.5~20.5kg, Zone A~J)
FXIMP_ECON = {
    0.5:  [92200,130900,94900,80500,113300,115500,130800,131900,139300,140400],
    1.0:  [109600,149200,112300,93800,131700,134000,151800,166700,180400,184200],
    1.5:  [127000,167500,129700,107100,150100,152500,172800,201500,221500,228000],
    2.0:  [144400,185800,147100,120400,168500,171000,193800,236300,262600,271800],
    2.5:  [161800,204100,164500,133700,186900,189500,214800,271100,303700,315600],
    3.0:  [170100,217200,179800,146500,205100,207800,235800,295100,328500,341500],
    3.5:  [178400,230300,195100,159300,223300,226100,256800,319100,353300,367400],
    4.0:  [186700,243400,210400,172100,241500,244400,277800,343100,378100,393300],
    4.5:  [195000,256500,225700,184900,259700,262700,298800,367100,402900,419200],
    5.0:  [203300,269600,241000,197700,277900,281000,319800,391100,427700,445100],
    5.5:  [213900,282400,254400,209300,289300,292500,334800,412800,450000,470600],
    6.0:  [224500,295200,267800,220900,300700,304000,349800,434500,472300,496100],
    6.5:  [235100,308000,281200,232500,312100,315500,364800,456200,494600,521600],
    7.0:  [245700,320800,294600,244100,323500,327000,379800,477900,516900,547100],
    7.5:  [256300,333600,308000,255700,334900,338500,394800,499600,539200,572600],
    8.0:  [266900,346400,321400,267300,346300,350000,409800,521300,561500,598100],
    8.5:  [277500,359200,334800,278900,357700,361500,424800,543000,583800,623600],
    9.0:  [288100,372000,348200,290500,369100,373000,439800,564700,606100,649100],
    9.5:  [298700,384800,361600,302100,380500,384500,454800,586400,628400,674600],
    10.0: [309300,397600,375000,313700,391900,396000,469800,608100,650700,700100],
    10.5: [315000,405700,381400,322100,401200,405400,479300,622400,667400,715700],
    11.0: [320700,413800,387800,330500,410500,414800,488800,636700,684100,731300],
    11.5: [326400,421900,394200,338900,419800,424200,498300,651000,700800,746900],
    12.0: [332100,430000,400600,347300,429100,433600,507800,665300,717500,762500],
    12.5: [337800,438100,407000,355700,438400,443000,517300,679600,734200,778100],
    13.0: [343500,446200,413400,364100,447700,452400,526800,693900,750900,793700],
    13.5: [349200,454300,419800,372500,457000,461800,536300,708200,767600,809300],
    14.0: [354900,462400,426200,380900,466300,471200,545800,722500,784300,824900],
    14.5: [360600,470500,432600,389300,475600,480600,555300,736800,801000,840500],
    15.0: [366300,478600,439000,397700,484900,490000,564800,751100,817700,856100],
    15.5: [372000,486700,445400,406100,494200,499400,574300,765400,834400,871700],
    16.0: [377700,494800,451800,414500,503500,508800,583800,779700,851100,887300],
    16.5: [383400,502900,458200,422900,512800,518200,593300,794000,867800,902900],
    17.0: [389100,511000,464600,431300,522100,527600,602800,808300,884500,918500],
    17.5: [394800,519100,471000,439700,531400,537000,612300,822600,901200,934100],
    18.0: [400500,527200,477400,448100,540700,546400,621800,836900,917900,949700],
    18.5: [406200,535300,483800,456500,550000,555800,631300,851200,934600,965300],
    19.0: [411900,543400,490200,464900,559300,565200,640800,865500,951300,980900],
    19.5: [417600,551500,496600,473300,568600,574600,650300,879800,968000,996500],
    20.0: [423300,559600,503000,481700,577900,584000,659800,894100,984700,1012100],
    20.5: [429000,567700,509400,490100,587200,593400,669300,908400,1001400,1027700],
}
FXIMP_ECON_OVER = {
    "21-44":   [20700,27600,28200,25200,28300,30900,32500,46100,48900,51900],
    "45-70":   [18500,21600,23000,23200,25100,28200,29000,42200,44800,46500],
    "71-99":   [17600,19700,22900,22400,23500,25700,26200,39400,42800,44500],
    "100-299": [16400,18600,21100,21100,23000,24400,24100,39100,40900,42800],
    "300-499": [16100,17800,20000,20200,22700,23800,23200,38200,40300,42300],
    "500-999": [15900,17300,19300,20100,22700,23600,23000,38200,40300,42300],
    "1000+":   [15800,17100,19300,20100,22700,23600,23000,38200,40300,42300],
}

# ── UPS 수입 존 매핑 (국가 → 수입 Zone 1~9) ──
UPS_IMP_ZONE_MAP = {
    # ── Zone 1: 필리핀, 싱가포르 (엑셀 수입 Zone1) ──
    "Philippines":1,"Singapore":1,
    # ── Zone 2: 홍콩, 일본, 태국, 베트남 ──
    "Hong Kong SAR China":2,"Japan":2,"Thailand":2,"Vietnam":2,
    # ── Zone 3: 중국, 인도, 말레이시아, 파키스탄, 대만, 마카오, 피지 ──
    "China (People\'s Republic)":3,"India":3,"Malaysia":3,"Pakistan":3,
    "Taiwan, China":3,"Macau SAR China":3,
    # ── Zone 4: 호주, 방글라데시, 부탄, 브루나이, 캄보디아, 괌, 인도네시아,
    #            몽골, 미얀마, 네팔, 뉴질랜드, 스리랑카 ──
    "Australia":4,"Bangladesh":4,"Bhutan":4,"Brunei":4,
    "Cambodia":4,"Guam":4,"Indonesia":4,"Mongolia":4,"Myanmar":4,
    "Nepal":4,"New Zealand":4,"Sri Lanka":4,
    # ── Zone 5: 미국, 캐나다, 멕시코, 푸에르토리코 ──
    "United States of America":5,"Canada":5,"Mexico":5,"Puerto Rico":5,
    # ── Zone 6: 서유럽 ──
    "Belgium":6,"France":6,"Germany":6,"Italy":6,"Monaco":6,"Netherlands":6,
    "Spain":6,"United Kingdom":6,"Luxembourg":6,"Scotland":6,"Portugal":6,"Ireland":6,
    # ── Zone 7: 북/중부 유럽 ──
    "Austria":7,"Czech Republic":7,"Denmark":7,"Finland":7,"Greece":7,"Hungary":7,
    "Norway":7,"Poland":7,"Sweden":7,"Switzerland":7,
    # ── Zone 8: 중동/동유럽/아프리카 일부 ──
    "Algeria":8,"Angola":8,"Argentina":8,"Bahrain":8,"Iceland":8,
    "Israel":8,"Jordan":8,"Kenya":8,"Kuwait":8,"Lebanon":8,
    "Oman":8,"Qatar":8,"Romania":8,"Saudi Arabia":8,"Turkiye":8,
    "Uganda":8,"Ukraine":8,"United Arab Emirates":8,"Zambia":8,
    # ── Zone 9: 중남미/아프리카 ──
    "Afghanistan":9,"Bolivia":9,"Brazil":9,"Cameroon":9,"Chile":9,"Colombia":9,
    "Congo":9,"Dominican Republic":9,"Ecuador":9,"Egypt":9,"El Salvador":9,
    "Ethiopia":9,"Ghana":9,"Guatemala":9,"Haiti":9,"Honduras":9,
    "Jamaica":9,"Libya":9,"Madagascar":9,"Morocco":9,"Mozambique":9,
    "Nicaragua":9,"Niger":9,"Nigeria":9,"Panama":9,"Paraguay":9,"Peru":9,
    "Rwanda":9,"Senegal":9,"South Africa":9,"Sudan":9,"Tanzania":9,
    "Togo":9,"Trinidad and Tobago":9,"Tunisia":9,"Uruguay":9,"Venezuela":9,
    "Zimbabwe":9,
}

# ── UPS 수입 DOC (0.5~5.0kg, Zone 1~9) ──
UPS_IMP_DOC = {
    0.5: [49700,56900,54000,69400,70000,77600,80900,98700,120100],
    1.0: [77900,79200,79500,103800,109300,122100,129600,152300,172000],
    1.5: [104900,106400,108000,135900,145900,168600,179500,214100,224000],
    2.0: [130200,133200,135900,166900,178400,205600,226200,270300,273700],
    2.5: [158100,162200,164700,200700,216500,251600,278800,332100,324800],
    3.0: [171000,180300,184400,230900,234000,277700,305700,371700,357900],
    3.5: [182000,193800,202900,256100,250200,301800,328400,411700,387800],
    4.0: [194700,205500,219900,276300,264800,325500,350600,444600,418800],
    4.5: [202800,215100,231200,293700,280700,348500,373000,469700,450100],
    5.0: [209200,224900,242200,312100,295400,368400,395400,495400,486200],
}
# UPS 수입 NDC (0.5~20.0kg, Zone 1~9)
UPS_IMP_NDC = {
    0.5:  [134200,135700,145800,165400,155600,161800,172100,214700,218500],
    1.0:  [144300,146600,155900,179100,173500,185000,199500,253700,242200],
    1.5:  [154400,156300,166200,194100,189500,208100,227200,285500,269800],
    2.0:  [164800,166500,176400,208600,205000,231000,254200,318000,304100],
    2.5:  [173800,176300,187200,223000,220900,254200,281700,349600,338400],
    3.0:  [181900,186000,198200,240600,236400,277700,305700,383100,369000],
    3.5:  [189600,195700,209200,258700,250200,301800,328400,415900,399800],
    4.0:  [196700,205500,219900,276300,264800,325500,350600,444600,431800],
    4.5:  [202800,215100,231200,293700,280700,348500,373000,469700,464100],
    5.0:  [209200,224900,242200,312100,295400,372100,395400,495400,496100],
    5.5:  [215400,235900,252900,325800,310000,394400,418200,518400,519200],
    6.0:  [221400,246100,264200,339300,324500,410000,441200,546100,549400],
    6.5:  [227000,257100,275000,353200,338900,425600,463400,576200,579700],
    7.0:  [232700,267300,285700,367000,353000,441300,486500,606000,609700],
    7.5:  [237800,278200,296900,380900,365400,456600,509000,636000,640100],
    8.0:  [247200,287400,306800,394500,379400,472900,534100,662300,666100],
    8.5:  [256600,296600,316500,408000,393200,488000,558900,689000,692900],
    9.0:  [266300,305800,326300,421900,406800,503600,583700,715400,719300],
    9.5:  [276300,314700,336400,435800,420600,519300,608800,742000,746100],
    10.0: [285900,323900,346500,449800,434600,534600,633500,776200,780400],
    10.5: [295700,330500,353400,460700,444900,547400,655700,802500,807000],
    11.0: [305300,343500,360500,472000,455800,560800,677700,828900,828700],
    11.5: [315000,357100,368000,483100,466700,573900,699300,861800,864000],
    12.0: [322100,371000,375300,494400,477000,586800,721400,890900,892300],
    12.5: [328000,385000,385800,505900,488100,600200,743000,923700,920300],
    13.0: [333900,398800,392200,517000,499100,613100,765200,948300,947500],
    13.5: [340100,412400,405300,528800,509500,626400,785400,968000,964700],
    14.0: [346100,424500,419800,540100,520000,639700,807600,983700,981300],
    14.5: [351900,432200,434200,551600,531000,652900,829500,1002600,1007900],
    15.0: [357800,439400,448700,562900,541700,666000,851600,1028500,1034000],
    15.5: [363900,440600,462800,567500,552300,681700,860300,1058700,1064300],
    16.0: [370400,443100,467600,572800,562500,699300,868900,1088800,1094800],
    16.5: [376100,444800,468500,578100,573100,720300,878000,1118800,1125100],
    17.0: [382400,445900,469500,582900,583400,741300,886500,1149100,1155800],
    17.5: [388600,447200,472300,587500,590800,760400,894900,1178700,1185700],
    18.0: [393100,448700,472600,592200,598500,780400,912400,1196100,1202800],
    18.5: [397100,449800,472900,596500,606300,798400,929700,1213800,1217200],
    19.0: [401600,451500,473900,601200,620300,817200,946000,1228800,1243900],
    19.5: [410000,453100,474600,605300,631700,835900,962000,1243900,1271000],
    20.0: [420400,454400,476000,612500,647000,852900,977200,1263600,1302400],
}
UPS_IMP_OVER = {
    "21-44":  [21000,22500,23600,30500,31800,42600,48000,62200,63800],
    "45-70":  [21000,22500,23600,30500,31800,42600,45100,62200,63800],
    "71-99":  [19100,20900,22500,29100,30000,41300,42900,61400,62600],
    "100-299":[19100,20900,22500,28600,30000,41300,42900,61400,62600],
    "300-499":[17900,19500,21900,27100,29100,40900,42000,59800,56300],
    "500-999":[17900,19500,21900,27100,29100,40900,42000,59800,56300],
    "1000+":  [17900,19500,21900,27100,29100,40900,42000,59800,56300],
}


# ══════════════════════════════════════════════════════════
# UPS 수입 원가 테이블 — 2계정 분리
# 2F94A8 (Q6438503KR) / B8733R (Q9240598KR)
# Zone 1~9  ← UPS_IMP_ZONE_MAP 기준
# ══════════════════════════════════════════════════════════

# ── 2F94A8 수입 원가: 서류(DOC ≤5.0kg) Zone 1~9 ──
UPS_IMP_2F_DOC = {
    # Zone:    1      2      3      4      5      6      7      8      9
    0.5: [14910,17070,16200,27760,22600,23280,24270,29610,36030],
    1.0: [23370,23760,23850,41520,32790,36630,38880,45690,51600],
    1.5: [31470,31920,32400,54360,43770,50580,53850,64230,67200],
    2.0: [39060,39960,40770,66760,53520,61680,67860,81090,82110],
    2.5: [47430,48660,49410,80280,64950,75480,83640,99630,97440],
    3.0: [51300,54090,55320,92360,70200,83310,91710,111510,107370],
    3.5: [54600,58140,60870,102440,75060,90540,98520,123510,116340],
    4.0: [58410,61650,65970,110520,79440,97650,105180,133380,125640],
    4.5: [60840,64530,69360,117480,84210,104550,111900,140910,135030],
    5.0: [62760,67470,72660,124840,88620,110520,118620,148620,145860],
}
# ── 2F94A8 수입 원가: 물품(PKG, 0.5~20.0kg) Zone 1~9 ──
UPS_IMP_2F_PKG = {
    # Zone:     1      2      3      4      5      6      7      8      9
    0.5:  [40260,40710,43740,66160,46680,48540,51630,64410,65550],
    1.0:  [43290,43980,46770,71640,52050,55500,59850,76110,72660],
    1.5:  [46320,46890,49860,77640,56850,62430,68160,85650,80940],
    2.0:  [49440,49950,52920,83440,61500,69300,76260,95400,91230],
    2.5:  [52140,52890,56160,89200,66270,76260,84510,104880,101520],
    3.0:  [54570,55800,59460,96240,70920,83310,91710,114930,110700],
    3.5:  [56880,58710,62760,103480,75060,90540,98520,124770,119940],
    4.0:  [59010,61650,65970,110520,79440,97650,105180,133380,129540],
    4.5:  [60840,64530,69360,117480,84210,104550,111900,140910,139230],
    5.0:  [62760,67470,72660,124840,88620,111630,118620,148620,148830],
    5.5:  [64620,70770,75870,130320,93000,118320,125460,155520,155760],
    6.0:  [66420,73830,79260,135720,97350,123000,132360,163830,164820],
    6.5:  [68100,77130,82500,141280,101670,127680,139020,172860,173910],
    7.0:  [69810,80190,85710,146800,105900,132390,145950,181800,182910],
    7.5:  [71340,83460,89070,152360,109620,136980,152700,190800,192030],
    8.0:  [74160,86220,92040,157800,113820,141870,160230,198690,199830],
    8.5:  [76980,88980,94950,163200,117960,146400,167670,206700,207870],
    9.0:  [79890,91740,97890,168760,122040,151080,175110,214620,215790],
    9.5:  [82890,94410,100920,174320,126180,155790,182640,222600,223830],
    10.0: [85770,97170,103950,179920,130380,160380,190050,232860,234120],
    10.5: [88710,99150,106020,184280,133470,164220,196710,240750,242100],
    11.0: [91590,103050,108150,188800,136740,168240,203310,248670,248610],
    11.5: [94500,107130,110400,193240,140010,172170,209790,258540,259200],
    12.0: [96630,111300,112590,197760,143100,176040,216420,267270,267690],
    12.5: [98400,115500,115740,202360,146430,180060,222900,277110,276090],
    13.0: [100170,119640,117660,206800,149730,183930,229560,284490,284250],
    13.5: [102030,123720,121590,211520,152850,187920,235620,290400,289410],
    14.0: [103830,127350,125940,216040,156000,191910,242280,295110,294390],
    14.5: [105570,129660,130260,220640,159300,195870,248850,300780,302370],
    15.0: [107340,131820,134610,225160,162510,199800,255480,308550,310200],
    15.5: [109170,132180,138840,227000,165690,204510,258090,317610,319290],
    16.0: [111120,132930,140280,229120,168750,209790,260670,326640,328440],
    16.5: [112830,133440,140550,231240,171930,216090,263400,335640,337530],
    17.0: [114720,133770,140850,233160,175020,222390,265950,344730,346740],
    17.5: [116580,134160,141690,235000,177240,228120,268470,353610,355710],
    18.0: [117930,134610,141780,236880,179550,234120,273720,358830,360840],
    18.5: [119130,134940,141870,238600,181890,239520,278910,364140,365160],
    19.0: [120480,135450,142170,240480,186090,245160,283800,368640,373170],
    19.5: [123000,135930,142380,242120,189510,250770,288600,373170,381300],
    20.0: [126120,136320,142800,245000,194100,255870,293160,379080,390720],
}
# ── 2F94A8 수입 원가: 초과중량(20kg+) kg당 Zone 1~9 ──
UPS_IMP_2F_OVER = {
    #  max_kg: Zone 1~9
    44:      [6300,6750,7080,12200,9540,12780,14400,18660,19140],
    70:      [6300,6750,7080,12200,9540,12780,13530,18660,19140],
    99:      [5730,6270,6750,11640,9000,12390,12870,18420,18780],
    299:     [5730,6270,6750,11440,9000,12390,12870,18420,18780],
    499:     [5370,5850,6570,10840,8730,12270,12600,17940,16890],
    999:     [5370,5850,6570,10840,8730,12270,12600,17940,16890],
    9999999: [5370,5850,6570,10840,8730,12270,12600,17940,16890],
}

# ── B8733R 수입 원가: 서류(DOC ≤5.0kg) Zone 1~9 ──
UPS_IMP_B8_DOC = {
    # Zone:    1      2      3      4      5      6      7      8      9
    0.5: [23359,26743,25380,32618,32900,36472,38023,46389,56447],
    1.0: [36613,37224,37365,48786,51371,57387,60912,71581,80840],
    1.5: [49303,50008,50760,63873,68573,79242,84365,100627,105280],
    2.0: [61194,62604,63873,78443,83848,96632,106314,127041,128639],
    2.5: [74307,76234,77409,94329,101755,118252,131036,156087,152656],
    3.0: [80370,84741,86668,108523,109980,130519,143679,174699,168213],
    3.5: [85540,91086,95363,120367,117594,141846,154348,193499,182266],
    4.0: [91509,96585,103353,129861,124456,152985,164782,208962,196836],
    4.5: [95316,101097,108664,138039,131929,163795,175310,220759,211547],
    5.0: [98324,105703,113834,146687,138838,173148,185838,232838,228514],
}
# ── B8733R 수입 원가: 물품(PKG, 0.5~20.0kg) Zone 1~9 ──
UPS_IMP_B8_PKG = {
    # Zone:     1       2       3       4       5       6       7       8       9
    0.5:  [ 67100, 67850, 72900, 82700, 77800, 80900, 86050,107350,109250],
    1.0:  [ 72150, 73300, 77950, 89550, 86750, 92500, 99750,126850,121100],
    1.5:  [ 77200, 78150, 83100, 97050, 94750,104050,113600,142750,134900],
    2.0:  [ 82400, 83250, 88200,104300,102500,115500,127100,159000,152050],
    2.5:  [ 86900, 88150, 93600,111500,110450,127100,140850,174800,169200],
    3.0:  [ 90950, 93000, 99100,120300,118200,138850,152850,191550,184500],
    3.5:  [ 94800, 97850,104600,129350,125100,150900,164200,207950,199900],
    4.0:  [ 98350,102750,109950,138150,132400,162750,175300,222300,215900],
    4.5:  [101400,107550,115600,146850,140350,174250,186500,234850,232050],
    5.0:  [104600,112450,121100,156050,147700,186050,197700,247700,248050],
    5.5:  [107700,117950,126450,162900,155000,197200,209100,259200,259600],
    6.0:  [110700,123050,132100,169650,162250,205000,220600,273050,274700],
    6.5:  [113500,128550,137500,176600,169450,212800,231700,288100,289850],
    7.0:  [116350,133650,142850,183500,176500,220650,243250,303000,304850],
    7.5:  [118900,139100,148450,190450,182700,228300,254500,318000,320050],
    8.0:  [123600,143700,153400,197250,189700,236450,267050,331150,333050],
    8.5:  [128300,148300,158250,204000,196600,244000,279450,344500,346450],
    9.0:  [133150,152900,163150,210950,203400,251800,291850,357700,359650],
    9.5:  [138150,157350,168200,217900,210300,259650,304400,371000,373050],
    10.0: [142950,161950,173250,224900,217300,267300,316750,388100,390200],
    10.5: [147850,165250,176700,230350,222450,273700,327850,401250,403500],
    11.0: [152650,171750,180250,236000,227900,280400,338850,414450,414350],
    11.5: [157500,178550,184000,241550,233350,286950,349650,430900,432000],
    12.0: [161050,185500,187650,247200,238500,293400,360700,445450,446150],
    12.5: [164000,192500,192900,252950,244050,300100,371500,461850,460150],
    13.0: [166950,199400,196100,258500,249550,306550,382600,474150,473750],
    13.5: [170050,206200,202650,264400,254750,313200,392700,484000,482350],
    14.0: [173050,212250,209900,270050,260000,319850,403800,491850,490650],
    14.5: [175950,216100,217100,275800,265500,326450,414750,501300,503950],
    15.0: [178900,219700,224350,281450,270850,333000,425800,514250,517000],
    15.5: [181950,220300,231400,283750,276150,340850,430150,529350,532150],
    16.0: [185200,221550,233800,286400,281250,349650,434450,544400,547400],
    16.5: [188050,222400,234250,289050,286550,360150,439000,559400,562550],
    17.0: [191200,222950,234750,291450,291700,370650,443250,574550,577900],
    17.5: [194300,223600,236150,293750,295400,380200,447450,589350,592850],
    18.0: [196550,224350,236300,296100,299250,390200,456200,598050,601400],
    18.5: [198550,224900,236450,298250,303150,399200,464850,606900,608600],
    19.0: [200800,225750,236950,300600,310150,408600,473000,614400,621950],
    19.5: [205000,226550,237300,302650,315850,417950,481000,621950,635500],
    20.0: [210200,227200,238000,306250,323500,426450,488600,631800,651200],
}
# ── B8733R 수입 원가: 초과중량(20kg+) kg당 Zone 1~9 ──
UPS_IMP_B8_OVER = {
    #  max_kg: Zone 1~9
    44:      [10500,11250,11800,15250,15900,21300,24000,31100,31900],
    70:      [10500,11250,11800,15250,15900,21300,22550,31100,31900],
    99:      [ 9550,10450,11250,14550,15000,20650,21450,30700,31300],
    299:     [ 9550,10450,11250,14300,15000,20650,21450,30700,31300],
    499:     [ 8950, 9750,10950,13550,14550,20450,21000,29900,28150],
    999:     [ 8950, 9750,10950,13550,14550,20450,21000,29900,28150],
    9999999: [ 8950, 9750,10950,13550,14550,20450,21000,29900,28150],
}

# ══════════════════════════════════════════════════════════
# 수입 Lookup 함수
# ══════════════════════════════════════════════════════════
def dhl_imp_lookup(w, zi, is_doc=False):
    """DHL 수입 요금 조회 (공시가)"""
    if is_doc and w <= 2.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(DHL_IMP_DOX[key][zi] for key in sorted(DHL_IMP_DOX) if key >= k))
    elif w <= 30.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(DHL_IMP_NDC[key][zi] for key in sorted(DHL_IMP_NDC) if key >= k))
    else:
        rw = math.ceil(w)
        if rw <= 70:   br = "30-70"
        elif rw <= 300:br = "70-300"
        else:          br = "300+"
        return ceil10(DHL_IMP_OVER[br][zi] * rw)

def fximp_lookup(w, zi, is_doc=False, econ=False):
    """FedEx 수입 요금 조회 (공시가, 10원 올림)"""
    # IP만 Envelope/PAK 있음 (Economy 수입은 서류도 NDC 요금 적용)
    if not econ:
        if is_doc and w <= 0.5:
            return ceil10(FXIMP_ENV[0.5][zi])
        if is_doc and w <= 2.5:
            k = math.ceil(w * 2) / 2
            return ceil10(next(FXIMP_PAK[key][zi] for key in sorted(FXIMP_PAK) if key >= k))
    tbl  = FXIMP_ECON      if econ else FXIMP_IP
    over = FXIMP_ECON_OVER if econ else FXIMP_OVER
    if w <= 20.5:
        k = math.ceil(w * 2) / 2
        return ceil10(next(tbl[key][zi] for key in sorted(tbl) if key >= k))
    rw = int(math.ceil(w))
    if rw <= 44:    br = "21-44"
    elif rw <= 70:  br = "45-70"
    elif rw <= 99:  br = "71-99"
    elif rw <= 299: br = "100-299"
    elif rw <= 499: br = "300-499"
    elif rw <= 999: br = "500-999"
    else:           br = "1000+"
    return ceil10(over[br][zi] * rw)

def ups_imp_lookup(w, zi, is_doc=False):
    """UPS 수입 공시가 조회"""
    if is_doc and w <= 5.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(UPS_IMP_DOC[key][zi] for key in sorted(UPS_IMP_DOC) if key >= k))
    if w <= 20.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(UPS_IMP_NDC[key][zi] for key in sorted(UPS_IMP_NDC) if key >= k))
    rw = int(math.ceil(w))
    if rw <= 44:    br = "21-44"
    elif rw <= 70:  br = "45-70"
    elif rw <= 99:  br = "71-99"
    elif rw <= 299: br = "100-299"
    elif rw <= 499: br = "300-499"
    elif rw <= 999: br = "500-999"
    else:           br = "1000+"
    return ceil10(UPS_IMP_OVER[br][zi] * rw)


def dhl_imp_cost_lookup(w, zi, is_doc=False):
    """DHL 수입 원가 조회 (에어브리지 계약 원가 테이블 직접 참조)"""
    if is_doc and w <= 2.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(DHL_IMP_COST_DOX[key][zi] for key in sorted(DHL_IMP_COST_DOX) if key >= k))
    if w <= 30.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(DHL_IMP_COST_NDC[key][zi] for key in sorted(DHL_IMP_COST_NDC) if key >= k))
    rw = math.ceil(w)
    if rw <= 70:    br = "30-70"
    elif rw <= 300: br = "70-300"
    else:           br = "300+"
    return ceil10(DHL_IMP_COST_OVER[br][zi] * rw)

def ups_imp_cost_lookup(w, zi, is_doc=False, acct="2F94A8"):
    """UPS 수입 원가 조회 (계정별 계약 원가 테이블)"""
    doc_tbl  = UPS_IMP_2F_DOC  if acct == "2F94A8" else UPS_IMP_B8_DOC
    pkg_tbl  = UPS_IMP_2F_PKG  if acct == "2F94A8" else UPS_IMP_B8_PKG
    over_tbl = UPS_IMP_2F_OVER if acct == "2F94A8" else UPS_IMP_B8_OVER
    if is_doc and w <= 5.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(doc_tbl[key][zi] for key in sorted(doc_tbl) if key >= k))
    if w <= 20.0:
        k = math.ceil(w * 2) / 2
        return ceil10(next(pkg_tbl[key][zi] for key in sorted(pkg_tbl) if key >= k))
    rw = int(math.ceil(w))
    return ceil10(next(over_tbl[mw][zi] * rw for mw in sorted(over_tbl) if rw <= mw))



# ══════════════════════════════════════════════════════════
# 수입 내부 매입할인율 (항공사 계약 할인 — 원가 계산 기준)
# 고객 청구가는 별도 "고객 할인율"로 설정
# ══════════════════════════════════════════════════════════
# 아래 값은 session_state 에서 읽어와 사이드바에서 수정 가능
# 기본값 정의는 _DEFAULTS 딕셔너리 참고
IMP_BUYRATE_DEFAULT_DHL      = 50.0
IMP_BUYRATE_DEFAULT_FEDEX_IP = 35.0
IMP_BUYRATE_DEFAULT_FEDEX_EC = 0.0
IMP_BUYRATE_DEFAULT_UPS      = 0.0

# ═══════════════════════════════════════════════════
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
def generate_pdf(quote_num, customer, dest_country, zone_label, ct_count,
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
    def pdf_disp(name):
        if "UPS" in name: return "UPS"
        return name

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

    d.text((logo_end_x, 40),  "국제특송 운임견적서",       font=fnt(52, bold=True), fill='#ffffff')
    d.text((logo_end_x, 118), "FREIGHT RATE QUOTATION",   font=fnt(30),            fill='#bfdbfe')

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

    sel_names_raw = [n for n, v in selected.items() if v]

    # UPS는 무조건 단일 "UPS"로 표기
    seen_ups = False
    sel_names = []
    for n in sel_names_raw:
        if "UPS" in n:
            if not seen_ups:
                sel_names.append(n)
                seen_ups = True
        else:
            sel_names.append(n)
    ups_both = seen_ups and sum(1 for n in sel_names_raw if "UPS" in n) >= 2

    fuel_items = []
    for nm in sel_names_raw:
        if "DHL"   in nm and f"DHL {fuel_dhl}%"     not in fuel_items: fuel_items.append(f"DHL {fuel_dhl:.2f}%")
        if "FedEx" in nm and f"FedEx {fuel_fedex}%" not in fuel_items: fuel_items.append(f"FedEx {fuel_fedex:.2f}%")
        if "UPS"   in nm and f"UPS {fuel_ups}%"     not in fuel_items: fuel_items.append(f"UPS {fuel_ups:.2f}%")

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
        ("목 적 지", dest_country),
        ("운송 구분", _mode_str),
        ("화물 구분", _cargo_type_str),
        ("적용 Zone", _zone_short),
    ]
    info_R = [
        ("견적번호", quote_num),
        ("견적일자", datetime.now().strftime("%Y년 %m월 %d일")),
        ("유효기간", "발행일로부터 7일"),
        ("선택운송사", _carrier_str),
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

            # CARD_H를 is_nsvc 여부와 관계없이 먼저 계산
            if is_nsvc:
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
        LBL_W = 360
        RH    = 86

        name_groups = [sel_names[i:i+2] for i in range(0, len(sel_names), 2)]
        for gi, group in enumerate(name_groups):
            nc = len(group)
            col_w = (W - PAD*2 - LBL_W) // nc
            if gi > 0: y += 20
            y = draw_section_bar(y, f"  운임 비교표 ({gi+1}/{len(name_groups)})" if len(name_groups)>1 else "  운임 비교표")

            d.rectangle([PAD, y, W-PAD, y+RH+16], fill='#1e3a8a')
            d.text((PAD+28, y+22), "구분", font=fnt(34, bold=True), fill='#aabbdd')
            for i, name in enumerate(group):
                cx = PAD+LBL_W+i*col_w
                color, _ = CC_TBL.get(name, ('#333','#fff'))
                d.rectangle([cx, y, cx+col_w-2, y+RH+16], fill=color)
                d.text((cx+24, y+22), pdf_disp(name), font=fnt(34, bold=True), fill='white')
            y += RH+16

            all_pdf_sur_names = []
            for pn in group:
                for s_nm in results.get(pn,{}).get("surs_detail",{}).keys():
                    if s_nm not in all_pdf_sur_names:
                        all_pdf_sur_names.append(s_nm)

            rdefs = [
                ("항공운임", lambda r: r.get("pub_disc",0), False, False),
                ("  └ 단가/kg", lambda r: r.get("rate_info",{}).get("disc_rpk") or r.get("rate_info",{}).get("rate_per_kg") or 0, False, True),
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
                rh_row = RH-16 if is_indent else RH
                bg = '#eff6ff' if is_hl else ('#f8faff' if is_indent else ('#f5f8ff' if ri2%2==0 else '#ffffff'))
                d.rectangle([PAD, y, W-PAD, y+rh_row], fill=bg)
                lpad = PAD+54 if is_indent else PAD+28
                fs   = 28 if is_indent else 34
                fc   = '#94a3b8' if is_indent else ('#334155' if not is_hl else '#1e3a8a')
                d.text((lpad, y+(14 if is_indent else 22)), label.strip(), font=fnt(fs, bold=is_hl), fill=fc)
                for i, name in enumerate(group):
                    r = results.get(name, {})
                    color, _ = CC_TBL.get(name, ('#333','#fff'))
                    cx = PAD+LBL_W+i*col_w
                    if r.get("no_service"):
                        ra("서비스불가", fnt(28, bold=False), cx+col_w-22, y+(14 if is_indent else 22), '#b91c1c')
                        continue
                    v = vfn(r)
                    _is_rpk_lbl = label.strip().startswith("└ 단가/kg")
                    if _is_rpk_lbl:
                        val_str = (f"{int(v):,}원/kg" if v and v > 0 else "-")
                    else:
                        val_str = fmt(v) if v != 0 else "-"
                    vc = '#aabbcc' if is_indent and v==0 else (color if is_hl else ('#99aabb' if is_indent else '#2a3a4a'))
                    ra(val_str, fnt(fs, bold=is_hl), cx+col_w-22, y+(14 if is_indent else 22), vc)
                d.line([PAD, y+rh_row, W-PAD, y+rh_row], fill='#e8eaf0', width=1)
                y += rh_row

            d.rectangle([PAD, y, W-PAD, y+RH], fill='#eff6ff')
            d.text((PAD+28, y+22), "T/T (예상)", font=fnt(34, bold=True), fill='#1e3a8a')
            for i, name in enumerate(group):
                cx = PAD+LBL_W+i*col_w
                d.text((cx+22, y+22), TT.get(name,"-"), font=fnt(34), fill='#2563eb')
            y += RH + 24

        min_nm = min(
            [n for n in sel_names if not results.get(n,{}).get("no_service")],
            key=lambda n: results.get(n,{}).get("total_quote", float('inf')),
            default=sel_names[0]
        )
        min_q  = results.get(min_nm,{}).get("total_quote",0)
        d.rectangle([PAD, y, W-PAD, y+78], fill='#ecfdf5')
        d.rectangle([PAD, y, PAD+9,  y+78], fill='#059669')
        d.text((PAD+28, y+10), "[ 최저 견적 추천 ]",                    font=fnt(28, bold=True), fill='#065f46')
        d.text((PAD+28, y+44), f"  {pdf_disp(min_nm)}  →  {fmt(min_q)}", font=fnt(28),            fill='#047857')
        y += 90

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
# 상태 초기화 — 모든 영구 보존값 여기서 한 번만 세팅
# ═══════════════════════════════════════════════════
_DEFAULTS = {
    "pkg_types":    1,
    "qty_0": 1, "qty_1": 1, "qty_2": 1, "qty_3": 1, "qty_4": 1,
    "mode":        "수출",          # 수출 / 수입
    # 수출 유류/할인
    "fuel_dhl":   28.75,
    "fuel_fedex": 29.75,
    "fuel_ups":   29.50,
    "disc_dhl":    50.0,
    "disc_fedex":   0.0,
    "disc_fedex_e": 0.0,
    "disc_ups":     0.0,
    "tgt_margin":  30.0,
    # 수입 전용 — UPS B8733R 할인율만 별도 (수출에는 UPS 계정 구분 없음)
    "imp_disc_ups_b8":   0.0,
    # ※ 유류할증료·DHL/FedEx 할인율·목표마진은 수출키(fuel_dhl 등)를 공유사용
    "our_company":  "(주)에어브리지",
    "our_contact":  "",
    "our_phone":    "",
    "our_email":    "",
}
# [프로그래머A] 초기화: 파일 저장값 강제 우선 적용
# "최초 1회" 보호는 __settings_loaded__ 플래그로 처리
if "settings_loaded" not in st.session_state:
    for _k, _v in _DEFAULTS.items():
        # 파일에 저장된 값이 있으면 무조건 파일값 적용 (기본값 무시)
        st.session_state[_k] = _SAVED.get(_k, _v)
    st.session_state["settings_loaded"] = True
else:
    # 이후 렌더: 없는 키만 기본값으로 채움 (위젯 변경값 유지)
    for _k, _v in _DEFAULTS.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v

# ═══════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════

# ════════════════════════════════════════════════════════
# Windows 11 Fluent Design — 테마 딕셔너리
# 수출(exp): 딥 인디고 블루  |  수입(imp): 딥 로즈/크림슨
# ════════════════════════════════════════════════════════
_IS_IMP = (st.session_state.get("mode","수출") == "수입")
_T = {
    # 사이드바 로고 그라데이션
    "sb_grad_a":    "#9f1239" if _IS_IMP else "#1d4ed8",
    "sb_grad_b":    "#e11d48" if _IS_IMP else "#2563eb",
    "sb_grad_c":    "#fb7185" if _IS_IMP else "#3b82f6",
    # 사이드바 섹션 박스 border
    "sb_border":    "rgba(251,113,133,.22)" if _IS_IMP else "rgba(96,165,250,.15)",
    "sb_border2":   "rgba(251,113,133,.25)" if _IS_IMP else "rgba(96,165,250,.2)",
    "sb_accent":    "#e11d48"               if _IS_IMP else "#3b82f6",
    # 섹션 타이틀 / 레이블 텍스트
    "sb_title":     "#fb7185"               if _IS_IMP else "#60a5fa",
    "sb_label":     "#fda4af"               if _IS_IMP else "#93c5fd",
    # C/T 배지
    "sb_ct_bg":     "rgba(225,29,72,.08)"   if _IS_IMP else "rgba(37,99,235,.08)",
    "sb_ct_fg":     "#9f1239"               if _IS_IMP else "#1e3a8a",
    "sb_ct_bdr":    "#fda4af"               if _IS_IMP else "#bfdbfe",
    # 메인 영역 accent
    "main_accent":       "#e11d48"          if _IS_IMP else "#3b82f6",
    "main_accent_dark":  "#9f1239"          if _IS_IMP else "#1e3a8a",
    # T/T 배지 (카드)
    "tt_color":     "#e11d48"               if _IS_IMP else "#2563eb",
    "tt_bg":        "rgba(225,29,72,.10)"   if _IS_IMP else "rgba(37,99,235,.10)",
    # 비교표 헤더
    "tbl_hdr_bg":   "linear-gradient(135deg,#4c0519,#9f1239)" if _IS_IMP else "linear-gradient(135deg,#1e3a8a,#2563eb)",
    "tbl_hdr_sub":  "#f9a8b8"               if _IS_IMP else "#aabbdd",
}
# 짧은 alias (f-string 내 사용)
_sb_border=_T["sb_border"]; _sb_border2=_T["sb_border2"]; _sb_accent=_T["sb_accent"]
_sb_title=_T["sb_title"];   _sb_label=_T["sb_label"]
_sb_ct_bg=_T["sb_ct_bg"];   _sb_ct_fg=_T["sb_ct_fg"];    _sb_ct_bdr=_T["sb_ct_bdr"]
_main_accent=_T["main_accent"]; _main_accent_dark=_T["main_accent_dark"]
_tt_color=_T["tt_color"];   _tt_bg=_T["tt_bg"]
_tbl_hdr_bg=_T["tbl_hdr_bg"]; _tbl_hdr_sub=_T["tbl_hdr_sub"]
_sb_grad_a=_T["sb_grad_a"]; _sb_grad_b=_T["sb_grad_b"]; _sb_grad_c=_T["sb_grad_c"]

with st.sidebar:
    # ── 로고 헤더 ──
    st.markdown(f"""<div style="background:linear-gradient(135deg,{_sb_grad_a},{_sb_grad_b},{_sb_grad_c});
        border-radius:12px;padding:16px;text-align:center;margin-bottom:4px;
        box-shadow:0 4px 20px rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.12);">
        <span style="color:#ffffff;font-size:1.15rem;font-weight:900;letter-spacing:.12em;">✈ AIRBRIDGE</span>
        <div style="color:#93c5fd;font-size:.65rem;margin-top:3px;letter-spacing:.06em;">국제특송 운임계산기 v5.0</div>
    </div>""", unsafe_allow_html=True)

    # ── 수출 / 수입 모드 선택 ──
    st.markdown(f"""<div style="background:rgba(255,255,255,.05);border:1px solid {_sb_border2};
        border-radius:10px;padding:10px 10px 8px;margin-bottom:8px;">
        <div style="font-size:.68rem;color:{_sb_title};font-weight:700;text-align:center;
        margin-bottom:8px;letter-spacing:.08em;">▶ 계산 모드 선택</div>""", unsafe_allow_html=True)
    mode_cols = st.columns(2)
    with mode_cols[0]:
        if st.button("✈ 수  출", key="btn_exp", use_container_width=True,
                     type="primary" if st.session_state.get("mode","수출")=="수출" else "secondary"):
            _save_settings()
            st.session_state["mode"] = "수출"
            st.rerun()
    with mode_cols[1]:
        if st.button("📦 수  입", key="btn_imp", use_container_width=True,
                     type="primary" if st.session_state.get("mode","수출")=="수입" else "secondary"):
            _save_settings()
            st.session_state["mode"] = "수입"
            st.rerun()
    mode = st.session_state.get("mode", "수출")
    st.markdown(f'''<div data-airbridge-mode="{'imp' if mode=='수입' else 'exp'}"
        style="text-align:center;font-size:.68rem;
        color:{"#fda4af" if mode=="수입" else "#60a5fa"};font-weight:800;
        margin:6px 0 0;background:{"rgba(225,29,72,.12)" if mode=="수입" else "rgba(96,165,250,.12)"};
        border-radius:6px;padding:4px;">
        {"📦 수입 모드" if mode=="수입" else "✈ 수출 모드"}
        </div></div>''', unsafe_allow_html=True)
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    # ── 기본 정보 섹션 ──
    st.markdown(f"""<div style="background:rgba(255,255,255,.04);border:1px solid {_sb_border};
        border-left:3px solid {_sb_accent};border-radius:8px;padding:8px 10px 2px;margin-bottom:6px;">
        <div style="font-size:.68rem;color:{_sb_title};font-weight:700;letter-spacing:.07em;margin-bottom:6px;">
        📋 기본 정보</div>""", unsafe_allow_html=True)
    customer  = st.text_input("고객명 (수신)", placeholder="(주)고객사명", key="customer_input")
    quote_num = st.text_input("견적번호", value=f"AB-{datetime.now().strftime('%Y%m%d')}-001", key="quote_num")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 담당자 정보 섹션 ──
    st.markdown(f"""<div style="background:rgba(255,255,255,.04);border:1px solid {_sb_border};
        border-left:3px solid {_sb_accent};border-radius:8px;padding:8px 10px 2px;margin-bottom:6px;">
        <div style="font-size:.68rem;color:{_sb_label};font-weight:700;letter-spacing:.07em;margin-bottom:6px;">
        🏢 담당자 정보</div>
        <div style="font-size:.62rem;color:#64748b;margin-bottom:4px;">PDF 견적서에 표시됩니다</div>""",
        unsafe_allow_html=True)
    our_company = st.text_input("회사명",   key="our_company")
    our_contact = st.text_input("담당자명", key="our_contact")
    our_phone   = st.text_input("연락처",   key="our_phone",   placeholder="02-1234-5678")
    our_email   = st.text_input("이메일",   key="our_email",   placeholder="airbridge@example.com")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 목적지 섹션 ──
    st.markdown(f"""<div style="background:rgba(255,255,255,.04);border:1px solid {_sb_border};
        border-left:3px solid {_sb_accent};border-radius:8px;padding:8px 10px 2px;margin-bottom:6px;">
        <div style="font-size:.68rem;color:{_sb_label};font-weight:700;letter-spacing:.07em;margin-bottom:6px;">
        🌏 목적지 / 발송지</div>""", unsafe_allow_html=True)

    # 목적지: 한/영 병기 (한국어명 (영어명) 형식)
    COUNTRY_KR = {
        "Albania":"알바니아","Algeria":"알제리","American Samoa":"아메리칸사모아",
        "Andorra":"안도라","Angola":"앙골라","Argentina":"아르헨티나","Armenia":"아르메니아",
        "Australia":"호주","Austria":"오스트리아","Azerbaijan":"아제르바이잔",
        "Bahamas":"바하마","Bahrain":"바레인","Bangladesh":"방글라데시","Belarus":"벨라루스",
        "Belgium":"벨기에","Belize":"벨리즈","Benin":"베냉","Bhutan":"부탄","Bolivia":"볼리비아",
        "Brazil":"브라질","Brunei":"브루나이","Bulgaria":"불가리아","Burkina Faso":"부르키나파소",
        "Burundi":"부룬디","Cambodia":"캄보디아","Cameroon":"카메룬","Canada":"캐나다",
        "Chile":"칠레","China (People's Republic)":"중국","Colombia":"콜롬비아",
        "Costa Rica":"코스타리카","Croatia":"크로아티아","Cuba":"쿠바","Cyprus":"키프로스",
        "Czech Republic":"체코","Denmark":"덴마크","Dominican Republic":"도미니카공화국",
        "Ecuador":"에콰도르","Egypt":"이집트","El Salvador":"엘살바도르","Estonia":"에스토니아",
        "Ethiopia":"에티오피아","Fiji":"피지","Finland":"핀란드","France":"프랑스",
        "Gabon":"가봉","Georgia":"조지아","Germany":"독일","Ghana":"가나","Greece":"그리스",
        "Guatemala":"과테말라","Guinea":"기니","Haiti":"아이티","Honduras":"온두라스",
        "Hong Kong SAR China":"홍콩","Hungary":"헝가리","Iceland":"아이슬란드","India":"인도",
        "Indonesia":"인도네시아","Iran, Islamic Rep. of":"이란","Iraq":"이라크","Ireland":"아일랜드","Israel":"이스라엘",
        "Italy":"이탈리아","Jamaica":"자메이카","Japan":"일본","Jordan":"요르단",
        "Kazakhstan":"카자흐스탄","Kenya":"케냐","Kuwait":"쿠웨이트","Lao P.D.R.":"라오스",
        "Latvia":"라트비아","Lebanon":"레바논","Liechtenstein":"리히텐슈타인",
        "Lithuania":"리투아니아","Luxembourg":"룩셈부르크","Macau SAR China":"마카오",
        "Madagascar":"마다가스카르","Malaysia":"말레이시아","Maldives":"몰디브","Malta":"몰타",
        "Martinique":"마르티니크","Mauritius":"모리셔스","Mexico":"멕시코","Moldova":"몰도바",
        "Monaco":"모나코","Mongolia":"몽골","Montenegro":"몬테네그로","Morocco":"모로코",
        "Mozambique":"모잠비크","Myanmar":"미얀마","Namibia":"나미비아","Nepal":"네팔",
        "Netherlands":"네덜란드","New Zealand":"뉴질랜드","Nicaragua":"니카라과","Niger":"니제르",
        "Nigeria":"나이지리아","Norway":"노르웨이","Oman":"오만","Pakistan":"파키스탄",
        "Panama":"파나마","Papua New Guinea":"파푸아뉴기니","Paraguay":"파라과이","Peru":"페루",
        "Philippines":"필리핀","Poland":"폴란드","Portugal":"포르투갈","Puerto Rico":"푸에르토리코",
        "Qatar":"카타르","Romania":"루마니아","Russia":"러시아","Rwanda":"르완다",
        "Saudi Arabia":"사우디아라비아","Senegal":"세네갈","Serbia":"세르비아",
        "Singapore":"싱가포르","Slovakia":"슬로바키아","Slovenia":"슬로베니아",
        "South Africa":"남아프리카공화국","Spain":"스페인","Sri Lanka":"스리랑카","Sudan":"수단",
        "Sweden":"스웨덴","Switzerland":"스위스","Syria":"시리아","Taiwan, China":"대만",
        "Tanzania":"탄자니아","Thailand":"태국","Togo":"토고","Trinidad and Tobago":"트리니다드토바고",
        "Tunisia":"튀니지","Turkiye":"튀르키예","Uganda":"우간다","Ukraine":"우크라이나",
        "United Arab Emirates":"아랍에미리트","United Kingdom":"영국",
        "United States of America":"미국","Uruguay":"우루과이","Uzbekistan":"우즈베키스탄",
        "Venezuela":"베네수엘라","Vietnam":"베트남","Yemen":"예멘","Zambia":"잠비아","Zimbabwe":"짐바브웨",
    }
    countries_raw = sorted(DHL_ZONE_MAP.keys())
    # 한국어명 (영어명) 형식으로 표시
    countries_display = [f"{COUNTRY_KR.get(c, c)} ({c})" for c in countries_raw]
    default_idx = countries_raw.index("United States of America")
    selected_display = st.selectbox("목적지 국가", countries_display, index=default_idx, key="dest_select")
    # 선택된 표시문자에서 실제 영어 국가명 추출
    dest_country = countries_raw[countries_display.index(selected_display)]
    dhl_zone = DHL_ZONE_MAP.get(dest_country, 5)
    dhl_zi = dhl_zone - 1

    # FedEx zone 추론 (영문 국가명 직접 조회 → fallback: 한국어 COUNTRY_TO_FEDEX 매핑)
    fx_zone_direct = FEDEX_ZONE_MAP_EN.get(dest_country)
    if fx_zone_direct:
        fx_zone = fx_zone_direct
    else:
        COUNTRY_TO_FEDEX = {
            "Japan":"일본","China (People's Republic)":"중국 (남부 제외)","Hong Kong SAR China":"홍콩",
            "Taiwan, China":"대만","Macau SAR China":"마카오","Singapore":"싱가포르",
            "Thailand":"태국","Malaysia":"말레이시아","Indonesia":"인도네시아","Philippines":"필리핀",
            "Vietnam":"베트남","Cambodia":"캄보디아","Lao P.D.R.":"라오스","Brunei":"브루나이",
            "India":"인도","Bangladesh":"방글라데시","Pakistan":"파키스탄","Sri Lanka":"스리랑카",
            "Nepal":"네팔","United States of America":"미국 (기타 지역)","Canada":"캐나다",
            "Australia":"호주","New Zealand":"뉴질랜드","Mexico":"멕시코","Puerto Rico":"푸에르토리코",
            "Germany":"독일","United Kingdom":"영국","France":"프랑스","Italy":"이탈리아",
            "Spain":"스페인","Netherlands":"네덜란드","Belgium":"벨기에","Austria":"오스트리아",
            "Switzerland":"스위스","Denmark":"덴마크","Finland":"핀란드","Greece":"그리스",
            "Hungary":"헝가리","Ireland":"아일랜드","Luxembourg":"룩셈부르크","Norway":"노르웨이",
            "Poland":"폴란드","Portugal":"포르투갈","Sweden":"스웨덴","Czech Republic":"체코",
            "Romania":"루마니아","Bulgaria":"불가리아","Croatia":"크로아티아","Estonia":"에스토니아",
            "Latvia":"라트비아","Lithuania":"리투아니아","Slovakia":"슬로바키아","Slovenia":"슬로베니아",
            "Russia":"러시아","Ukraine":"우크라이나","Turkiye":"터키","Kazakhstan":"카자흐스탄",
            "Moldova":"몰도바","Serbia":"세르비아","Montenegro":"몬테네그로",
            "Saudi Arabia":"사우디아라비아","United Arab Emirates":"아랍에미리트","Qatar":"카타르",
            "Kuwait":"쿠웨이트","Bahrain":"바레인","Oman":"오만","Jordan":"요르단","Egypt":"이집트",
            "Iraq":"이라크","Lebanon":"레바논","Israel":"이스라엘",
            "Brazil":"브라질","Colombia":"콜롬비아","Argentina":"아르헨티나","Chile":"칠레",
            "Peru":"페루","Ecuador":"에콰도르","Bolivia":"볼리비아","Paraguay":"파라과이",
            "Uruguay":"우루과이","Venezuela":"베네수엘라","Costa Rica":"코스타리카","Panama":"파나마",
            "Guatemala":"과테말라","Honduras":"온두라스","El Salvador":"엘살바도르",
            "Nicaragua":"니카라과","Jamaica":"자메이카","Dominican Republic":"도미니카공화국",
            "Nigeria":"나이지리아","Kenya":"케냐","South Africa":"남아프리카",
            "Ethiopia":"에티오피아","Tanzania":"탄자니아",
        }
        fx_country_kr = COUNTRY_TO_FEDEX.get(dest_country, "미국 (기타 지역)")
        fx_zone = FEDEX_ZONE_MAP.get(fx_country_kr, "F")
    fx_zi = FEDEX_ZONES.index(fx_zone)

    # ── 서비스 불가 플래그 ──
    ups_no_service   = dest_country in UPS_NO_SERVICE
    fedex_no_service = dest_country in FEDEX_NO_SERVICE

    ups_zone_num = UPS_ZONE_MAP.get(dest_country, 5)
    ups_zi = ups_zone_num - 1

    is_doc = st.radio("화물 구분", ["물품 (Non-Document)", "서류 (Document)"], horizontal=True).startswith("서류")

    st.markdown("---")

    # FedEx 스타일: 유형별 수량 입력 (동일 스펙 N박스 = 1유형 + 수량)
    st.markdown(f'<div style="background:rgba(255,255,255,.04);border:1px solid {_sb_border};border-left:3px solid {_sb_accent};border-radius:8px;padding:10px 10px 6px;margin-bottom:6px;"><div style="font-size:.68rem;color:{_sb_label};font-weight:700;letter-spacing:.07em;margin-bottom:6px;">📦 패키지 정보</div>', unsafe_allow_html=True)
    n_types = st.session_state.pkg_types
    ct_data = []
    for i in range(n_types):
        qty_cur = int(st.session_state.get(f"qty_{i}", 1))
        hL, hR = st.columns([4, 1])
        with hL:
            _bgt = (f' <b style="color:{_sb_ct_fg};">{qty_cur}박스</b>' if qty_cur > 1 else "")
            st.markdown(f'<div style="font-size:.72rem;font-weight:800;color:{_sb_accent};">유형 {i+1}{_bgt}</div>', unsafe_allow_html=True)
        with hR:
            if n_types > 1 and st.button("✕", key=f"del_{i}", use_container_width=True):
                for j in range(i, n_types-1):
                    for k in ["qty","wt","L","W","H"]: st.session_state[f"{k}_{j}"] = st.session_state.get(f"{k}_{j+1}", {"qty":1,"wt":35.,"L":30.,"W":30.,"H":30.}[k])
                st.session_state.pkg_types -= 1; st.rerun()
        qa, qb = st.columns([1, 2])
        with qa: qty_val = st.number_input("수량(박스)", 1, 99, qty_cur, 1, key=f"qty_{i}", help="동일 스펙 박스 수")
        with qb: wt_i = st.number_input("실중량(kg)", .1, 1000., float(st.session_state.get(f"wt_{i}", 35.)), .5, key=f"wt_{i}")
        d1,d2,d3 = st.columns(3)
        with d1: li = st.number_input("가로(cm)", 1., 500., float(st.session_state.get(f"L_{i}", 30.)), 1., key=f"L_{i}")
        with d2: wi = st.number_input("세로(cm)", 1., 500., float(st.session_state.get(f"W_{i}", 30.)), 1., key=f"W_{i}")
        with d3: hi = st.number_input("높이(cm)", 1., 500., float(st.session_state.get(f"H_{i}", 30.)), 1., key=f"H_{i}")
        for _ in range(int(qty_val)): ct_data.append({"wt": wt_i, "L": li, "W": wi, "H": hi})
        if i < n_types-1: st.markdown(f'<hr style="border:none;border-top:1px dashed {_sb_border};margin:8px 0;">', unsafe_allow_html=True)
    total_ct = len(ct_data)
    bl, bc, br2 = st.columns([1, 2, 1])
    with bl:
        if n_types > 1 and st.button("➖ 유형", key="del_type"): st.session_state.pkg_types = max(1, n_types-1); st.rerun()
    with bc:
        _nt = (f" ({n_types}유형)" if n_types > 1 else "")
        st.markdown(f'<div style="text-align:center;padding:7px;background:{_sb_ct_bg};border-radius:7px;color:{_sb_ct_fg};font-weight:700;border:1px solid {_sb_ct_bdr};font-size:.82rem;">총 {total_ct} C/T{_nt}</div>', unsafe_allow_html=True)
    with br2:
        if n_types < 5 and st.button("➕ 유형", key="add_type"):
            ni = n_types
            for k,v in [("qty",1),("wt",35.),("L",30.),("W",30.),("H",30.)]:
                if f"{k}_{ni}" not in st.session_state: st.session_state[f"{k}_{ni}"] = v
            st.session_state.pkg_types = n_types+1; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # 유류할증료 & 할인율 섹션
    # ── 핵심 설계: 수출·수입 모드 모두 동일한 session_state key 사용 ──
    # → 수출에서 입력한 값이 수입 전환 후에도 그대로 유지됨
    # ══════════════════════════════════════════════════════════════════
    st.markdown(f"""<div style="background:rgba(255,255,255,.04);border:1px solid {_sb_border};
        border-left:3px solid rgba(255,255,255,.20);border-radius:8px;padding:8px 10px 2px;margin-bottom:6px;">
        <div style="font-size:.68rem;color:#94a3b8;font-weight:700;letter-spacing:.07em;margin-bottom:4px;">
        💰 유류할증료 &amp; 할인율</div>""", unsafe_allow_html=True)

    # ── 유류할증료: 수출/수입 동일 key 사용 (carrier fuel은 방향 무관) ──
    st.markdown("**유류할증료 (운송사별, %)**")
    st.markdown('<div style="font-size:.68rem;color:#64748b;margin-bottom:6px;">DHL: 매월 변동 | FedEx·UPS: 매주 변동</div>', unsafe_allow_html=True)
    fuel_dhl   = st.number_input("DHL 유류할증료(%)",   0., 60., step=.25, key="fuel_dhl",   on_change=_save_settings)
    fuel_fedex = st.number_input("FedEx 유류할증료(%)", 0., 60., step=.25, key="fuel_fedex", on_change=_save_settings)
    fuel_ups   = st.number_input("UPS 유류할증료(%)",   0., 60., step=.25, key="fuel_ups",   on_change=_save_settings)

    # ── 할인율: 수출/수입 동일 key 사용 (UPS B8733R만 수입 전용) ──
    st.markdown("**📉 고객 할인율 (%)**")
    if mode == "수출":
        st.markdown('<div style="font-size:.68rem;color:#64748b;margin-bottom:4px;">수출 할인율 | 소수점 2자리까지</div>', unsafe_allow_html=True)
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            disc_dhl     = st.number_input("DHL",           0.0, 99.99, step=0.01, format="%.2f", key="disc_dhl",     on_change=_save_settings)
            disc_fedex   = st.number_input("FedEx IP",      0.0, 99.99, step=0.01, format="%.2f", key="disc_fedex",   on_change=_save_settings)
            disc_fedex_e = st.number_input("FedEx Economy", 0.0, 99.99, step=0.01, format="%.2f", key="disc_fedex_e", on_change=_save_settings)
        with _dc2:
            disc_ups     = st.number_input("UPS",           0.0, 99.99, step=0.01, format="%.2f", key="disc_ups",     on_change=_save_settings)
            tgt_margin   = st.number_input("목표마진(%)",   0.0, 99.99, step=0.01, format="%.2f", key="tgt_margin",   on_change=_save_settings)
        disc_ups_b8 = disc_ups   # 수출: 2F94A8·B8733R 동일 할인율
    else:
        st.markdown('<div style="font-size:.68rem;color:#64748b;margin-bottom:4px;">수입 할인율 | UPS는 계정별 별도 설정</div>', unsafe_allow_html=True)
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            # ★ 핵심 수정: 수입도 수출과 동일 key → 값이 연동됨
            disc_dhl     = st.number_input("DHL",           0.0, 99.99, step=0.01, format="%.2f", key="disc_dhl",     on_change=_save_settings)
            disc_fedex   = st.number_input("FedEx IP",      0.0, 99.99, step=0.01, format="%.2f", key="disc_fedex",   on_change=_save_settings)
            disc_fedex_e = st.number_input("FedEx Economy", 0.0, 99.99, step=0.01, format="%.2f", key="disc_fedex_e", on_change=_save_settings)
        with _dc2:
            disc_ups     = st.number_input("UPS 2F94A8",    0.0, 99.99, step=0.01, format="%.2f", key="disc_ups",     on_change=_save_settings)
            disc_ups_b8  = st.number_input("UPS B8733R",    0.0, 99.99, step=0.01, format="%.2f", key="imp_disc_ups_b8", on_change=_save_settings)
            tgt_margin   = st.number_input("목표마진(%)",   0.0, 99.99, step=0.01, format="%.2f", key="tgt_margin",   on_change=_save_settings)

    p_add = 0

    st.markdown("</div>", unsafe_allow_html=True)

    # ── 특이사항 섹션 ──
    st.markdown(f"""<div style="background:rgba(255,255,255,.04);border:1px solid {_sb_border};
        border-left:3px solid rgba(255,255,255,.20);border-radius:8px;padding:8px 10px 2px;margin-bottom:6px;">
        <div style="font-size:.68rem;color:#94a3b8;font-weight:700;letter-spacing:.07em;margin-bottom:4px;">
        📝 특이사항</div>""", unsafe_allow_html=True)
    notes_input = st.text_area("견적서 포함 메모", placeholder="예: 위험물 포함 / 냉장 필요 등", height=70)
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# 계산 — 수출 / 수입 분기
# ═══════════════════════════════════════════════════
_save_if_changed()   # [프로그래머A] 렌더 시점 자동 저장 (on_change 보완)
total_pub_dhl = total_net_dhl = 0
total_pub_fedex_ip = total_net_fedex_ip = 0
total_pub_fedex_ec = total_net_fedex_ec = 0
total_pub_ups_2F = total_net_ups_2F = 0
total_pub_ups_B8 = total_net_ups_B8 = 0
total_actual_wt = total_vol_wt = total_chargeable = 0

sur_dhl_ct   = {}
sur_fedex_ct = {}
sur_ups_ct   = {}

# 수입 UPS 존
ups_imp_zone_num = UPS_IMP_ZONE_MAP.get(dest_country, 5)
ups_imp_zi = ups_imp_zone_num - 1

ct_results = []
for ct in ct_data:
    winfo = calc_weight(ct["wt"], ct["L"], ct["W"], ct["H"])
    total_actual_wt  += ct["wt"]
    total_vol_wt     += winfo["volume"]
    total_chargeable += winfo["rounded"]
    dims = sorted([ct["L"], ct["W"], ct["H"]], reverse=True)

    if mode == "수출":
        # ── DHL 수출 부가서비스 — C/T별 누적 (운임은 루프 후 총중량으로 단일계산) ──
        w_dhl = winfo["rounded"]
        s_dhl = {}
        if 25 < w_dhl <= 70: s_dhl["컨베이어 운반 불가"] = 30000
        if w_dhl > 70:        s_dhl["중량 초과"]          = 150000
        if dims[0] > 100 or dims[1] > 80: s_dhl["길이 초과"] = 30000
        for k, v in s_dhl.items(): sur_dhl_ct[k] = sur_dhl_ct.get(k, 0) + v
        # 분쟁지역/제재국 수수료 — 발송건당 1회만 (첫 C/T에서만 추가)
        if ct_data.index(ct) == 0:
            if dest_country in DHL_CONFLICT_COUNTRIES:
                sur_dhl_ct["분쟁지역 배송"] = sur_dhl_ct.get("분쟁지역 배송", 0) + DHL_CONFLICT_SUR
            if dest_country in DHL_SANCTION_COUNTRIES:
                sur_dhl_ct["무역제재국 배송"] = sur_dhl_ct.get("무역제재국 배송", 0) + DHL_SANCTION_SUR

        # ── FedEx 수출 부가서비스 — C/T별 누적 (운임은 루프 후 총중량으로 단일계산) ──
        w_fx = winfo["rounded"]
        s_fx = {}
        _fx_oversized = w_fx > 50
        _fx_add_wt    = w_fx > 25
        _fx_add_vol   = dims[0] > 121 or dims[1] > 76
        # ※ 특대형 적용 시 추가취급(중량/용적) 중복 부과 안 됨 (FedEx 정책)
        if _fx_oversized:
            s_fx["특대형"] = 86000
        else:
            if _fx_add_wt:  s_fx["추가취급(중량)"] = 35600
            if _fx_add_vol: s_fx["추가취급(용적)"] = 35600
        for k, v in s_fx.items(): sur_fedex_ct[k] = sur_fedex_ct.get(k, 0) + v

        # ── UPS 수출 부가서비스 — C/T별 누적 (운임은 루프 후 총중량으로 단일계산) ──
        w_ups = winfo["rounded"]
        s_ups = {}
        ups_girth = (dims[1] + dims[2]) * 2
        _ups_large_pkg = (dims[0] + ups_girth) > 300
        _ups_osp       = dims[0] > 122 or dims[1] > 76 or ct["wt"] > 25
        # ※ 대형포장물 먼저 적용 시 비규격품(OSP) 부과 안 됨 (UPS 정책)
        if _ups_large_pkg:
            s_ups["대형포장물"] = 69200
        elif _ups_osp:
            s_ups["비규격품(OSP)"] = 21400
        # ※ 70kg 초과 C/T: UPS WW Express Freight 전환 → Saver 진행 불가
        if ct["wt"] > 70: s_ups["⚠ WW Express Freight — Saver 진행 불가"] = 0
        for k, v in s_ups.items(): sur_ups_ct[k] = sur_ups_ct.get(k, 0) + v

        ct_results.append({
            "winfo": winfo, "w": winfo["rounded"],
            "w_dhl": w_dhl, "w_fx": w_fx, "w_ups": w_ups,
            "dhl":    {"pub": 0, "net": 0, "surs": s_dhl},
            "fedex":  {"pub": 0, "net": 0, "surs": s_fx},
            "fedexec":{"pub": 0, "net": 0, "surs": s_fx},
            "ups2f":  {"pub": 0, "net": 0, "surs": s_ups},
            "upsb8":  {"pub": 0, "net": 0, "surs": s_ups},
        })

    else:  # mode == "수입"
        # ── DHL 수입 부가서비스 — C/T별 누적 (운임은 루프 후 총중량으로 단일계산) ──
        w_dhl = winfo["rounded"]
        s_dhl = {}
        if 25 < w_dhl <= 70: s_dhl["컨베이어 운반 불가"] = 30000
        if w_dhl > 70:        s_dhl["중량 초과"]          = 150000
        if dims[0] > 100 or dims[1] > 80: s_dhl["길이 초과"] = 30000
        for k, v in s_dhl.items(): sur_dhl_ct[k] = sur_dhl_ct.get(k, 0) + v
        if ct_data.index(ct) == 0:
            if dest_country in DHL_CONFLICT_COUNTRIES:
                sur_dhl_ct["분쟁지역 배송"] = sur_dhl_ct.get("분쟁지역 배송", 0) + DHL_CONFLICT_SUR
            if dest_country in DHL_SANCTION_COUNTRIES:
                sur_dhl_ct["무역제재국 배송"] = sur_dhl_ct.get("무역제재국 배송", 0) + DHL_SANCTION_SUR

        # ── FedEx 수입 부가서비스 — C/T별 누적 (운임은 루프 후 총중량으로 단일계산) ──
        w_fx = winfo["rounded"]
        s_fx = {}
        _fx_oversized = w_fx > 50
        _fx_add_wt    = w_fx > 25
        _fx_add_vol   = dims[0] > 121 or dims[1] > 76
        if _fx_oversized:
            s_fx["특대형"] = 86000
        else:
            if _fx_add_wt:  s_fx["추가취급(중량)"] = 35600
            if _fx_add_vol: s_fx["추가취급(용적)"] = 35600
        for k, v in s_fx.items(): sur_fedex_ct[k] = sur_fedex_ct.get(k, 0) + v

        # ── UPS 수입 부가서비스 — C/T별 누적 (운임은 루프 후 총중량으로 단일계산) ──
        w_ups = winfo["rounded"]
        s_ups = {}
        ups_girth = (dims[1] + dims[2]) * 2
        _ups_large_pkg = (dims[0] + ups_girth) > 300
        _ups_osp       = dims[0] > 122 or dims[1] > 76 or ct["wt"] > 25
        # ※ 대형포장물 먼저 적용 시 비규격품(OSP) 부과 안 됨 (UPS 정책)
        if _ups_large_pkg:
            s_ups["대형포장물"] = 69200
        elif _ups_osp:
            s_ups["비규격품(OSP)"] = 21400
        # ※ 70kg 초과 C/T: UPS WW Express Freight 전환 → Saver 진행 불가
        if ct["wt"] > 70: s_ups["⚠ WW Express Freight — Saver 진행 불가"] = 0
        for k, v in s_ups.items(): sur_ups_ct[k] = sur_ups_ct.get(k, 0) + v

        ct_results.append({
            "winfo": winfo, "w": winfo["rounded"],
            "w_dhl": w_dhl, "w_fx": w_fx, "w_ups": w_ups,
            "dhl":    {"pub": 0, "net": 0, "surs": s_dhl},
            "fedex":  {"pub": 0, "net": 0, "surs": s_fx},
            "fedexec":{"pub": 0, "net": 0, "surs": s_fx},
            "ups2f":  {"pub": 0, "net": 0, "surs": s_ups},
            "upsb8":  {"pub": 0, "net": 0, "surs": s_ups},
        })

total_sur_dhl   = sum(sur_dhl_ct.values())
total_sur_fedex = sum(sur_fedex_ct.values())
total_sur_ups   = sum(sur_ups_ct.values())

# ══════════════════════════════════════════════════════════════════
# 3사 운임 — 총 청구중량 기반 단일 산출
# ※ DHL · FedEx · UPS 모두:
#   총 청구중량으로 구간 결정 → 단가/kg × 총 중량
#   (DHL/FedEx 고객서비스팀, UPS 고객서비스팀 공동 확인)
# ══════════════════════════════════════════════════════════════════
_total_w = total_chargeable   # 전체 C/T 합산 청구중량

# ── DHL ──
if mode == "수출":
    total_pub_dhl, total_net_dhl = dhl_lookup(_total_w, dhl_zi, is_doc)
    # p_add(남부 추가요금)는 C/T 수만큼 누적 (박스별 고정 추가금)
    _p_add_total = p_add * len(ct_data)
    total_pub_dhl += _p_add_total
    total_net_dhl += _p_add_total
else:
    total_pub_dhl = dhl_imp_lookup(_total_w, dhl_zi, is_doc)
    total_net_dhl = dhl_imp_cost_lookup(_total_w, dhl_zi, is_doc)

# ── FedEx ──
if mode == "수출":
    total_pub_fedex_ip  = fedex_lookup(_total_w, fx_zi, is_doc=is_doc, econ=False)
    total_net_fedex_ip  = ceil10(total_pub_fedex_ip  * 0.5)
    total_pub_fedex_ec  = fedex_lookup(_total_w, fx_zi, is_doc=False,  econ=True)
    total_net_fedex_ec  = ceil10(total_pub_fedex_ec  * 0.5)
else:
    total_pub_fedex_ip  = fximp_lookup(_total_w, fx_zi, is_doc=is_doc, econ=False)
    total_net_fedex_ip  = ceil10(total_pub_fedex_ip  * 0.5)
    total_pub_fedex_ec  = fximp_lookup(_total_w, fx_zi, is_doc=False,  econ=True)
    total_net_fedex_ec  = ceil10(total_pub_fedex_ec  * 0.5)

# ── DHL 단가/kg 정보 (크로스체크용) ──
def _dhl_rate_per_kg(w, zi, is_imp=False):
    rw = int(math.ceil(w))
    if w <= 30: return None   # 단가표 구간 (kg당 아님)
    if is_imp:
        return DHL_IMP_OVER["30-70"][zi]   # 30kg+ 단일구간
    return DHL_PUB_OVER["30.1-70"][zi]

def _dhl_bracket(w):
    if w <= 30: return "≤30kg (단가표)"
    elif w <= 70: return "30.1~70kg"
    return "70kg+"

# ── FedEx 단가/kg 정보 (크로스체크용) ──
def _fx_rate_per_kg(w, zi, is_imp=False, econ=False):
    rw = int(math.ceil(w))
    if w <= 20.5: return None
    br = ("21-44" if rw<=44 else "45-70" if rw<=70 else "71-99" if rw<=99
          else "100-299" if rw<=299 else "300-499" if rw<=499
          else "500-999" if rw<=999 else "1000+")
    if is_imp:
        tbl = FXIMP_ECON_OVER if econ else FXIMP_OVER
    else:
        tbl = FEDEX_PUB_ECON_OVER if econ else FEDEX_PUB_OVER
    return tbl[br][zi]

def _fx_bracket(w):
    rw = int(math.ceil(w))
    if w <= 20.5: return "≤20.5kg (단가표)"
    return ("21~44kg" if rw<=44 else "45~70kg" if rw<=70 else "71~99kg" if rw<=99
            else "100~299kg" if rw<=299 else "300~499kg" if rw<=499
            else "500~999kg" if rw<=999 else "1000kg+")

_is_imp = (mode == "수입")
dhl_rate_per_kg  = _dhl_rate_per_kg(_total_w, dhl_zi, _is_imp)
dhl_bracket_str  = _dhl_bracket(_total_w)
fx_zi_disp       = fx_zi
fx_rate_per_kg   = _fx_rate_per_kg(_total_w, fx_zi_disp, _is_imp, econ=False)
fx_ec_rate_per_kg= _fx_rate_per_kg(_total_w, fx_zi_disp, _is_imp, econ=True)
fx_bracket_str   = _fx_bracket(_total_w)

ups_total_w = _total_w   # UPS도 동일 총중량 사용
if mode == "수출":
    total_pub_ups_2F, total_net_ups_2F = ups_lookup(ups_total_w, ups_zi,     is_doc, "2F94A8")
    total_pub_ups_B8, total_net_ups_B8 = ups_lookup(ups_total_w, ups_zi,     is_doc, "B8733R")
else:
    total_pub_ups_2F = ups_imp_lookup(ups_total_w, ups_imp_zi, is_doc)
    total_net_ups_2F = ups_imp_cost_lookup(ups_total_w, ups_imp_zi, is_doc, "2F94A8")
    total_pub_ups_B8 = ups_imp_lookup(ups_total_w, ups_imp_zi, is_doc)
    total_net_ups_B8 = ups_imp_cost_lookup(ups_total_w, ups_imp_zi, is_doc, "B8733R")

# UPS 구간 정보 (크로스 체크용 표시)
def _ups_bracket(w):
    rw = int(math.ceil(w))
    if rw <= 20:  return f"≤20kg (단가표)"
    elif rw <= 44:  return "21~44kg"
    elif rw <= 70:  return "45~70kg"
    elif rw <= 99:  return "71~99kg"
    elif rw <= 299: return "100~299kg"
    elif rw <= 499: return "300~499kg"
    else:           return "500kg+"

def _ups_rate_per_kg(w, zi, is_imp=False):
    """UPS 단가/kg 반환 (크로스체크·표시용)"""
    rw = int(math.ceil(w))
    if rw <= 20: return None   # 단가표 (kg당 아님)
    if is_imp:
        br = ("21-44" if rw<=44 else "45-70" if rw<=70 else "71-99" if rw<=99
              else "100-299" if rw<=299 else "300-499" if rw<=499 else "500-999")
        return UPS_IMP_OVER.get(br, UPS_IMP_OVER["500-999"])[zi]
    else:
        br = ("21-44" if rw<=44 else "45-70" if rw<=70 else "71-99" if rw<=99
              else "100-299" if rw<=299 else "300-499" if rw<=499 else "500+")
        return UPS_PUB_OVER.get(br, UPS_PUB_OVER["500+"])[zi]

_ups_is_imp    = (mode == "수입")
_ups_zi_disp   = ups_imp_zi if _ups_is_imp else ups_zi
ups_rate_per_kg = _ups_rate_per_kg(ups_total_w, _ups_zi_disp, _ups_is_imp)
ups_bracket_str = _ups_bracket(ups_total_w)

res_dhl     = calc_carrier("DHL Express",       total_pub_dhl,      total_net_dhl,      total_sur_dhl,   fuel_dhl,   disc_dhl)
res_fedex   = calc_carrier("FedEx IP",          total_pub_fedex_ip, total_net_fedex_ip, total_sur_fedex, fuel_fedex, disc_fedex)
res_fedex_e = calc_carrier("FedEx Economy",     total_pub_fedex_ec, total_net_fedex_ec, total_sur_fedex, fuel_fedex, disc_fedex_e)

# ── UPS 계정 사용료 3% — net_base와 분리하여 net_fee로 전달 ──
UPS_ACCT_FEE_RATE = 0.03
ups_fee_2F = ceil10(total_net_ups_2F * UPS_ACCT_FEE_RATE)   # 3% 수수료 (2F94A8)
ups_fee_B8 = ceil10(total_net_ups_B8 * UPS_ACCT_FEE_RATE)   # 3% 수수료 (B8733R)
# total_net_ups_2F / B8 는 변경 없음 — 계약서 원가 그대로 유지

res_ups2f   = calc_carrier("UPS 2F94A8",  total_pub_ups_2F, total_net_ups_2F, total_sur_ups, fuel_ups, disc_ups,                                    net_fee=ups_fee_2F)
res_upsb8   = calc_carrier("UPS B8733R",  total_pub_ups_B8, total_net_ups_B8, total_sur_ups, fuel_ups, disc_ups if mode == "수출" else disc_ups_b8, net_fee=ups_fee_B8)

def _agg_surs(key):
    agg = {}
    for ct in ct_results:
        for name, val in ct[key]["surs"].items():
            agg[name] = agg.get(name, 0) + val
    return agg

res_dhl    ["surs_detail"] = _agg_surs("dhl")
res_fedex  ["surs_detail"] = _agg_surs("fedex")
res_fedex_e["surs_detail"] = _agg_surs("fedexec")
res_ups2f  ["surs_detail"] = _agg_surs("ups2f")
res_upsb8  ["surs_detail"] = _agg_surs("upsb8")

# ── 3사 크로스체크 정보 주입 (할인율 포함 → 할인 후 단가/kg 표시용) ──
def _disc_rpk(pub_total, disc_pct, tw):
    """할인 적용 후 단가/kg = 할인후 운임 / 총중량 (10원 단위 반올림)"""
    if tw <= 0 or pub_total <= 0: return None
    discounted = math.ceil(pub_total * (1 - disc_pct/100) / 10) * 10
    return round(discounted / tw)

_dhl_rate_info = {
    "total_w":      _total_w,
    "bracket":      dhl_bracket_str,
    "rate_per_kg":  dhl_rate_per_kg,
    "disc_rpk":     _disc_rpk(total_pub_dhl, disc_dhl, _total_w),
    "disc_pct":     disc_dhl,
    "n_ct":         len(ct_data),
}
_fx_rate_info = {
    "total_w":      _total_w,
    "bracket":      fx_bracket_str,
    "rate_per_kg":  fx_rate_per_kg,
    "disc_rpk":     _disc_rpk(total_pub_fedex_ip, disc_fedex, _total_w),
    "disc_pct":     disc_fedex,
    "n_ct":         len(ct_data),
}
_fx_ec_rate_info = {
    "total_w":      _total_w,
    "bracket":      fx_bracket_str,
    "rate_per_kg":  fx_ec_rate_per_kg,
    "disc_rpk":     _disc_rpk(total_pub_fedex_ec, disc_fedex_e, _total_w),
    "disc_pct":     disc_fedex_e,
    "n_ct":         len(ct_data),
}
_ups_rate_info = {
    "total_w":      ups_total_w,
    "bracket":      ups_bracket_str,
    "rate_per_kg":  ups_rate_per_kg,
    "disc_rpk":     _disc_rpk(total_pub_ups_2F, disc_ups, ups_total_w),
    "disc_pct":     disc_ups,
    "n_ct":         len(ct_data),
}
_ups_b8_rate_info = {
    "total_w":      ups_total_w,
    "bracket":      ups_bracket_str,
    "rate_per_kg":  ups_rate_per_kg,
    "disc_rpk":     _disc_rpk(total_pub_ups_B8, disc_ups if mode=="수출" else disc_ups_b8, ups_total_w),
    "disc_pct":     disc_ups if mode=="수출" else disc_ups_b8,
    "n_ct":         len(ct_data),
}
res_dhl    ["rate_info"] = _dhl_rate_info
res_fedex  ["rate_info"] = _fx_rate_info
res_fedex_e["rate_info"] = _fx_ec_rate_info
res_ups2f  ["rate_info"] = _ups_rate_info
res_upsb8  ["rate_info"] = _ups_b8_rate_info

# ── 서비스 불가 플래그 주입 ──
res_ups2f["no_service"] = ups_no_service
res_upsb8["no_service"] = ups_no_service
res_fedex["no_service"] = fedex_no_service
res_fedex_e["no_service"] = fedex_no_service
res_dhl["no_service"] = False

if mode == "수출":
    all_results = {
        "DHL Express":   res_dhl,
        "FedEx IP":      res_fedex,
        "FedEx Economy": res_fedex_e,
        "UPS 2F94A8":    res_ups2f,
        "UPS B8733R":    res_upsb8,
    }
else:  # 수입: UPS 2계정 분리 (수출과 동일 구조)
    all_results = {
        "DHL Express":   res_dhl,
        "FedEx IP":      res_fedex,
        "FedEx Economy": res_fedex_e,
        "UPS 2F94A8":    res_ups2f,
        "UPS B8733R":    res_upsb8,
    }

# 서비스 불가 제외하고 최저가 비교
all_quotes_svc = {k: v["total_quote"] for k, v in all_results.items() if not v.get("no_service")}
best_carrier = min(all_quotes_svc, key=all_quotes_svc.get) if all_quotes_svc else "DHL Express"
all_quotes   = {k: v["total_quote"] for k, v in all_results.items()}

if mode == "수출":
    zone_label = f"DHL Zone {dhl_zone} | FedEx Zone {fx_zone} | UPS Zone {ups_zone_num}"
else:
    zone_label = f"DHL Zone {dhl_zone} | FedEx Zone {fx_zone} | UPS Zone {ups_imp_zone_num}"

# ═══════════════════════════════════════════════════
# UI 렌더링
# ═══════════════════════════════════════════════════
_logo_en_html = ("<img src='" + _LOGO_EN_B64 + "' style='height:60px;object-fit:contain;' />") if _LOGO_EN_B64 else ""
_logo_kr_html = ("<img src='" + _LOGO_KR_B64 + "' style='height:32px;object-fit:contain;opacity:0.85;' />") if _LOGO_KR_B64 else ""
_today_str    = datetime.now().strftime("%Y년 %m월 %d일")
_mode_color   = "#ffffff"  # 배너 글씨: 항상 흰색 (배경이 핑크/블루 다크 그라데이션)
_mode_bg      = "rgba(225,29,72,0.15)" if mode == "수입" else "rgba(255,255,255,0.15)"
_ups_z_str    = f"UPS Z{ups_imp_zone_num}" if mode == "수입" else f"UPS Z{ups_zone_num}"
# 배너 배경: Python mode 기반 직접 인라인 주입 — JS 타이밍 무관
_banner_bg = (
    "linear-gradient(135deg, #4c0519 0%, #9f1239 50%, #e11d48 100%)"
    if mode == "수입" else
    "linear-gradient(135deg, #1e3a8a 0%, #2563eb 60%, #3b82f6 100%)"
)
_banner_shadow = (
    "0 8px 32px rgba(225,29,72,.30)"
    if mode == "수입" else
    "0 8px 32px rgba(37,99,235,.25)"
)
_banner_html  = (
    f'<div class="banner" style="background:{_banner_bg};box-shadow:{_banner_shadow};">'
    '<div style="display:flex;align-items:center;gap:20px;">'
    + _logo_en_html + _logo_kr_html +
    f'<div style="margin-left:8px;padding-left:18px;border-left:3px solid {_mode_color}30;">'
    f'<div class="banner-title" style="color:{_mode_color};">에어브리지 운임계산기</div>'
    f'<div style="font-size:1.55rem;font-weight:900;color:{_mode_color};opacity:0.85;margin-top:2px;letter-spacing:.06em;">— {"수  입" if mode=="수입" else "수  출"}</div>'
    f'<div class="banner-sub" style="margin-top:6px;">국제특송 운임 비교 · {_today_str} · 2026 Rate Card</div>'
    '</div>'
    '</div>'
    '<div style="text-align:right">'
    f'<div style="font-size:.85rem;color:#64748b;">{"발송지" if mode=="수입" else "목적지"}</div>'
    f'<div style="font-size:1.15rem;font-weight:800;color:{_mode_color};">{dest_country}</div>'
    f'<div style="font-size:.76rem;color:#475569;margin-top:2px;">DHL Z{dhl_zone} | FedEx Z{fx_zone} | {_ups_z_str}</div>'
    f'<div style="margin-top:8px;padding:4px 12px;background:{_mode_bg};border:1px solid {_mode_color}40;border-radius:20px;display:inline-block;">'
    f'<span style="font-size:.8rem;font-weight:800;color:{_mode_color};">{"📦 수입 모드" if mode=="수입" else "✈ 수출 모드"}</span>'
    '</div>'
    '</div></div>'
)
st.markdown(_banner_html, unsafe_allow_html=True)

# ── 상단 요약 (수출·수입 공통 7칸) ──
_dir_lbl = "발송지" if mode == "수입" else "목적지"
_mc      = "#f43f5e" if mode == "수입" else "#2563eb"
def _mbox_nsvc(lbl, color, country): return f'<div class="mbox"><div class="mbox-lbl">{lbl}</div><div class="mbox-val" style="color:#b91c1c;font-size:.78rem;">🚫 서비스불가</div><div class="mbox-sub" style="color:#ef4444;">{country[:12]}</div></div>'
def _mbox_ok(lbl, color, quote, margin): return f'<div class="mbox"><div class="mbox-lbl">{lbl}</div><div class="mbox-val" style="color:{color};font-size:.88rem;">{fmt(quote)}</div><div class="mbox-sub">마진 {pct(margin)}</div></div>'
s1,s2,s3,s4,s5,s6,s7 = st.columns(7)
with s1: st.markdown(f'<div class="mbox"><div class="mbox-lbl">{_dir_lbl}</div><div class="mbox-val" style="font-size:.78rem;color:{_mc};">{dest_country[:12]}</div><div class="mbox-sub">{len(ct_data)} C/T</div></div>', unsafe_allow_html=True)
with s2: st.markdown(f'<div class="mbox"><div class="mbox-lbl">총 청구중량</div><div class="mbox-val" style="color:{_mc};font-size:1.1rem;">{total_chargeable:.1f} kg</div><div class="mbox-sub">실중량 {total_actual_wt:.1f}kg</div></div>', unsafe_allow_html=True)
with s3: st.markdown(_mbox_nsvc("DHL Express","#D40511",dest_country) if res_dhl.get("no_service") else _mbox_ok("DHL Express","#D40511",res_dhl["total_quote"],res_dhl["margin_rate"]), unsafe_allow_html=True)
with s4: st.markdown(_mbox_nsvc("FedEx IP","#4D148C",dest_country) if res_fedex.get("no_service") else _mbox_ok("FedEx IP","#4D148C",res_fedex["total_quote"],res_fedex["margin_rate"]), unsafe_allow_html=True)
with s5: st.markdown(_mbox_nsvc("FedEx Economy","#6620b0",dest_country) if res_fedex_e.get("no_service") else _mbox_ok("FedEx Economy","#6620b0",res_fedex_e["total_quote"],res_fedex_e["margin_rate"]), unsafe_allow_html=True)
with s6: st.markdown(_mbox_nsvc("UPS 2F94A8","#351C15",dest_country) if res_ups2f.get("no_service") else _mbox_ok("UPS 2F94A8","#351C15",res_ups2f["total_quote"],res_ups2f["margin_rate"]), unsafe_allow_html=True)
with s7: st.markdown(_mbox_nsvc("UPS B8733R","#5c3a1e",dest_country) if res_upsb8.get("no_service") else _mbox_ok("UPS B8733R","#5c3a1e",res_upsb8["total_quote"],res_upsb8["margin_rate"]), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══ 탭 ══
tab1, tab2, tab3 = st.tabs(["📊 5사 비교 분석", "📋 상세 명세", "📄 PDF 견적서 발행"])

# ─────────────────────────────────────────────
# TAB 1: 5사 비교 분석
# ─────────────────────────────────────────────
with tab1:
    st.markdown("##### 💡 고객 안내 기준 — 5사 운임 비교")

    def margin_alert(mr, tgt):
        if mr >= tgt: return f'<div class="alert alert-ok">✅ 목표 마진 달성 ({pct(mr)})</div>'
        if mr >= 15:  return f'<div class="alert alert-warn">⚠️ 마진 부족 — {pct(tgt-mr)} 미달</div>'
        return f'<div class="alert alert-bad">🚨 마진 위험 — 재검토 필요</div>'

    def render_card(res, name, css_class, badge_class, color, disc_val, tt_info="", acct_info="", is_import=False):
        is_no_svc = res.get("no_service", False)
        # ── UPS 최대한도초과 = Express Freight 전환 필요 ──
        _surs_d = res.get("surs_detail", {})
        is_ups_freight = ("UPS" in name) and ("최대한도초과" in _surs_d)
        is_best = (name == best_carrier) and not is_no_svc and not is_ups_freight
        extra_cls = "disabled" if (is_no_svc or is_ups_freight) else ""
        best_badge = '<span class="carrier-badge badge-best">🏆 최저견적</span>' if is_best else ''

        # ── UPS Worldwide Express Freight 전환 안내 카드 ──
        if is_ups_freight:
            return f"""
<div class="carrier-card ups disabled">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <span class="carrier-badge badge-ups">{name}</span>
    <span style="font-size:.6rem;background:#fff7ed;color:#c2410c;border-radius:4px;padding:2px 7px;font-weight:700;">운송 불가 (Saver)</span>
  </div>
  <div style="margin-top:20px;padding:16px 10px;text-align:center;">
    <div style="font-size:1.6rem;margin-bottom:8px;">🚚</div>
    <div style="font-size:.82rem;font-weight:800;color:#92400e;line-height:1.6;">
      UPS Worldwide Express Freight<br>화물로 Saver 진행 불가능
    </div>
    <div style="font-size:.68rem;color:#94a3b8;margin-top:8px;line-height:1.5;">
      C/T당 실중량 70kg 초과 시<br>WW Express Saver 서비스 불가<br>
      <span style="color:#c2410c;font-weight:700;">WW Express Freight 상품으로 별도 문의 필요</span>
    </div>
  </div>
</div>"""

        # ── 서비스 불가 카드 ──
        if is_no_svc:
            return f"""
<div class="carrier-card {css_class} disabled">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <span class="carrier-badge {badge_class}">{name}</span>
    <span style="font-size:.65rem;background:#fee2e2;color:#b91c1c;border-radius:4px;padding:2px 7px;font-weight:700;">서비스불가</span>
  </div>
  <div style="margin-top:24px;text-align:center;padding:20px 10px;">
    <div style="font-size:1.8rem;margin-bottom:8px;">🚫</div>
    <div style="font-size:.88rem;font-weight:700;color:#b91c1c;line-height:1.5;">서비스 불가 국가</div>
    <div style="font-size:.72rem;color:#94a3b8;margin-top:6px;line-height:1.5;">{dest_country}은(는)<br>2026년 기준 {name}<br>서비스 미제공 지역입니다</div>
  </div>
</div>"""

        tt_html = f'<div style="font-size:.67rem;color:{_tt_color};background:{_tt_bg};border-radius:4px;padding:2px 8px;display:inline-block;margin-right:4px;font-weight:600;">🕐 T/T {tt_info}</div>' if tt_info else '<div style="display:inline-block;height:20px;"></div>'
        acct_html = f'<div style="font-size:.67rem;color:#997755;background:rgba(255,200,100,.15);border-radius:4px;padding:2px 7px;display:inline-block;font-weight:600;">🔑 {acct_info}</div>' if acct_info else ''

        margin_num_color = "#16a34a" if res["margin_rate"] >= tgt_margin else ("#d97706" if res["margin_rate"] >= 15 else "#dc2626")

        # ── 견적가 상세 ──
        base_amt   = res["pub_disc"] + res["sur_total"]
        fuel_amt   = res["pub_fuel"] + res["sur_fuel_pub"]
        surs_detail = res.get("surs_detail", {})
        has_sur    = res["sur_total"] > 0

        # ── 단가/kg 크로스체크 라인 (할인 적용 후 단가 표시) ──
        _rate_info = res.get("rate_info", {})
        _rpk      = _rate_info.get("rate_per_kg")    # 공시 단가/kg
        _disc_rpk = _rate_info.get("disc_rpk")       # 할인 후 단가/kg
        _disc_pct = _rate_info.get("disc_pct", 0)
        _brk = _rate_info.get("bracket","")
        _tw  = _rate_info.get("total_w", total_chargeable)
        _nct = _rate_info.get("n_ct", len(ct_data))
        _show_rpk = _disc_rpk or _rpk
        if _show_rpk:
            _rate_ck_html = (
                f'<div style="font-size:.63rem;color:#64748b;padding:2px 0 4px;">'
                f'({_show_rpk:,}원/kg)'
                f'</div>'
            )
        else:
            _rate_ck_html = ""

        if has_sur:
            bd_rows = [("항공운임", res["pub_disc"])]
            for sur_name, sur_val in surs_detail.items():
                bd_rows.append((f"  └ {sur_name}", sur_val))
            if len(surs_detail) >= 2:
                bd_rows.append(("부가서비스 소계", res["sur_total"]))
            bd_rows.append(("유류할증료", fuel_amt))
            while len(bd_rows) < 4:
                bd_rows.append(("─", 0))
        else:
            bd_rows = [
                ("항공운임",   res["pub_disc"]),
                ("유류할증료", fuel_amt),
                ("─", 0),
                ("─", 0),
            ]

        bd_html = ""
        for lbl, v in bd_rows:
            if lbl == "─":
                bd_html += '<div class="breakdown-row" style="opacity:0;"><span class="bd-label">-</span><span class="bd-cost">-</span></div>'
                continue
            is_sub  = (lbl == "부가서비스 소계")
            is_item = lbl.startswith("  └")
            style_extra = "border-top:1px dashed #ccd4e0;margin-top:2px;padding-top:4px;" if is_sub else ""
            fw      = "font-weight:600;" if is_sub else ""
            lbl_col = "color:#94a3b8;" if is_item else ""
            val_col = "color:#94a3b8;" if is_item else ""
            bd_html += (
                f'<div class="breakdown-row" style="{style_extra}">'
                f'<span class="bd-label" style="{fw}{lbl_col}">{lbl}</span>'
                f'<span class="bd-cost" style="{fw}{val_col}">{fmt(v)}</span>'
                f'</div>'
            )

        bd_html += (
            f'<div class="breakdown-row" style="border-top:2px solid #d0d8ee;margin-top:4px;padding-top:6px;">'
            f'<span class="bd-label" style="font-weight:700;">합계</span>'
            f'<span class="bd-cost" style="font-weight:700;color:{color};">{fmt(res["total_quote"])}</span>'
            f'</div>'
        )

        return f"""
<div class="carrier-card {css_class} {extra_cls}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <span class="carrier-badge {badge_class}">{name}</span>
    {best_badge}
  </div>
  <div style="margin-top:6px;min-height:22px;">{tt_html}{acct_html}</div>
  <div style="font-size:.72rem;color:#64748b;margin-top:2px;margin-bottom:2px;">{"매입 할인율" if is_import else "고객 할인율"} {disc_val:.2f}% {"적용 (원가 기준)" if is_import else "적용"}</div>
  <div class="carrier-quote" style="color:{color};">{fmt(res['total_quote'])}</div>
  <div style="font-size:.88rem;font-weight:700;color:{margin_num_color};margin-bottom:6px;">마진 {pct(res['margin_rate'])}</div>
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;padding:6px 10px;background:rgba(0,0,0,.04);border-radius:7px;">
    <span style="font-size:.72rem;color:#889aaa;font-weight:600;">원가</span>
    <span style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;color:#64748b;">{fmt(res["total_cost"])}</span>
    {(f'<span style="font-size:.65rem;color:#b08030;background:rgba(255,180,0,.13);border-radius:4px;padding:1px 5px;margin-left:4px;">+수수료{fmt(res["net_fee"])}</span>' if res.get("net_fee",0)>0 else '')}
  </div>
  <hr style="border-color:rgba(0,0,0,.08);margin:8px 0 5px;">
  <div style="font-size:.7rem;font-weight:700;color:#8899aa;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px;">견적가 상세</div>
  {_rate_ck_html}
  <div style="flex:1;">{bd_html}</div>
  <div style="margin-top:10px;">{margin_alert(res['margin_rate'], tgt_margin)}</div>
</div>"""

    # 카드 렌더링 — 수출/수입 공통: 5사 3+2 레이아웃
    if mode == "수출":
        col_d, col_fi, col_fe = st.columns(3, gap="medium")
        col_u1, col_u2, _spacer = st.columns([1, 1, 1], gap="medium")
        with col_d:  st.markdown(render_card(res_dhl,     "DHL Express",    "dhl",   "badge-dhl",   "#D40511", disc_dhl,     tt_info="1~3 영업일"), unsafe_allow_html=True)
        with col_fi: st.markdown(render_card(res_fedex,   "FedEx IP",       "fedex", "badge-fedex", "#4D148C", disc_fedex,   tt_info="1~3 영업일"), unsafe_allow_html=True)
        with col_fe: st.markdown(render_card(res_fedex_e, "FedEx Economy",  "fedex", "badge-fedex", "#6620b0", disc_fedex_e, tt_info="7~8 영업일"), unsafe_allow_html=True)
        with col_u1: st.markdown(render_card(res_ups2f,   "UPS WW Express", "ups",   "badge-ups",   "#351C15", disc_ups,     tt_info="2~5 영업일", acct_info="계정: 2F94A8"), unsafe_allow_html=True)
        with col_u2: st.markdown(render_card(res_upsb8,   "UPS WW Express", "ups",   "badge-ups",   "#351C15", disc_ups,     tt_info="2~5 영업일", acct_info="계정: B8733R"), unsafe_allow_html=True)
        with _spacer: st.empty()
    else:  # 수입: 5사 3+2 레이아웃 (수출과 동일)
        col_d, col_fi, col_fe = st.columns(3, gap="medium")
        col_u1, col_u2, _spacer = st.columns([1, 1, 1], gap="medium")
        with col_d:  st.markdown(render_card(res_dhl,     "DHL Express",    "dhl",   "badge-dhl",   "#D40511", disc_dhl,     tt_info="1~3 영업일", is_import=True), unsafe_allow_html=True)
        with col_fi: st.markdown(render_card(res_fedex,   "FedEx IP",       "fedex", "badge-fedex", "#4D148C", disc_fedex,   tt_info="1~3 영업일", is_import=True), unsafe_allow_html=True)
        with col_fe: st.markdown(render_card(res_fedex_e, "FedEx Economy",  "fedex", "badge-fedex", "#6620b0", disc_fedex_e, tt_info="7~8 영업일", is_import=True), unsafe_allow_html=True)
        with col_u1: st.markdown(render_card(res_ups2f,   "UPS WW Express", "ups",   "badge-ups",   "#351C15", disc_ups,     tt_info="2~5 영업일", is_import=True, acct_info="계정: 2F94A8"), unsafe_allow_html=True)
        with col_u2: st.markdown(render_card(res_upsb8,   "UPS WW Express", "ups",   "badge-ups",   "#351C15", disc_ups_b8,  tt_info="2~5 영업일", is_import=True, acct_info="계정: B8733R"), unsafe_allow_html=True)
        with _spacer: st.empty()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 항목별 상세 비교 테이블 (원가/청구 색상 구분) ──
    st.markdown("##### 📊 항목별 상세 비교 (5사)")

    # 운임 합계 계산 보조 (유류 통합용)
    def combined_fuel(res):
        return res.get("pub_fuel", 0) + res.get("sur_fuel_pub", 0)
    def combined_net_fuel(res):
        return res.get("net_fuel", 0) + res.get("sur_fuel", 0)

    # 5사 전체에서 등장한 부가서비스 항목명을 운송사별로 수집
    # 원가 섹션: 각 운송사 surs_detail 키
    # 견적 섹션: 동일 금액이므로 동일하게 사용

    if mode == "수출":
        carriers_5 = [
            ("DHL Express",   res_dhl,     "#ff5566"),
            ("FedEx IP",      res_fedex,   "#8855ee"),
            ("FedEx Economy", res_fedex_e, "#aa66ff"),
            ("UPS 2F94A8",    res_ups2f,   "#e8893a"),
            ("UPS B8733R",    res_upsb8,   "#d4a055"),
        ]
    else:
        carriers_5 = [
            ("DHL Express",   res_dhl,     "#ff5566"),
            ("FedEx IP",      res_fedex,   "#8855ee"),
            ("FedEx Economy", res_fedex_e, "#aa66ff"),
            ("UPS 2F94A8",    res_ups2f,   "#e8893a"),
            ("UPS B8733R",    res_upsb8,   "#d4a055"),
        ]

    # 운송사별 surs_detail에서 행 빌드 — 운송사마다 다른 이름
    def make_sur_rows(section):
        """section: 'cost' or 'quote' — 섹션 타입에 따라 배경색 다름"""
        rows = []
        for cn, res, _ in carriers_5:
            for nm in res.get("surs_detail", {}).keys():
                if nm not in [r[0] for r in rows]:
                    rows.append((nm, section))
        return rows  # [(항목명, stype), ...]

    # 행 정의: (라벨, callable(res), 섹션타입)
    # 부가서비스 행은 동적으로 삽입
    all_sur_names = []
    for _, res, _ in carriers_5:
        for nm in res.get("surs_detail", {}).keys():
            if nm not in all_sur_names:
                all_sur_names.append(nm)

    row_defs = [
        ("항공운임 (원가)",        lambda r: r.get("net_base",0), "cost"),
        ("  └ 단가/kg (원가)",     lambda r: round(r.get("net_base",0)/r.get("rate_info",{}).get("total_w",1)) if r.get("rate_info",{}).get("total_w",0)>0 else 0, "cost_rpk"),
        ("  계정수수료 3%",        lambda r: r.get("net_fee",0),  "cost"),
    ]
    for nm in all_sur_names:
        row_defs.append((f"  {nm} (원가)", lambda r, n=nm: r.get("surs_detail",{}).get(n,0), "cost"))
    row_defs += [
        ("유류할증료 (원가)",      lambda r: combined_net_fuel(r),    "cost"),
        ("▶ 원가 합계",            lambda r: r.get("total_cost",0),  "cost_sum"),
        ("항공운임 (견적)",        lambda r: r.get("pub_disc",0),    "quote"),
        ("  └ 단가/kg (견적)",     lambda r: r.get("rate_info",{}).get("disc_rpk") or 0, "quote_rpk"),
    ]
    for nm in all_sur_names:
        row_defs.append((f"  {nm}", lambda r, n=nm: r.get("surs_detail",{}).get(n,0), "quote"))
    row_defs += [
        ("유류할증료",        lambda r: combined_fuel(r),         "quote"),
        ("▶ 청구가 합계",     lambda r: r.get("total_quote",0),   "quote_sum"),
        ("마진액",            lambda r: r.get("margin_amt",0),    "margin"),
    ]

    # 섹션별 색상 결정
    def row_bg(stype):
        return {"cost":"#eaf6fd","cost_rpk":"#ddf0fa","cost_sum":"#c5e3f5","quote":"#f0faf2","quote_rpk":"#e6f9ec","quote_sum":"#c5eece","margin":"#eaecff"}.get(stype,"#fff")

    cmp = f"""<table style="width:100%;border-collapse:collapse;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.07);font-size:.8rem;">
<thead><tr style="background:{_tbl_hdr_bg};">
  <th style="padding:10px 12px;text-align:left;color:{_tbl_hdr_sub};font-size:.7rem;width:18%;">구분</th>"""
    for cn, _, cc in carriers_5:
        cmp += f'<th style="padding:10px 8px;text-align:right;color:{cc};font-size:.7rem;">{cn}</th>'
    cmp += "</tr></thead><tbody>"

    # 섹션 구분선 삽입
    prev_section = None
    for label, val_fn, stype in row_defs:
        bg = row_bg(stype)
        section_grp = stype.replace("_sum","").replace("_rpk","")
        if prev_section and section_grp != prev_section:
            cmp += f'<tr><td colspan="{1+len(carriers_5)}" style="padding:0;background:#d0d8e8;height:3px;"></td></tr>'
        prev_section = section_grp

        is_sum    = stype.endswith("_sum")
        is_rpk    = stype.endswith("_rpk")
        is_indent = label.startswith("  ") or is_rpk
        lbl_clean = label.lstrip("▶ ").lstrip()
        fw        = "font-weight:700;" if is_sum else ""
        lbl_col   = "color:#94a3b8;" if is_indent else ("color:#334155;" if not is_sum else "color:#1e3a8a;")
        fs        = "font-size:.74rem;" if is_indent else ""
        cmp += f'<tr style="background:{bg};">'
        icon = {"cost":"💰","cost_rpk":"📐","cost_sum":"💰","quote":"🧾","quote_rpk":"📐","quote_sum":"🧾","margin":"📈"}.get(stype,"")
        icon_str = "" if is_indent else icon + " "
        indent_pad = "padding-left:22px;" if is_indent else ""
        cmp += f'<td style="padding:6px 12px;{fw}{lbl_col}{fs}{indent_pad}">{icon_str}{lbl_clean}</td>'
        for _, res, cc in carriers_5:
            if res.get("no_service"):
                cmp += f'<td style="padding:6px 8px;text-align:right;font-size:.75rem;color:#b91c1c;font-weight:700;">🚫 서비스불가</td>'
                continue
            v   = val_fn(res)
            if is_rpk:
                val = (f"{int(v):,}원/kg" if v and v > 0 else '<span style="color:#ccc;">-</span>')
            else:
                val = fmt(v) if v != 0 else '<span style="color:#ccc;">-</span>'
            col = cc if is_sum else ("#99aabb" if is_indent else "#2a3a4a")
            cmp += f'<td style="padding:6px 8px;text-align:right;{fw}color:{col};font-family:monospace;{fs}">{val}</td>'
        cmp += "</tr>"

    # 마진율 행
    cmp += f'<tr style="background:#dde2ff;"><td style="padding:8px 12px;font-weight:700;color:#334;">📊 마진율</td>'
    for _, res, cc in carriers_5:
        if res.get("no_service"):
            cmp += f'<td style="padding:8px 8px;text-align:right;font-size:.75rem;color:#b91c1c;font-weight:700;">🚫</td>'
            continue
        mr = res.get("margin_rate",0)
        mr_col = "#009944" if mr>=tgt_margin else ("#ff7700" if mr>=15 else "#cc0022")
        cmp += f'<td style="padding:8px 8px;text-align:right;font-weight:700;color:{mr_col};font-family:monospace;">{pct(mr)}</td>'
    cmp += "</tr>"

    # 범례
    cmp += f"""</tbody></table>
<div style="margin-top:8px;font-size:.68rem;color:#64748b;display:flex;gap:16px;">
  <span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#c5e3f5;border-radius:2px;display:inline-block;"></span>원가 영역</span>
  <span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#c5eece;border-radius:2px;display:inline-block;"></span>청구 영역</span>
  <span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;background:#dde2ff;border-radius:2px;display:inline-block;"></span>마진</span>
</div>"""
    st.markdown(cmp, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TAB 2: 상세 명세
# ─────────────────────────────────────────────
with tab2:
    if len(ct_data) > 1:
        st.markdown(f"##### 📦 C/T별 상세 명세 (총 {len(ct_data)} C/T)")
        for i, r in enumerate(ct_results):
            winfo = r["winfo"]
            with st.expander(f"C/T {i+1} — {winfo['rounded']}kg 청구 ({winfo['basis']})", expanded=True):
                ec1, ec2, ec3, ec4, ec5 = st.columns(5)
                def ct_table(res_ct, carrier_name, color):
                    surs_str = ", ".join(res_ct["surs"].keys()) or "없음"
                    return f"""
<div style="background:white;border-radius:10px;padding:12px;border:1px solid #e0e4f0;">
<div style="font-weight:700;color:{color};margin-bottom:6px;font-size:.8rem;">{carrier_name}</div>
<div style="font-size:.75rem;color:#334155;">원가: <b>{fmt(res_ct['net'])}</b></div>
<div style="font-size:.75rem;color:#334155;">Pub: <b>{fmt(res_ct['pub'])}</b></div>
<div style="font-size:.7rem;color:#64748b;margin-top:4px;">할증: {surs_str}</div>
</div>"""
                with ec1: st.markdown(ct_table(r["dhl"],    "DHL Express",      "#D40511"), unsafe_allow_html=True)
                with ec2: st.markdown(ct_table(r["fedex"],  "FedEx IP",          "#4D148C"), unsafe_allow_html=True)
                with ec3: st.markdown(ct_table(r["fedexec"],"FedEx Economy",     "#6620b0"), unsafe_allow_html=True)
                with ec4: st.markdown(ct_table(r["ups2f"],  "UPS WW (2F94A8)",   "#351C15"), unsafe_allow_html=True)
                with ec5: st.markdown(ct_table(r["upsb8"],  "UPS WW (B8733R)",   "#5c3a1e"), unsafe_allow_html=True)
    else:
        st.info("C/T가 1개일 때는 '5사 비교 분석' 탭에서 상세 내역을 확인하세요.")

    st.markdown("---")
    st.markdown("**⚖️ 중량 상세**")
    wt_df = pd.DataFrame([
        {"항목": f"C/T {i+1}", "실중량(kg)": ct["wt"],
         "부피중량(kg)": calc_weight(ct["wt"], ct["L"], ct["W"], ct["H"])["volume"],
         "청구중량(kg)": calc_weight(ct["wt"], ct["L"], ct["W"], ct["H"])["rounded"],
         "기준": calc_weight(ct["wt"], ct["L"], ct["W"], ct["H"])["basis"]}
        for i, ct in enumerate(ct_data)
    ] + [{"항목": "합계", "실중량(kg)": total_actual_wt,
           "부피중량(kg)": round(total_vol_wt, 2), "청구중량(kg)": total_chargeable, "기준": "─"}])
    st.dataframe(wt_df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# TAB 3: PDF 견적서
# ─────────────────────────────────────────────
with tab3:
    st.markdown("##### 📄 PDF 견적서 발행")
    st.markdown("포함할 운송사를 선택하세요. 선택한 운송사만 견적서에 인쇄됩니다.")

    pc1, pc2, pc3, pc4, pc5 = st.columns(5)
    with pc1: sel_dhl    = st.checkbox("🔴 DHL Express",    value=True,  key="sel_dhl")
    with pc2: sel_fedex  = st.checkbox("🟣 FedEx IP",       value=True,  key="sel_fedex")
    with pc3: sel_fedexe = st.checkbox("🟦 FedEx Economy",  value=False, key="sel_fedexe")
    if mode == "수출":
        with pc4: sel_ups2f = st.checkbox("🟤 UPS 2F94A8",    value=False, key="sel_ups2f")
        with pc5: sel_upsb8 = st.checkbox("🟫 UPS B8733R",    value=False, key="sel_upsb8")
        selected_map = {
            "DHL Express":   sel_dhl,
            "FedEx IP":      sel_fedex,
            "FedEx Economy": sel_fedexe,
            "UPS 2F94A8":    sel_ups2f,
            "UPS B8733R":    sel_upsb8,
        }
        disc_map_pdf = {
            "DHL Express":   disc_dhl,
            "FedEx IP":      disc_fedex,
            "FedEx Economy": disc_fedex_e,
            "UPS 2F94A8":    disc_ups,
            "UPS B8733R":    disc_ups,
        }
    else:  # 수입: UPS 2계정 각각 선택 가능
        with pc4: sel_ups2f_i = st.checkbox("🟤 UPS 2F94A8",    value=False, key="sel_ups2f_imp")
        with pc5: sel_upsb8_i = st.checkbox("🟫 UPS B8733R",    value=False, key="sel_upsb8_imp")
        selected_map = {
            "DHL Express":   sel_dhl,
            "FedEx IP":      sel_fedex,
            "FedEx Economy": sel_fedexe,
            "UPS 2F94A8":    sel_ups2f_i,
            "UPS B8733R":    sel_upsb8_i,
        }
        disc_map_pdf = {
            "DHL Express":   disc_dhl,
            "FedEx IP":      disc_fedex,
            "FedEx Economy": disc_fedex_e,
            "UPS 2F94A8":    disc_ups,
            "UPS B8733R":    disc_ups_b8,
        }

    st.markdown("---")
    # ── PDF 레이아웃 선택 ──
    layout_choice = st.radio(
        "📐 PDF 견적서 레이아웃",
        ["📋 표형 (여러 운송사 비교)", "🃏 카드형 (운송사별 개별 박스)"],
        horizontal=True,
        key="pdf_layout"
    )
    pdf_layout = "table" if layout_choice.startswith("📋") else "card"

    st.markdown('<div style="font-size:.75rem;color:#64748b;margin-top:-8px;margin-bottom:8px;">'
                '표형: 운송사를 나란히 비교 | 카드형: 각 운송사를 박스로 개별 표시 (고객 전달용 추천)</div>',
                unsafe_allow_html=True)

    n_selected = sum(selected_map.values())

    if n_selected > 0:
        st.markdown(f"<div style='background:white;border-radius:10px;padding:14px 18px;border:1px solid #dde2ee;margin:10px 0;'>"
                    f"<b>선택된 운송사:</b> {', '.join(k for k,v in selected_map.items() if v)}<br>"
                    f"<b>고객사:</b> {customer or '(주)에어브리지'} &nbsp;|&nbsp; "
                    f"<b>목적지:</b> {dest_country} &nbsp;|&nbsp; "
                    f"<b>청구중량:</b> {total_chargeable:.1f}kg &nbsp;|&nbsp; "
                    f"<b>C/T:</b> {len(ct_data)}개</div>",
                    unsafe_allow_html=True)
    else:
        st.warning("⚠️ 최소 1개 이상의 운송사를 선택해주세요.")

    st.markdown('<div class="pdf-btn">', unsafe_allow_html=True)
    if st.button("📄 PDF 견적서 생성", disabled=(n_selected == 0)):
        with st.spinner("PDF 생성 중..."):
            pdf_bytes = generate_pdf(
                quote_num=quote_num,
                customer=customer or "(주)에어브리지",
                dest_country=dest_country,
                zone_label=f"DHL Z{dhl_zone} / FedEx Z{fx_zone} / UPS Z{ups_zone_num}",
                ct_count=len(ct_data),
                total_chargeable=total_chargeable,
                fuel_dhl=fuel_dhl,
                fuel_fedex=fuel_fedex,
                fuel_ups=fuel_ups,
                selected=selected_map,
                results=all_results,
                disc_map=disc_map_pdf,
                notes=notes_input,
                layout=pdf_layout,
                our_company=st.session_state.get("our_company",""),
                our_contact=st.session_state.get("our_contact",""),
                our_phone=st.session_state.get("our_phone",""),
                our_email=st.session_state.get("our_email",""),
                ct_data=ct_data,
                total_actual_wt=total_actual_wt,
                is_doc=is_doc,
                mode=mode,
            )
        st.success("✅ PDF 견적서 생성 완료!")
        fn = f"견적서_{customer or '에어브리지'}_{dest_country[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label="⬇️ 견적서 다운로드",
            data=pdf_bytes,
            file_name=fn,
            mime="application/pdf",
            use_container_width=True,
        )
        st.markdown("**💡 메일 발송 팁:** PDF를 첨부하거나, 아래 복사용 텍스트를 이메일 본문에 붙여넣기 하세요.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════
    # 📧 이메일 견적 복사용
    # 설계 원칙 (DHL·FedEx·UPS 영업팀 / 고객사 해외영업팀·수출입관리팀·회계팀 합의):
    #   - 운임 항목을 항목별로 명확히 나열 (항공운임 / 부가서비스 / 유류할증료 / 합계)
    #   - 회계팀: 항목별 금액 분리 → 비용처리·증빙 용이
    #   - 수출입관리팀: C/T 수량·중량·화물구분 명시
    #   - 해외영업팀: T/T·목적지·최저가 추천 상단 배치
    #   - DHL/FedEx/UPS 영업팀: 유류할증료율·Zone 명시로 검증 가능
    #   - = / - 구분선만 사용 (모든 이메일 클라이언트 완전 호환)
    # ══════════════════════════════════════════════════════════════════

    st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
  <div style="width:5px;height:32px;background:linear-gradient(180deg,{_main_accent_dark},{_main_accent});
              border-radius:3px;flex-shrink:0;"></div>
  <div>
    <div style="font-size:1.05rem;font-weight:800;color:{_main_accent_dark};
                letter-spacing:.03em;">📧 이메일 견적 복사용</div>
    <div style="font-size:.71rem;color:#64748b;margin-top:2px;">
      항목별 상세 나열 양식 — 회계·수출입관리·해외영업팀 공용 / Gmail·Outlook·네이버메일 호환
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    _cust_nm    = customer or "(주)에어브리지"
    _date_str   = datetime.now().strftime("%Y년 %m월 %d일")
    _kr_country = COUNTRY_KR.get(dest_country, dest_country)
    _cargo_type = "서류 (Document)" if is_doc else "물품 (Non-Document)"
    _mode_str   = "수입 (Import)" if mode == "수입" else "수출 (Export)"

    _DIV_MAJOR = "=" * 60
    _DIV_MID   = "-" * 60
    _DIV_MINOR = "·" * 60

    _TT = {
        "DHL Express":   "1~3 영업일",
        "FedEx IP":      "1~3 영업일",
        "FedEx Economy": "5~7 영업일",
        "UPS 2F94A8":    "2~5 영업일",
        "UPS B8733R":    "2~5 영업일",
    }

    def _carrier_disp(name):
        if "UPS" in name: return "UPS Worldwide Express"
        return name

    def _fw(n):
        return f"₩{int(n):,}"

    def _fwp(n, pct_val):
        return f"₩{int(n):,}  ({pct_val:.2f}%)"

    _active = {n: r for n, r in all_results.items() if selected_map.get(n)}
    _best   = min(_active, key=lambda n: _active[n]["total_quote"]) if _active else None

    _co = st.session_state.get("our_company", "") or "(주)에어브리지"
    _ct = st.session_state.get("our_contact", "")
    _ph = st.session_state.get("our_phone", "")
    _em = st.session_state.get("our_email", "")



    from math import ceil as _ceil2

    _kr_c    = COUNTRY_KR.get(dest_country, dest_country)
    _mode_s  = '수입 (Import)' if mode == '수입' else '수출 (Export)'
    _carg_s  = '서류 (Document)' if is_doc else '물품 (Non-Document)'
    _co      = st.session_state.get('our_company', '') or '(주)에어브리지'
    _ct_nm   = st.session_state.get('our_contact', '')
    _ph      = st.session_state.get('our_phone', '')
    _em_addr = st.session_state.get('our_email', '')
    _TT2 = {
        'DHL Express':'1~3 영업일', 'FedEx IP':'1~3 영업일',
        'FedEx Economy':'5~7 영업일', 'UPS 2F94A8':'2~5 영업일', 'UPS B8733R':'2~5 영업일',
    }
    _active = {n: r for n, r in all_results.items() if selected_map.get(n)}
    _best   = min(_active, key=lambda n: _active[n]['total_quote']) if _active else None
    _notices = [
        ('유효기간',   '발행일로부터 7일 (이후 운임 변동 가능)'),
        ('추가비용',   '관세·부가세·통관비·현지비용은 실비 별도 청구'),
        ('유류할증료', '발송일 기준 적용 / DHL 매월, FedEx·UPS 매주 변동'),
        ('외곽지역',   '도서·산간 지역 배송 시 RAS/ODA 추가요금 가능'),
        ('반송비용',   '현지 통관 거부·반송 시 수입운임 및 현지비용 발송자 부담'),
        ('중량기준',   'C/T당 실중량 25kg 초과 시 비규격 추가비용 가능'),
        ('배송지연',   'T/T는 예상치이며 항공·통관 지연으로 보장되지 않습니다'),
    ]
    if notes_input.strip():
        _notices.append(('특이사항', notes_input.strip()))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HTML 이메일 빌더 (Outlook / Gmail 표 붙여넣기)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _H(t):
        return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

    TS  = 'font-family:Arial,sans-serif;'   # table base
    TD0 = 'padding:7px 14px;font-size:12px;'

    def _tbl(rows_html, mb=16):
        return (
            '<table style="width:100%;max-width:620px;border-collapse:collapse;'
            'border:1px solid #cbd5e1;margin-bottom:' + str(mb) + 'px;' + TS + '">'
            + rows_html + '</table>'
        )

    def _hdr(title, bg='#1e3a8a', fg='#ffffff', colspan=2):
        return (
            '<tr><td colspan="' + str(colspan) + '" style="background:' + bg + ';color:' + fg + ';'
            'font-size:13px;font-weight:700;padding:9px 14px;' + TS + '">'
            + _H(title) + '</td></tr>'
        )

    def _row2(lbl, val, shade=False):
        bg = '#f4f6ff' if shade else '#ffffff'
        return (
            '<tr style="background:' + bg + ';">'
            '<td style="' + TD0 + 'color:#64748b;width:160px;white-space:nowrap;">' + _H(lbl) + '</td>'
            '<td style="' + TD0 + 'color:#1e293b;font-weight:600;">' + _H(val) + '</td>'
            '</tr>'
        )

    def _div_row(colspan=2):
        return '<tr><td colspan="' + str(colspan) + '" style="height:1px;background:#e2e8f0;padding:0;"></td></tr>'

    def _amt_s(n):      return '\u20a9' + format(int(n), ',')
    def _amtp_s(n, p):  return '\u20a9' + format(int(n), ',') + '  (' + '{:.2f}'.format(p) + '%)'

    h = []
    h.append('<div style="' + TS + 'font-size:13px;color:#1e293b;line-height:1.7;max-width:640px;">')

    # 인사말
    h.append(
        '<p style="margin:0 0 18px;">'
        '안녕하세요, <b>' + _H(_cust_nm) + '</b> 담당자님.<br><br>'
        '국제특송 운임 견적을 아래와 같이 안내드립니다.<br>'
        '검토 후 추가 문의 사항은 언제든 연락 주시기 바랍니다.'
        '</p>'
    )

    # ── 견적 기본 정보 ──
    rows = _hdr('견적 기본 정보')
    for idx, (lbl, val) in enumerate([
        ('견적번호',    quote_num),
        ('견적일자',    _date_str),
        ('유효기간',    '발행일로부터 7일'),
        ('수신',        _cust_nm),
        ('운송구분',    _mode_s),
        ('목적지',      _kr_c + '  (' + dest_country + ')'),
        ('화물구분',    _carg_s),
        ('총 박스수',   str(len(ct_data)) + ' BOX'),
        ('실중량 합계', '{:.1f} kg'.format(total_actual_wt)),
        ('청구중량 합계', '{:.1f} kg'.format(total_chargeable)),
    ]):
        rows += _row2(lbl, val, shade=(idx % 2 == 0))
    h.append(_tbl(rows))

    # ── 화물 명세 ──
    if ct_data:
        TH = 'padding:7px 10px;font-size:11px;font-weight:700;color:#475569;background:#e8edf8;text-align:'
        rows = _hdr('화물 명세')
        rows += (
            '<tr>'
            '<th style="' + TH + 'center;width:48px;">BOX</th>'
            '<th style="' + TH + 'right;">실중량</th>'
            '<th style="' + TH + 'center;">크기 (cm)</th>'
            '<th style="' + TH + 'right;">부피중량</th>'
            '<th style="' + TH + 'right;">청구중량</th>'
            '<th style="' + TH + 'center;">기준</th>'
            '</tr>'
        )
        for idx2, ct in enumerate(ct_data):
            vw  = round(ct['L'] * ct['W'] * ct['H'] / 5000, 2)
            cw2 = round(_ceil2(max(ct['wt'], vw) * 2) / 2, 1)
            bas = '부피중량' if vw > ct['wt'] else '실중량'
            bg  = '#f8faff' if idx2 % 2 == 0 else '#ffffff'
            TD  = 'padding:6px 10px;font-size:12px;'
            rows += (
                '<tr style="background:' + bg + ';">'
                '<td style="' + TD + 'text-align:center;color:#94a3b8;">{:02d}</td>'.format(idx2+1) +
                '<td style="' + TD + 'text-align:right;">{:.1f} kg</td>'.format(ct['wt']) +
                '<td style="' + TD + 'text-align:center;">{:.0f} × {:.0f} × {:.0f}</td>'.format(ct['L'], ct['W'], ct['H']) +
                '<td style="' + TD + 'text-align:right;color:#94a3b8;">{:.2f} kg</td>'.format(vw) +
                '<td style="' + TD + 'text-align:right;font-weight:600;">{:.1f} kg</td>'.format(cw2) +
                '<td style="' + TD + 'text-align:center;color:#0369a1;">' + bas + '</td>'
                '</tr>'
            )
        TD2 = 'padding:7px 10px;font-size:12px;font-weight:700;background:#dde4f5;'
        rows += (
            '<tr>'
            '<td style="' + TD2 + 'text-align:center;">합계</td>'
            '<td style="' + TD2 + 'text-align:right;">{:.1f} kg</td>'.format(total_actual_wt) +
            '<td colspan="2" style="' + TD2 + '"></td>'
            '<td style="' + TD2 + 'text-align:right;">{:.1f} kg</td>'.format(total_chargeable) +
            '<td style="' + TD2 + '"></td>'
            '</tr>'
        )
        h.append(_tbl(rows))

    # ── 운임 견적 상세 ──
    h.append('<p style="font-size:11px;color:#94a3b8;margin:0 0 8px;">※ 관세·부가세·통관비·현지비용은 실비 별도 청구</p>')

    for _nm, _res in _active.items():
        _fpct    = fuel_dhl if 'DHL' in _nm else (fuel_ups if 'UPS' in _nm else fuel_fedex)
        _tt      = _TT2.get(_nm, '')
        _is_best = (_nm == _best)
        _fuel_a  = _res.get('pub_fuel', 0) + _res.get('sur_fuel_pub', 0)
        _surs    = _res.get('surs_detail', {})
        _sur_tot = _res.get('sur_total', 0)
        _air_amt = _res.get('pub_disc', 0)
        _total_q = _res.get('total_quote', 0)
        _ri      = _res.get('rate_info', {})
        _drpk    = _ri.get('disc_rpk') or _ri.get('rate_per_kg')
        _dname   = 'UPS Worldwide Express' if 'UPS' in _nm else _nm
        _zinfo   = ('DHL Zone ' + str(dhl_zone) if 'DHL' in _nm
                    else 'FedEx Zone ' + str(fx_zone) if 'FedEx' in _nm
                    else 'UPS Zone ' + str(ups_zone_num))
        _hdr_bg  = ('#C00010' if 'DHL' in _nm
                    else '#4D148C' if 'FedEx IP' == _nm
                    else '#5510a0' if 'Economy' in _nm
                    else '#6b3320')
        _star = (
            '&nbsp;&nbsp;<span style="background:#fef9c3;color:#92400e;'
            'font-size:11px;padding:2px 8px;border-radius:3px;">★ 최저가 추천</span>'
            if _is_best else ''
        )

        rows = (
            '<tr><td colspan="2" style="background:' + _hdr_bg + ';color:#fff;'
            'font-size:13px;font-weight:700;padding:9px 14px;">'
            + _H(_dname) + _star + '</td></tr>'
        )
        rows += (
            '<tr><td colspan="2" style="background:#f8f9fa;padding:5px 14px;'
            'font-size:11px;color:#64748b;">'
            '배송소요일: ' + _H(_tt) + '&nbsp;&nbsp;|&nbsp;&nbsp;' + _H(_zinfo) +
            '</td></tr>'
        )

        # 항공운임
        _air_lbl = '항공운임' + ('  (' + format(int(_drpk), ',') + '원/kg)' if _drpk else '')
        rows += (
            '<tr style="background:#f0f4ff;">'
            '<td style="' + TD0 + 'color:#334155;">' + _H(_air_lbl) + '</td>'
            '<td style="' + TD0 + 'text-align:right;font-weight:600;">' + _H(_amt_s(_air_amt)) + '</td>'
            '</tr>'
        )

        # 부가서비스 항목
        for _sn, _sv in _surs.items():
            rows += (
                '<tr style="background:#fafbff;">'
                '<td style="' + TD0 + 'color:#64748b;padding-left:26px;">└ ' + _H(_sn) + '</td>'
                '<td style="' + TD0 + 'text-align:right;color:#64748b;">' + _H(_amt_s(_sv)) + '</td>'
                '</tr>'
            )
        if len(_surs) >= 2:
            rows += (
                '<tr style="background:#f0f4ff;">'
                '<td style="' + TD0 + 'color:#334155;">부가서비스 소계</td>'
                '<td style="' + TD0 + 'text-align:right;font-weight:600;">' + _H(_amt_s(_sur_tot)) + '</td>'
                '</tr>'
            )

        # 유류할증료
        rows += (
            '<tr style="background:#fafbff;">'
            '<td style="' + TD0 + 'color:#64748b;">유류할증료</td>'
            '<td style="' + TD0 + 'text-align:right;color:#64748b;">' + _H(_amtp_s(_fuel_a, _fpct)) + '</td>'
            '</tr>'
        )

        # 청구금액 합계
        rows += (
            '<tr style="background:#1e3a8a;">'
            '<td style="' + TD0 + 'color:#fff;font-weight:700;">청구금액 합계</td>'
            '<td style="' + TD0 + 'text-align:right;font-size:14px;font-weight:800;color:#fbbf24;">'
            + _H(_amt_s(_total_q)) + '</td>'
            '</tr>'
        )
        h.append(_tbl(rows, mb=12))

    # ── 안내사항 ──
    rows = _hdr('안내 사항', bg='#334155')
    for idx3, (lbl, txt) in enumerate(_notices):
        rows += _row2(lbl, txt, shade=(idx3 % 2 == 0))
    h.append(_tbl(rows))

    # ── 서명 ──
    sig = '<b>' + _H(_co) + '</b>'
    if _ct_nm:   sig += '<br>담당자: ' + _H(_ct_nm)
    if _ph:      sig += '<br>연락처: ' + _H(_ph)
    if _em_addr: sig += '<br>이메일: ' + _H(_em_addr)
    h.append(
        '<p style="margin:0;font-size:13px;">'
        '추가 문의 및 발송 의뢰는 언제든지 연락 주시기 바랍니다.<br>'
        '감사합니다.<br><br>' + sig + '</p>'
    )
    h.append('</div>')
    _html_email = ''.join(h)

    # ── 플레인텍스트 (미리보기 전용) ──
    ml = []
    W2 = 54
    def _pr(lbl, val, w=20):
        return '  ' + lbl + ' ' + '.' * max(2, w - len(lbl)) + ' ' + val
    def _pa(lbl, n, w=20):
        return _pr(lbl, '\u20a9' + format(int(n), ','), w)
    def _pap(lbl, n, p, w=20):
        return _pr(lbl, '\u20a9' + format(int(n), ',') + '  ({:.2f}%)'.format(p), w)
    ml += ['안녕하세요, ' + _cust_nm + ' 담당자님.', '',
           '국제특송 운임 견적을 아래와 같이 안내드립니다.', '']
    ml += ['='*W2, '  견적 기본 정보', '='*W2]
    ml += [_pr('견적번호', quote_num), _pr('견적일자', _date_str),
           _pr('유효기간', '발행일로부터 7일'), '-'*W2,
           _pr('수신', _cust_nm), _pr('운송구분', _mode_s),
           _pr('목적지', _kr_c + ' (' + dest_country + ')'), '-'*W2,
           _pr('화물구분', _carg_s),
           _pr('총 박스수', str(len(ct_data)) + ' BOX'),
           _pr('실중량 합계', '{:.1f} kg'.format(total_actual_wt)),
           _pr('청구중량 합계', '{:.1f} kg'.format(total_chargeable)), '']
    if ct_data:
        ml += ['='*W2, '  화물 명세', '='*W2]
        for ii, ct in enumerate(ct_data):
            vw  = round(ct['L']*ct['W']*ct['H']/5000, 2)
            cw2 = round(_ceil2(max(ct['wt'],vw)*2)/2, 1)
            bas = '부피중량' if vw > ct['wt'] else '실중량'
            ml.append('  BOX {:02d}  {:.1f}kg  {:.0f}x{:.0f}x{:.0f}cm  청구 {:.1f}kg ({})'.format(
                ii+1, ct['wt'], ct['L'], ct['W'], ct['H'], cw2, bas))
        ml += ['-'*W2, '  합계  실중량 {:.1f}kg  /  청구중량 {:.1f}kg'.format(
            total_actual_wt, total_chargeable), '']
    ml += ['='*W2, '  운임 견적 상세', '='*W2]
    for _nm2, _res2 in _active.items():
        _fpct2   = fuel_dhl if 'DHL' in _nm2 else (fuel_ups if 'UPS' in _nm2 else fuel_fedex)
        _tt2     = _TT2.get(_nm2, '')
        _ib2     = (_nm2 == _best)
        _fa2     = _res2.get('pub_fuel',0) + _res2.get('sur_fuel_pub',0)
        _su2     = _res2.get('surs_detail',{})
        _st2     = _res2.get('sur_total',0)
        _aa2     = _res2.get('pub_disc',0)
        _tq2     = _res2.get('total_quote',0)
        _ri2     = _res2.get('rate_info',{})
        _dp2     = _ri2.get('disc_rpk') or _ri2.get('rate_per_kg')
        _dn2     = 'UPS Worldwide Express' if 'UPS' in _nm2 else _nm2
        _zi2     = ('DHL Zone ' + str(dhl_zone) if 'DHL' in _nm2
                    else 'FedEx Zone ' + str(fx_zone) if 'FedEx' in _nm2
                    else 'UPS Zone ' + str(ups_zone_num))
        ml += ['-'*W2, '  ▶ ' + _dn2 + ('  ★ 최저가 추천' if _ib2 else ''),
               '     ' + _tt2 + '  (' + _zi2 + ')', '-'*W2]
        if _dp2:
            ml.append(_pr('항공운임', '\u20a9' + format(int(_aa2), ',') + '  (' + format(int(_dp2), ',') + '원/kg)'))
        else:
            ml.append(_pa('항공운임', _aa2))
        for _sn2, _sv2 in _su2.items():
            ml.append(_pa('  + ' + _sn2, _sv2))
        if len(_su2) >= 2:
            ml.append(_pa('부가서비스 소계', _st2))
        ml.append(_pap('유류할증료', _fa2, _fpct2))
        ml += ['  ' + '─'*(W2-2), _pa('청구금액 합계', _tq2), '']
    ml += ['='*W2, '  안내 사항', '='*W2]
    for lbl2, txt2 in _notices:
        ml.append('  * ' + lbl2 + ': ' + txt2)
    ml += ['='*W2, '', '추가 문의 및 발송 의뢰는 언제든지 연락 주시기 바랍니다.',
           '감사합니다.', '', '-'*W2, '  ' + _co]
    if _ct_nm:   ml.append('  담당자  ' + _ct_nm)
    if _ph:      ml.append('  연락처  ' + _ph)
    if _em_addr: ml.append('  이메일  ' + _em_addr)
    ml.append('-'*W2)
    _copytext = "\n".join(ml)

    # ── UI: 미리보기 박스 ──
    st.markdown("""
<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:10px;
            padding:12px 16px;margin-bottom:10px;font-size:.72rem;color:#475569;
            display:flex;gap:18px;flex-wrap:wrap;">
  <span>✅ <b>Gmail</b> 호환</span>
  <span>✅ <b>Outlook</b> 호환</span>
  <span>✅ <b>네이버메일</b> 호환</span>
  <span>✅ <b>iPhone Mail</b> 호환</span>
  <span>✅ <b>모바일 Android</b> 호환</span>
</div>""", unsafe_allow_html=True)

    st.text_area(
        "이메일 본문",
        _copytext,
        height=500,
        help="텍스트 영역 클릭 → Ctrl+A(전체선택) → Ctrl+C(복사) 후 이메일 본문에 붙여넣기",
        label_visibility="collapsed",
    )


    # ── 복사 버튼 — HTML + 플레인텍스트 동시 클립보드 (Outlook/Gmail 표 붙여넣기) ──
    import base64 as _b64m
    _b64_html  = _b64m.b64encode(_html_email.encode('utf-8')).decode('ascii')
    _b64_plain = _b64m.b64encode(_copytext.encode('utf-8')).decode('ascii')

    _copy_html = """<!DOCTYPE html>
<html><body style="margin:0;padding:0;font-family:Arial,sans-serif;">
<button id="copybtn" onclick="doCopy()" style="
  display:block;width:100%;padding:12px 0;
  background:linear-gradient(135deg,#1e3a8a,#2563eb);
  color:#fff;border:none;border-radius:9px;
  font-size:14px;font-weight:800;cursor:pointer;
  box-shadow:0 3px 14px rgba(37,99,235,.3);
  letter-spacing:.04em;">&#128203; 이메일 본문 복사 (표 포함)</button>
<div id="msg" style="margin-top:8px;font-size:12px;text-align:center;min-height:18px;color:#059669;"></div>
<script>
var B64H  = '""" + _b64_html + """';
var B64P  = '""" + _b64_plain + """';
function decode(b64) {
  var bin=atob(b64), bytes=new Uint8Array(bin.length);
  for(var i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
  return new TextDecoder('utf-8').decode(bytes);
}
function showOK() {
  var btn=document.getElementById('copybtn');
  var msg=document.getElementById('msg');
  btn.innerHTML='&#10003; 복사 완료!';
  btn.style.background='linear-gradient(135deg,#059669,#047857)';
  msg.innerHTML='&#10003; 클립보드에 복사되었습니다. 아웃룩/Gmail에 붙여넣기 하세요.';
  setTimeout(function(){
    btn.innerHTML='&#128203; 이메일 본문 복사 (표 포함)';
    btn.style.background='linear-gradient(135deg,#1e3a8a,#2563eb)';
    msg.innerHTML='';
  }, 3000);
}
function showFail() {
  document.getElementById('msg').style.color='#dc2626';
  document.getElementById('msg').innerHTML='&#10005; 복사 실패 — 아래 텍스트를 직접 복사하세요.';
}
function doCopy() {
  var htmlText  = decode(B64H);
  var plainText = decode(B64P);
  if(window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {
    var item = new ClipboardItem({
      'text/html':  new Blob([htmlText],  {type:'text/html'}),
      'text/plain': new Blob([plainText], {type:'text/plain'})
    });
    navigator.clipboard.write([item]).then(showOK).catch(function(){ fallback(plainText); });
  } else if(navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(plainText).then(showOK).catch(function(){ fallback(plainText); });
  } else {
    fallback(plainText);
  }
}
function fallback(txt) {
  var ta=document.createElement('textarea');
  ta.value=txt; ta.style.cssText='position:fixed;top:0;left:0;opacity:0.01;';
  document.body.appendChild(ta); ta.focus(); ta.select();
  try{ document.execCommand('copy'); showOK(); } catch(e){ showFail(); }
  document.body.removeChild(ta);
}
</script>
</body></html>"""

    st.components.v1.html(_copy_html, height=80)


st.markdown(f'<div style="text-align:center;padding:12px 0;color:#94a3b8;font-size:.7rem;">에어브리지 운임계산기 v4.2 · DHL + FedEx IP/Economy + UPS(2F94A8/B8733R) · 관세·세금·통관비 별도</div>', unsafe_allow_html=True)
