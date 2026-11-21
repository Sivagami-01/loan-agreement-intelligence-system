"""scripts/test_5b_translate.py

Stage 5b: Verification suite for translation feature and endpoint.
Tests:
  (a) Good translation returns status "ok", translated_text present, check passes;
  (b) Changed number triggers retry with explicit feedback, and if retry still fails,
      returns status "number_check_failed" with source text and failing numbers,
      leaving translated_text = "";
  (c) Calling the endpoint twice on the same document + language returns the cached
      result on the second call with live_calls = 0 (translator not invoked again);
  (d) Quota_blocked path returns status "quota_blocked" with 0 live calls;
  (e) Endpoint rejects unknown doc_id (404), unknown source (422), unknown language (422),
      missing turn_index for chat (422), out-of-range turn_index (422);
  (f) Verbatim quotes in document evidence are NOT passed to the translator;
  (g) Static check: no GEMINI_API_KEY leaks, no localStorage/sessionStorage, no advice words,
      language selector present in both SummaryTab.jsx and ChatTab.jsx;
  (h) llm_log.csv row count delta == 0.

ZERO Gemini API calls: asserts data/processed/llm_log.csv row count delta == 0.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.api import main as api_module
from app.api.main import app
from src.translate.translate_text import translate_text, SUPPORTED_LANGUAGES

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
WEB_SRC_DIR = ROOT / "web" / "src"
EXPECTED_DOC_ID = "893857f8b7e3"


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def test_a_good_translation() -> tuple[bool, str]:
    """Test (a): good translation returns status 'ok', translated_text present, check passes."""
    source = "The interest rate is 10.5% per annum for 24 months."
    hindi_trans = "ब्याज दर 24 महीनों के लिए प्रति वर्ष 10.5% है।"

    def fake_llm(prompt: str) -> str:
        return hindi_trans

    res = translate_text(source, "hi", llm_call=fake_llm)
    ok = (
        res.get("status") == "ok"
        and res.get("translated_text") == hindi_trans
        and res.get("source_text") == source
        and res.get("number_check", {}).get("status") == "pass"
        and res.get("live_calls") == 1
    )
    detail = (
        f"status={res.get('status')}, "
        f"check={res.get('number_check', {}).get('status')}, "
        f"live_calls={res.get('live_calls')}"
    )
    return ok, detail


def test_b_changed_number_retry_and_failure() -> tuple[bool, str]:
    """Test (b): changed number triggers retry with explicit feedback and returns number_check_failed."""
    source = "The interest rate is 10.5% per annum for 24 months."
    call_log: list[str] = []

    def failing_fake_llm(prompt: str) -> str:
        call_log.append(prompt)
        # Always return altered rate 11.5% instead of 10.5%
        return "ब्याज दर 24 महीनों के लिए प्रति वर्ष 11.5% है।"

    res = translate_text(source, "hi", llm_call=failing_fake_llm)

    retry_triggered = len(call_log) == 2
    has_retry_feedback = (
        len(call_log) == 2
        and "CRITICAL CORRECTION" in call_log[1]
        and "10.5" in call_log[1]
    )
    num_check = res.get("number_check", {})
    ok = (
        res.get("status") == "number_check_failed"
        and res.get("translated_text") == ""
        and res.get("source_text") == source
        and "10.5" in num_check.get("missing_in_translation", [])
        and "11.5" in num_check.get("extra_in_translation", [])
        and res.get("live_calls") == 2
        and retry_triggered
        and has_retry_feedback
    )
    detail = (
        f"status={res.get('status')}, "
        f"translated_text_blank={res.get('translated_text') == ''}, "
        f"missing={num_check.get('missing_in_translation')}, "
        f"extra={num_check.get('extra_in_translation')}, "
        f"calls={len(call_log)}, "
        f"feedback_verified={has_retry_feedback}"
    )
    return ok, detail


def test_b2_retry_success() -> tuple[bool, str]:
    """Sub-test (b2): changed number on attempt 1, corrected on retry -> status 'ok'."""
    source = "Processing fee is Rs. 500."
    calls = 0

    def correcting_llm(prompt: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            return "प्रसंस्करण शुल्क 600 रुपये है।"  # wrong number 600
        return "प्रसंस्करण शुल्क 500 रुपये है।"  # corrected to 500 on retry

    res = translate_text(source, "hi", llm_call=correcting_llm)
    ok = (
        res.get("status") == "ok"
        and res.get("translated_text") == "प्रसंस्करण शुल्क 500 रुपये है।"
        and res.get("number_check", {}).get("status") == "pass"
        and res.get("live_calls") == 2
        and calls == 2
    )
    detail = f"status={res.get('status')}, calls={calls}, live_calls={res.get('live_calls')}"
    return ok, detail


def test_c_caching() -> tuple[bool, str]:
    """Test (c): calling endpoint twice returns cached result on 2nd call with live_calls = 0."""
    client = TestClient(app)
    hook_calls = 0

    def fake_hook(text_en: str, lang: str) -> dict[str, Any]:
        nonlocal hook_calls
        hook_calls += 1
        return {
            "status": "ok",
            "lang": lang,
            "translated_text": f"अनुवाद: {text_en}",
            "source_text": text_en,
            "number_check": {"status": "pass"},
            "model_used": "fake_model",
            "live_calls": 1,
        }

    # Clean up test cache file path before and after test
    test_cache_path = (
        ROOT
        / "data"
        / "processed"
        / "uploads"
        / EXPECTED_DOC_ID
        / "results"
        / "translations"
        / "summary_0_bn.json"
    )
    if test_cache_path.is_file():
        test_cache_path.unlink()

    orig_hook = api_module._TRANSLATE_HOOK
    try:
        api_module._TRANSLATE_HOOK = fake_hook

        # First call: executes fake translator hook and creates cache file
        r1 = client.post(
            f"/api/documents/{EXPECTED_DOC_ID}/translate",
            json={"source": "summary", "language": "bn"},
        )
        data1 = r1.json()

        # Second call: reads from cache, hook should not be called again, live_calls == 0
        r2 = client.post(
            f"/api/documents/{EXPECTED_DOC_ID}/translate",
            json={"source": "summary", "language": "bn"},
        )
        data2 = r2.json()

        ok = (
            r1.status_code == 200
            and r2.status_code == 200
            and data1.get("status") == "ok"
            and data2.get("status") == "ok"
            and data2.get("live_calls") == 0
            and hook_calls == 1
            and test_cache_path.is_file()
        )
        detail = (
            f"code1={r1.status_code}, code2={r2.status_code}, "
            f"hook_calls={hook_calls}, live_calls_2={data2.get('live_calls')}, "
            f"cache_file_exists={test_cache_path.is_file()}"
        )
        return ok, detail
    finally:
        api_module._TRANSLATE_HOOK = orig_hook
        if test_cache_path.is_file():
            test_cache_path.unlink()


def test_d_quota_blocked() -> tuple[bool, str]:
    """Test (d): quota_blocked path returns status 'quota_blocked' with 0 live calls."""
    with patch("app.api.task_service.count_today_live_calls", return_value=999):
        res = translate_text("Sample text to translate", "hi")
        ok = (
            res.get("status") == "quota_blocked"
            and res.get("live_calls") == 0
            and res.get("translated_text") == ""
        )
        detail = f"status={res.get('status')}, live_calls={res.get('live_calls')}"
        return ok, detail


def test_e_input_validation() -> tuple[bool, str]:
    """Test (e): endpoint rejects invalid inputs (404, 422)."""
    client = TestClient(app)

    # 1. Unknown doc_id (valid 12-hex format, but document does not exist) -> 404
    r_doc = client.post(
        "/api/documents/000000000000/translate",
        json={"source": "summary", "language": "hi"},
    )

    # 2. Unknown source -> 422
    r_src = client.post(
        f"/api/documents/{EXPECTED_DOC_ID}/translate",
        json={"source": "unsupported_source", "language": "hi"},
    )

    # 3. Unknown language -> 422
    r_lang = client.post(
        f"/api/documents/{EXPECTED_DOC_ID}/translate",
        json={"source": "summary", "language": "fr"},
    )

    # 4. Missing turn_index for chat -> 422
    r_turn_missing = client.post(
        f"/api/documents/{EXPECTED_DOC_ID}/translate",
        json={"source": "chat", "language": "hi"},
    )

    # 5. Out-of-range turn_index -> 422
    r_turn_oor = client.post(
        f"/api/documents/{EXPECTED_DOC_ID}/translate",
        json={"source": "chat", "turn_index": 99999, "language": "hi"},
    )

    ok = (
        r_doc.status_code == 404
        and r_src.status_code == 422
        and r_lang.status_code == 422
        and r_turn_missing.status_code == 422
        and r_turn_oor.status_code == 422
    )
    detail = (
        f"unknown_doc={r_doc.status_code}, "
        f"unknown_src={r_src.status_code}, "
        f"unknown_lang={r_lang.status_code}, "
        f"missing_turn={r_turn_missing.status_code}, "
        f"oor_turn={r_turn_oor.status_code}"
    )
    return ok, detail


def test_f_evidence_quotes_not_passed() -> tuple[bool, str]:
    """Test (f): verbatim quotes in document evidence are NOT passed to the translator."""
    client = TestClient(app)
    received_texts: list[str] = []

    def inspect_hook(text_en: str, lang: str) -> dict[str, Any]:
        received_texts.append(text_en)
        return {
            "status": "ok",
            "lang": lang,
            "translated_text": "अनुवादित उत्तर।",
            "source_text": text_en,
            "number_check": {"status": "pass"},
            "model_used": "fake_model",
            "live_calls": 0,
        }

    chat_file = (
        ROOT
        / "data"
        / "processed"
        / "uploads"
        / EXPECTED_DOC_ID
        / "results"
        / "chat.json"
    )
    if not chat_file.is_file():
        return False, f"chat.json missing at {chat_file}"

    chat_data = json.loads(chat_file.read_text(encoding="utf-8"))
    turns = chat_data.get("turns", [])
    if not turns:
        return False, "No turns in chat.json"

    # Find a turn with evidence quotes (e.g. turn 0)
    ev_turn_idx = None
    ev_quotes: list[str] = []
    for idx, t in enumerate(turns):
        ev = t.get("evidence", [])
        if isinstance(ev, list) and len(ev) > 0 and any(item.get("quote") for item in ev):
            ev_turn_idx = idx
            ev_quotes = [str(item.get("quote", "")).strip() for item in ev if item.get("quote")]
            break

    if ev_turn_idx is None or not ev_quotes:
        return False, "Could not find a turn with verified evidence quotes in chat.json"

    # Temporary cache file path for this test
    test_cache = (
        ROOT
        / "data"
        / "processed"
        / "uploads"
        / EXPECTED_DOC_ID
        / "results"
        / "translations"
        / f"chat_{ev_turn_idx}_pa.json"
    )
    if test_cache.is_file():
        test_cache.unlink()

    orig_hook = api_module._TRANSLATE_HOOK
    try:
        api_module._TRANSLATE_HOOK = inspect_hook
        res = client.post(
            f"/api/documents/{EXPECTED_DOC_ID}/translate",
            json={"source": "chat", "turn_index": ev_turn_idx, "language": "pa"},
        )
        if res.status_code != 200:
            return False, f"HTTP error {res.status_code}: {res.text}"

        if not received_texts:
            return False, "Hook was not called"

        sent_text = received_texts[0]
        # Assert that the full verbatim quote was NOT concatenated or passed to the translator
        quote_leaks = [q for q in ev_quotes if len(q) > 20 and q in sent_text]

        turn_answer = str(turns[ev_turn_idx].get("answer", "")).strip()
        matches_answer = sent_text == turn_answer

        ok = (len(quote_leaks) == 0) and matches_answer
        detail = (
            f"turn_idx={ev_turn_idx}, sent_length={len(sent_text)}, "
            f"matches_clean_answer={matches_answer}, leaked_quotes={len(quote_leaks)}"
        )
        return ok, detail
    finally:
        api_module._TRANSLATE_HOOK = orig_hook
        if test_cache.is_file():
            test_cache.unlink()


def test_g_static_scans() -> tuple[bool, str]:
    """Test (g): static check: no keys, no localStorage, no advice words, language selector present."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    key_bytes = api_key.encode("utf-8") if api_key and len(api_key) > 5 else None

    storage_re = re.compile(r"\b(localStorage|sessionStorage)\b")
    advice_re = re.compile(r"\b(you should|we recommend|what to ask the lender)\b", re.IGNORECASE)

    key_leaks: list[str] = []
    storage_hits: list[str] = []
    advice_hits: list[str] = []

    files_to_scan = [
        ROOT / "src" / "translate" / "number_check.py",
        ROOT / "src" / "translate" / "translate_text.py",
        ROOT / "web" / "src" / "SummaryTab.jsx",
        ROOT / "web" / "src" / "ChatTab.jsx",
        ROOT / "web" / "src" / "index.css",
    ]

    for fpath in files_to_scan:
        if not fpath.is_file():
            continue
        raw = fpath.read_bytes()
        if key_bytes and key_bytes in raw:
            key_leaks.append(fpath.name)
        text = raw.decode("utf-8", errors="ignore")
        if storage_re.search(text):
            storage_hits.append(fpath.name)
        if advice_re.search(text):
            advice_hits.append(f"{fpath.name}:{advice_re.search(text).group(0)}")

    sum_jsx = (ROOT / "web" / "src" / "SummaryTab.jsx").read_text(encoding="utf-8")
    chat_jsx = (ROOT / "web" / "src" / "ChatTab.jsx").read_text(encoding="utf-8")

    expected_langs = ["en", "hi", "ta", "bn", "pa", "ml"]
    sum_has_all_langs = all(f'value="{lang}"' in sum_jsx for lang in expected_langs)
    chat_has_all_langs = all(f'value="{lang}"' in chat_jsx for lang in expected_langs)

    # ChatTab must have exact refusal text and no consult
    consult_re = re.compile(r"\bconsult\b", re.IGNORECASE)
    chat_has_consult = bool(consult_re.search(chat_jsx))

    ok = (
        len(key_leaks) == 0
        and len(storage_hits) == 0
        and len(advice_hits) == 0
        and sum_has_all_langs
        and chat_has_all_langs
        and not chat_has_consult
    )
    detail = (
        f"key_leaks={len(key_leaks)}, storage_hits={len(storage_hits)}, "
        f"advice_hits={len(advice_hits)}, sum_langs={sum_has_all_langs}, "
        f"chat_langs={chat_has_all_langs}, chat_consult={chat_has_consult}"
    )
    return ok, detail


