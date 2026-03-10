"""에어브리지 국제특송 운임계산기 — Flask 앱"""
import os
import io
import json
import base64

# .env 파일 자동 로드 (로컬 테스트 시 API 키 설정)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session

from calculator import run_calculation, get_countries, COUNTRY_KR
from fuel_scraper import get_all_fuels, get_fuel
from google_sheets import load_customer_db, get_customer_list, get_customer_disc, clear_cache
import ai_ocr

# ── PDF 생성 (선택적) ──
try:
    from pdf_gen import generate_pdf
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "airbridge-secret-2026")

# ──────────────────────────────────────────
# 기본값
# ──────────────────────────────────────────
DEFAULTS = {
    "mode":        "수출",
    "fuel_dhl":    28.75,
    "fuel_fedex":  29.75,
    "fuel_ups":    29.50,
    "disc_dhl":    50.0,
    "disc_fedex":   0.0,
    "disc_fedex_e": 0.0,
    "disc_ups":     0.0,
    "disc_ups_b8":  0.0,
    "tgt_margin":  30.0,
    "our_contact":  "",
    "our_phone":   "032-502-1880",
}

STAFF = {
    "호영준": {"phone": "010-3767-5413", "email": "cs@airos.co.kr"},
    "양희석": {"phone": "010-4594-0768", "email": "cs@airos.co.kr"},
    "이현종": {"phone": "010-4767-3264", "email": "cs@airos.co.kr"},
}

# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────
def _get_settings() -> dict:
    s = dict(DEFAULTS)
    s.update({k: session.get(k, v) for k, v in DEFAULTS.items()})
    # fuel_cache.json에서 저장된 유류할증료 읽기
    try:
        from fuel_scraper import _load_file_cache, _cache
        _load_file_cache()
        for carrier, key in (("dhl","fuel_dhl"),("fedex","fuel_fedex"),("ups","fuel_ups")):
            if carrier in _cache and _cache[carrier].get("value") is not None:
                s[key] = _cache[carrier]["value"]
    except Exception:
        pass
    return s

def _fmt(n: float) -> str:
    return f"₩{int(n):,}"

# ──────────────────────────────────────────
# 라우트
# ──────────────────────────────────────────
@app.route("/")
def index():
    countries = get_countries()
    customer_list = get_customer_list()
    settings = _get_settings()
    quote_num = f"AB-{datetime.now().strftime('%Y%m%d')}-001"
    return render_template(
        "index.html",
        countries=countries,
        customer_list=customer_list,
        settings=settings,
        staff=STAFF,
        quote_num=quote_num,
        pdf_available=PDF_AVAILABLE,
    )


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    d = request.json or {}

    dest_country  = d.get("dest_country", "Germany")
    mode          = d.get("mode", "수출")
    is_doc        = bool(d.get("is_doc", False))
    ct_data       = d.get("ct_data", [{"wt": 1.0, "L": 10, "W": 10, "H": 10, "qty": 1}])
    fuel_dhl      = float(d.get("fuel_dhl",    28.75))
    fuel_fedex    = float(d.get("fuel_fedex",  29.75))
    fuel_ups      = float(d.get("fuel_ups",    29.50))
    disc_dhl      = float(d.get("disc_dhl",    50.0))
    disc_fedex    = float(d.get("disc_fedex",   0.0))
    disc_fedex_e  = float(d.get("disc_fedex_e", 0.0))
    disc_ups      = float(d.get("disc_ups",     0.0))
    disc_ups_b8   = float(d.get("disc_ups_b8",  0.0))
    remote_postal = str(d.get("remote_postal", ""))
    remote_city   = str(d.get("remote_city",   ""))
    customer      = str(d.get("customer",      ""))

    # C/T 데이터 정규화
    ct_norm = []
    for ct in ct_data:
        ct_norm.append({
            "wt":  max(0.1, float(ct.get("wt", 1.0))),
            "L":   max(1,   int(ct.get("L",  10))),
            "W":   max(1,   int(ct.get("W",  10))),
            "H":   max(1,   int(ct.get("H",  10))),
            "qty": max(1,   int(ct.get("qty", 1))),
        })

    try:
        result = run_calculation(
            dest_country=dest_country,
            mode=mode,
            is_doc=is_doc,
            ct_data=ct_norm,
            fuel_dhl=fuel_dhl,
            fuel_fedex=fuel_fedex,
            fuel_ups=fuel_ups,
            disc_dhl=disc_dhl,
            disc_fedex=disc_fedex,
            disc_fedex_e=disc_fedex_e,
            disc_ups=disc_ups,
            disc_ups_b8=disc_ups_b8,
            remote_postal=remote_postal,
            remote_city=remote_city,
            customer=customer,
        )
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/customer-disc", methods=["POST"])
def api_customer_disc():
    d = request.json or {}
    company = d.get("company", "")
    mode    = d.get("mode", "수출")
    if not company:
        return jsonify({"ok": False, "error": "회사명 없음"})
    disc = get_customer_disc(company, mode)
    debug = disc.pop("_debug", "")
    disc.pop("_ups_col", None)
    return jsonify({"ok": True, "disc": disc, "debug": debug})


