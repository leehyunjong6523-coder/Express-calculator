"""구글 시트 고객 할인율 로드 (Streamlit 의존성 없음)"""
import pandas as pd
import time

_SHEET_ID  = "1uiSCTWoajvCps0F7Ps41lZ427Xt21yr7JEVOzJPrqdM"
_SHEET_GID = "1287836905"

_cache_df = None
_cache_time = 0
_CACHE_TTL = 60  # 1분

def clear_cache():
    global _cache_df, _cache_time
    _cache_df   = None
    _cache_time = 0

def load_customer_db() -> pd.DataFrame:
    global _cache_df, _cache_time
    now = time.time()
    if _cache_df is not None and (now - _cache_time) < _CACHE_TTL:
        return _cache_df

    url = (f"https://docs.google.com/spreadsheets/d/{_SHEET_ID}"
           f"/export?format=csv&gid={_SHEET_GID}")
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        need = ["회사명", "DHL OUT", "UPS OUT", "FedEx OUT", "DHL IN", "UPS IN", "FedEx IN"]
        for c in need:
            if c not in df.columns:
                df[c] = "0"
        df = df[need].copy()
        df["회사명"] = df["회사명"].fillna("").str.strip()
        df = df[df["회사명"] != ""].reset_index(drop=True)
        for c in need[1:]:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace("%", "").str.strip(),
                errors="coerce").fillna(0)
        _cache_df = df
        _cache_time = now
        return df
    except Exception as e:
        print(f"[Google Sheets] 로드 실패: {e}")
        return pd.DataFrame(columns=["회사명","DHL OUT","UPS OUT","FedEx OUT","DHL IN","UPS IN","FedEx IN"])


def get_customer_list() -> list:
    df = load_customer_db()
    if df.empty:
        return []
    return sorted(df["회사명"].tolist())


def get_customer_disc(company: str, mode: str) -> dict:
    """고객명 + 모드(수출/수입) → 할인율 dict + 디버그 정보"""
    df = load_customer_db()
    if df.empty:
        return {"dhl": 0.0, "fedex": 0.0, "fedex_e": 0.0, "ups": 0.0, "_debug": "DB 비어있음"}

    # 컬럼명 정규화 맵 (공백·언더바 제거, 대문자)
    col_map = {}
    for c in df.columns:
        key = c.strip().upper().replace(" ", "").replace("_", "")
        col_map[key] = c

    def _gcol(target: str) -> str:
        """컬럼명 정규화 매칭 — DHL/UPS/FedEx 혼용 방지"""
        key = target.upper().replace(" ", "").replace("_", "").replace(".", "")
        # 1) 완전 일치
        if key in col_map:
            return col_map[key]
        # 2) 운송사 + 방향(IN/OUT) 모두 포함하는 컬럼만 매칭
        #    예: "UPSOUT" 검색 시 "UPS"는 무시하고 "UPSOUT"만 매칭
        carrier_key = key[:3]          # "DHL", "UPS", "FED"
        direction   = key[-3:]         # "OUT", "_IN" → "IN " 등
        for k, v in col_map.items():
            if k.startswith(carrier_key) and key in k:
                return v
        # 3) 포함 관계 (느슨한 fallback — 최후 수단)
        for k, v in col_map.items():
            if key in k:
                return v
        return target  # 최종 fallback

    # 고객명 매칭 (공백 차이 허용)
    row = df[df["회사명"].str.strip() == company.strip()]
    if row.empty:
        row = df[df["회사명"].str.replace(" ", "", regex=False) == company.replace(" ", "")]
    if row.empty:
        avail = df["회사명"].tolist()[:15]
        return {"dhl": 0.0, "fedex": 0.0, "fedex_e": 0.0, "ups": 0.0,
                "_debug": f"'{company}' 없음. 시트 고객: {avail}"}

    r = row.iloc[0]
    suffix = "IN" if mode == "수입" else "OUT"

    dhl_col   = _gcol(f"DHL {suffix}")
    fedex_col = _gcol(f"FedEx {suffix}")
    ups_col   = _gcol(f"UPS {suffix}")

    result = {
        "dhl":     float(r.get(dhl_col,   0) or 0),
        "fedex":   float(r.get(fedex_col, 0) or 0),
        "fedex_e": float(r.get(fedex_col, 0) or 0),
        "ups":     float(r.get(ups_col,   0) or 0),
        "_debug":  f"FOUND | {mode} | DHL_col='{dhl_col}':{r.get(dhl_col,'?')} | FX_col='{fedex_col}':{r.get(fedex_col,'?')} | UPS_col='{ups_col}':{r.get(ups_col,'?')}",
        "_cols":   list(df.columns),
        "_row":    {c: str(r[c]) for c in df.columns},
        "_ups_col": ups_col,
    }
    return result