def main() -> int:
    print("=" * 80)
    print("STAGE 5b: TRANSLATION FEATURE & ENDPOINT VERIFICATION SUITE")
    print("=" * 80)
    print("[NOTICE] All fake translations in this test suite are synthetic / builder-written")
    print("(optimistic evaluation) to prove logic, retry-loop, quote-protection, error codes,")
    print("and cache handling offline. This test does NOT prove that Gemini's real Indic output")
    print("is grammatically natural or legally accurate.\n")

    rows_before = _count_llm_log_rows()

    tests = [
        ("T1 (a)", "Good translation status 'ok', check pass", test_a_good_translation),
        ("T2 (b)", "Changed number triggers retry and reports number_check_failed", test_b_changed_number_retry_and_failure),
        ("T3 (b2)", "Changed number corrected on retry succeeds with status 'ok'", test_b2_retry_success),
        ("T4 (c)", "Endpoint caching returns live_calls=0 without invoking translator", test_c_caching),
        ("T5 (d)", "Quota blocked returns status 'quota_blocked' with 0 live calls", test_d_quota_blocked),
        ("T6 (e)", "Input validation: 404 unknown doc, 422 source/lang/turn_index", test_e_input_validation),
        ("T7 (f)", "Evidence quotes strictly excluded from text passed to translator", test_f_evidence_quotes_not_passed),
        ("T8 (g)", "Static scan: no key leaks, no storage, no advice, language selectors verified", test_g_static_scans),
    ]

    all_pass = True
    for tid, name, fn in tests:
        try:
            ok, detail = fn()
            status_str = "PASS" if ok else "FAIL"
            if not ok:
                all_pass = False
            print(f"[{status_str}] {tid}: {name}")
            print(f"       Details: {detail}\n")
        except Exception as exc:
            all_pass = False
            print(f"[FAIL] {tid}: {name}")
            print(f"       Exception: {exc}\n")

    rows_after = _count_llm_log_rows()
    delta = rows_after - rows_before

    print("-" * 80)
    print(f"llm_log.csv rows: {rows_before} -> {rows_after} (delta = {delta})")
    zero_calls_pass = delta == 0

    if not zero_calls_pass:
        print(f"[FAIL] Zero Gemini calls assertion failed: delta={delta} != 0")
        all_pass = False
    else:
        print("[PASS] Zero Gemini API calls assertion passed: delta == 0")

    print("=" * 80)
    if all_pass:
        print("STAGE 5b LOGIC TESTS PASSED (fake translations, no quality target measured)")
        return 0
    else:
        print("STAGE 5b TARGET MISSED: One or more tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