@app.route("/api/debug-customer", methods=["GET"])
def api_debug_customer():
    company = request.args.get("company", "")
    mode    = request.args.get("mode", "수출")
    try:
        df = load_customer_db()
        cols  = list(df.columns) if not df.empty else []
        names = df["회사명"].tolist() if not df.empty else []
        disc  = get_customer_disc(company, mode) if company else {}
        debug = disc.pop("_debug", "")
        row   = disc.pop("_row", {})
        ups_col = disc.pop("_ups_col", "")
        disc.pop("_cols", [])
        return jsonify({
            "columns": cols,
            "customers_first20": names[:20],
            "disc": disc,
            "debug": debug,
            "raw_row": row,
            "ups_col_used": ups_col,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/fuel", methods=["GET"])
def api_fuel():
    """유류할증료 자동 조회 — ?carrier=dhl|fedex|ups|all"""
    carrier = request.args.get("carrier", "all")
    try:
        if carrier == "all":
            return jsonify(get_all_fuels())
        else:
            return jsonify({carrier: get_fuel(carrier)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/save-fuel", methods=["POST"])
def api_save_fuel():
    """앱 화면에서 수동 입력한 유류할증료 저장"""
    data = request.get_json(force=True)
    from fuel_scraper import set_fuel_from_api
    for carrier, key in (("dhl","dhl"),("fedex","fedex"),("ups","ups")):
        val = data.get(key)
        if val is not None:
            try:
                set_fuel_from_api(carrier, float(val))
            except Exception:
                pass
    return jsonify({"ok": True})


@app.route("/api/update-fuel", methods=["POST"])
def api_update_fuel():
    """GitHub Actions에서 유류할증료 푸시 — SECRET_KEY 인증"""
    import os
    secret = request.headers.get("X-Secret-Key", "")
    if secret != os.environ.get("SECRET_KEY", ""):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    updated = []
    from fuel_scraper import set_fuel_from_api
    for carrier in ("dhl", "fedex", "ups"):
        val = data.get(carrier)
        if val is not None:
            try:
                set_fuel_from_api(carrier, float(val))
                updated.append(f"{carrier}={val}")
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "updated": updated})


@app.route("/api/reload-customers", methods=["POST"])
def api_reload_customers():
    """구글시트 캐시 강제 초기화 — 새 고객 추가 후 사용"""
    clear_cache()
    try:
        df = load_customer_db()
        names = df["회사명"].tolist() if not df.empty else []
        return jsonify({"ok": True, "count": len(names), "customers": names[:30]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
def api_customers():
    try:
        customers = get_customer_list()
        return jsonify({"ok": True, "customers": customers})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/ai-ocr", methods=["POST"])
def api_ai_ocr():
    mode = request.form.get("mode", "image")
    if mode == "text":
        text = request.form.get("text", "")
        result = ai_ocr.call_claude_text(text)
    else:
        file = request.files.get("file")
        if not file:
            return jsonify({"ok": False, "error": "파일 없음"})
        img_bytes = file.read()
        mime = file.content_type or "image/jpeg"
        result = ai_ocr.call_claude_image(img_bytes, mime)

    if "error" in result:
        return jsonify({"ok": False, "error": result["error"]})
    return jsonify({"ok": True, "data": result})


@app.route("/api/pdf", methods=["POST"])
def api_pdf():
    if not PDF_AVAILABLE:
        return jsonify({"ok": False, "error": "PDF 생성 불가"}), 400
    d = request.json or {}
    # PDF 생성 로직 (generate_pdf 호출)
    try:
        pdf_bytes = generate_pdf(**d)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"airbridge_quote_{d.get('quote_num','')}.pdf"
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def api_settings():
    d = request.json or {}
    for k in DEFAULTS:
        if k in d:
            session[k] = d[k]
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"\n  ✈ 에어브리지 운임계산기 시작")
    print(f"  → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
