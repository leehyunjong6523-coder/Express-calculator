"""
유류할증료 자동 조회 모듈 (2026)
DHL(월별), FedEx/UPS(주별) — JS SPA 대응, 다단계 fallback
"""
import re, json, time, datetime, urllib.request, urllib.error, ssl, logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

_cache = {}
_CACHE_TTL = {"dhl": 21600, "fedex": 7200, "ups": 7200}
_DEFAULTS  = {"dhl": 28.75, "fedex": 29.75, "ups": 29.50}


def _fetch(url, timeout=10, extra=None):
    h = dict(_HEADERS)
    if extra: h.update(extra)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as r:
        raw = r.read()
        enc = r.headers.get_content_charset("utf-8") or "utf-8"
        return raw.decode(enc, errors="replace")


def _extract_pct(html, lo=15, hi=50):
    """HTML/JSON에서 유류할증료 범위(lo~hi)의 첫 번째 숫자 반환"""
    candidates = re.findall(r'\b(\d{1,2}\.\d{2})\b', html)
    vals = sorted(set(float(c) for c in candidates if lo <= float(c) <= hi))
    return round(vals[0], 2) if vals else None


def _get_dhl():
    # 1) mydhl JSON API
    try:
        data = json.loads(_fetch(
            "https://mydhl.express.dhl/api/v1/ship/surcharges?countryCode=KR&language=ko",
            extra={"Accept":"application/json"}))
        for s in data.get("surcharges", []):
            if "fuel" in str(s.get("type","")).lower():
                v = float(s.get("rate", s.get("value", 0)))
                if 10 <= v <= 60: return round(v, 2)
    except Exception: pass

    # 2) HTML 파싱
    html = _fetch("https://mydhl.express.dhl/kr/ko/ship/surcharges.html")
    for pat in [
        r'"KR"[^}]{0,400}"export"[^}]{0,300}"fuel[^"]*"\s*:\s*([\d.]+)',
        r'fuelSurcharge["\s:]+(\d{2}\.\d{2})',
        r'연료\s*할증[^%\d]{0,60}(\d{2}\.\d{2})',
        r'Fuel[^%\d]{0,60}(\d{2}\.\d{2})',
    ]:
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            v = float(m.group(1))
            if 10 <= v <= 60: return round(v, 2)

    v = _extract_pct(html)
    if v: return v
    raise ValueError("DHL 조회 실패 — 수동 입력 필요")


def _get_fedex():
    # 1) JSON 엔드포인트 시도
    for url in [
        "https://www.fedex.com/content/dam/fedex/kr-korea/services/fuel_surcharge_kr.json",
        "https://www.fedex.com/en-us/shipping/current-rates/fuel-surcharge.html",
    ]:
        try:
            html = _fetch(url)
            if html.strip().startswith(("{","[")):
                v = _extract_pct(json.dumps(json.loads(html)))
                if v: return v
        except Exception as e:
            logger.error(f"[fedex] URL {url} 실패: {e}")

    # 2) HTML 파싱
    try:
        html = _fetch("https://www.fedex.com/ko-kr/shipping/surcharges.html")
        for pat in [
            r'국제\s*특송[^%\d]{0,100}(\d{2}\.\d{2})',
            r'International\s*Express[^%\d]{0,100}(\d{2}\.\d{2})',
            r'fuel[^%\d]{0,60}(\d{2}\.\d{2})',
        ]:
            m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
            if m:
                v = float(m.group(1))
                if 10 <= v <= 60: return round(v, 2)
        v = _extract_pct(html)
        if v: return v
    except Exception as e:
        logger.error(f"[fedex] HTML 파싱 실패: {e}")

    raise ValueError("FedEx 조회 실패 — 수동 입력 필요")


def _get_ups():
    # 1) JSON 엔드포인트 시도
    for url in [
        "https://www.ups.com/media/ko/KR/fuel_surcharge.json",
        "https://www.ups.com/media/en/KR/fuel_surcharge.json",
    ]:
        try:
            html = _fetch(url, extra={"Accept":"application/json"})
            if html.strip().startswith(("{","[")):
                v = _extract_pct(json.dumps(json.loads(html)))
                if v: return v
        except Exception: pass

    # 2) HTML 파싱
    html = _fetch("https://www.ups.com/kr/ko/support/shipping-support/shipping-costs-rates/fuel-surcharges")
    for pat in [
        r'국제\s*특급[^%\d]{0,100}(\d{2}\.\d{2})',
        r'International\s*Air[^%\d]{0,100}(\d{2}\.\d{2})',
        r'Express[^%\d]{0,60}(\d{2}\.\d{2})',
        r'fuel[^%\d]{0,60}(\d{2}\.\d{2})',
    ]:
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            v = float(m.group(1))
            if 10 <= v <= 60: return round(v, 2)

    v = _extract_pct(html)
    if v: return v
    raise ValueError("UPS 조회 실패 — 수동 입력 필요")


_FETCHERS = {"dhl": _get_dhl, "fedex": _get_fedex, "ups": _get_ups}


def get_fuel(carrier: str) -> dict:
    now = time.time()
    c = _cache.get(carrier)
    if c and (now - c["ts"]) < _CACHE_TTL[carrier]:
        return {"value": c["value"], "source": "cache", "updated": c["updated"], "error": None}
    try:
        val = _FETCHERS[carrier]()
        ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        _cache[carrier] = {"value": val, "ts": now, "updated": ts}
        return {"value": val, "source": "live", "updated": ts, "error": None}
    except Exception as e:
        logger.error(f"[fuel_scraper] {carrier} 조회 실패: {e}")
        if c:
            return {"value": c["value"], "source": "stale", "updated": c["updated"], "error": str(e)}
        return {"value": _DEFAULTS[carrier], "source": "default", "updated": "—", "error": str(e)}


def get_all_fuels() -> dict:
    return {k: get_fuel(k) for k in ("dhl", "fedex", "ups")}
