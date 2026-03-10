"""
GitHub Actions 전용 유류할증료 스크래퍼
GitHub 서버에서 실행 → Render 방화벽 우회
FedEx / UPS / DHL 긁어서 Render 앱으로 POST 전송
"""
import re, os, json, requests
from bs4 import BeautifulSoup

RENDER_APP_URL = os.environ["RENDER_APP_URL"].rstrip("/")
SECRET_KEY     = os.environ["SECRET_KEY"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}

DEFAULTS = {"dhl": 28.75, "fedex": 29.75, "ups": 29.50}


def extract_pct(text, lo=15, hi=50):
    candidates = re.findall(r'\b(\d{1,2}\.\d{2})\b', text)
    vals = sorted(set(float(c) for c in candidates if lo <= float(c) <= hi))
    return round(vals[0], 2) if vals else None


def scrape_dhl():
    try:
        r = requests.get(
            "https://mydhl.express.dhl/kr/ko/ship/surcharges.html",
            headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ")
        v = extract_pct(text)
        if v:
            print(f"[DHL] {v}%")
            return v
    except Exception as e:
        print(f"[DHL] 실패: {e}")
    return DEFAULTS["dhl"]


def scrape_fedex():
    urls = [
        "https://www.fedex.com/ko-kr/shipping/surcharges.html",
        "https://www.fedex.com/content/dam/fedex/kr-korea/services/fuel_surcharge_kr.json",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            text = r.text
            # JSON 응답이면 바로 파싱
            if text.strip().startswith(("{", "[")):
                v = extract_pct(json.dumps(json.loads(text)))
                if v:
                    print(f"[FedEx] {v}% (JSON)")
                    return v
            # HTML 파싱
            soup = BeautifulSoup(text, "html.parser")
            plain = soup.get_text(" ")
            for pat in [
                r'국제\s*특송[^%\d]{0,150}(\d{2}\.\d{2})',
                r'International\s*Express[^%\d]{0,150}(\d{2}\.\d{2})',
                r'Fuel[^%\d]{0,80}(\d{2}\.\d{2})',
            ]:
                m = re.search(pat, plain, re.IGNORECASE | re.DOTALL)
                if m:
                    v = float(m.group(1))
                    if 15 <= v <= 50:
                        print(f"[FedEx] {v}%")
                        return round(v, 2)
            v = extract_pct(plain)
            if v:
                print(f"[FedEx] {v}% (fallback)")
                return v
        except Exception as e:
            print(f"[FedEx] {url} 실패: {e}")
    print(f"[FedEx] 모두 실패 → 기본값 {DEFAULTS['fedex']}%")
    return DEFAULTS["fedex"]


def scrape_ups():
    urls = [
        "https://www.ups.com/kr/ko/support/shipping-support/shipping-costs-rates/fuel-surcharges",
        "https://www.ups.com/media/ko/KR/fuel_surcharge.json",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            text = r.text
            if text.strip().startswith(("{", "[")):
                v = extract_pct(json.dumps(json.loads(text)))
                if v:
                    print(f"[UPS] {v}% (JSON)")
                    return v
            soup = BeautifulSoup(text, "html.parser")
            plain = soup.get_text(" ")
            for pat in [
                r'국제\s*특급[^%\d]{0,150}(\d{2}\.\d{2})',
                r'International\s*Air[^%\d]{0,150}(\d{2}\.\d{2})',
                r'Express[^%\d]{0,80}(\d{2}\.\d{2})',
            ]:
                m = re.search(pat, plain, re.IGNORECASE | re.DOTALL)
                if m:
                    v = float(m.group(1))
                    if 15 <= v <= 50:
                        print(f"[UPS] {v}%")
                        return round(v, 2)
            v = extract_pct(plain)
            if v:
                print(f"[UPS] {v}% (fallback)")
                return v
        except Exception as e:
            print(f"[UPS] {url} 실패: {e}")
    print(f"[UPS] 모두 실패 → 기본값 {DEFAULTS['ups']}%")
    return DEFAULTS["ups"]


if __name__ == "__main__":
    print("=== 유류할증료 스크래핑 시작 ===")
    result = {
        "dhl":   scrape_dhl(),
        "fedex": scrape_fedex(),
        "ups":   scrape_ups(),
    }
    print(f"\n결과: {result}")

    print("\n=== Render 앱으로 전송 ===")
    resp = requests.post(
        f"{RENDER_APP_URL}/api/update-fuel",
        json=result,
        headers={
            "Content-Type": "application/json",
            "X-Secret-Key": SECRET_KEY,
        },
        timeout=30,
    )
    print(f"응답: {resp.status_code} {resp.text}")
    if resp.status_code != 200:
        raise SystemExit(f"전송 실패: {resp.status_code}")
    print("✅ 완료!")
