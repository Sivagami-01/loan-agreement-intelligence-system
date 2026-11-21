from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.translate.number_check import (
    check_numbers,
    extract_numeric_tokens,
    normalize_script_digits,
)


UPLOAD_DIR = ROOT / "data" / "processed" / "uploads" / "473af600944f"
SUMMARY_PATH = UPLOAD_DIR / "results" / "summary.json"
HINDI_PATH = UPLOAD_DIR / "results" / "translations" / "summary_0_hi.json"

TAMIL_SUMMARY = (
    "குவிக் கேஷ் கேபிடல் பைனான்ஸ் நிறுவனம் அர்ஜுன் குமார் ராமசாமிக்கு கடன் வழங்குகிறது [p.3]. "
    "அனுமதிக்கப்பட்ட அசல் தொகை ரூ. 5,00,000 [p.3]. பெயரளவிலான வட்டி விகிதம் மாதத்திற்கு "
    "8.00% (ஆண்டுக்கு 96.00%) [p.2]. கடன் காலம் 24 மாதங்கள் [p.2]. கடன் வாங்குபவர் "
    "ரூ. 47,489 வீதம் 24 மாதாந்திர தவணைகளில் திருப்பிச் செலுத்த வேண்டும்; "
    "2026 டிசம்பர் 1 ஆம் தேதி முதல் ஒவ்வொரு மாதமும் 1 ஆம் தேதி செலுத்த வேண்டும் [p.6]. "
    "பாதுகாப்பில் 150 கிராம் தங்க நகைகள் மற்றும் பிற சொத்துக்கள் அடங்கும் [p.7]."
)


def _print_result(label: str, passed: bool) -> None:
    print(f"{'PASS' if passed else 'FAIL'}: {label}")


def main() -> None:
    english = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))["result"]["short"]
    hindi = json.loads(HINDI_PATH.read_text(encoding="utf-8"))["translated_text"]
    tamil = TAMIL_SUMMARY

    _print_result(
        '"1st" extracts [\'1\']',
        extract_numeric_tokens("1st") == ["1"],
    )
    _print_result(
        '"1 ஆம்" (with space) extracts [\'1\']',
        extract_numeric_tokens("1 ஆம்") == ["1"],
    )
    _print_result(
        '"1ஆம்" (no space) extracts [\'1\']',
        extract_numeric_tokens("1ஆம்") == ["1"],
    )

    tamil_digits = normalize_script_digits("௫,௦௦,௦௦௦")
    _print_result(
        "Tamil digits ௫,௦௦,௦௦௦ normalize to 5,00,000",
        tamil_digits == "5,00,000"
        and extract_numeric_tokens(tamil_digits) == ["500000"],
    )

    tamil_check = check_numbers(english, tamil)
    _print_result(
        "sample agreement Tamil summary matches English (missing=[], extra=[])",
        tamil_check["status"] == "pass"
        and tamil_check["missing_in_translation"] == []
        and tamil_check["extra_in_translation"] == [],
    )

    hindi_check = check_numbers(english, hindi)
    _print_result(
        "sample agreement Hindi summary still matches English (no regression)",
        hindi_check["status"] == "pass"
        and hindi_check["missing_in_translation"] == []
        and hindi_check["extra_in_translation"] == [],
    )

    wrong_amount = tamil.replace("5,00,000", "6,00,000")
    wrong_amount_check = check_numbers(english, wrong_amount)
    _print_result(
        "SAFETY: Tamil text with a WRONG amount (5,00,000 changed to 6,00,000) is REJECTED",
        wrong_amount_check["status"] == "fail"
        and "500000" in wrong_amount_check["missing_in_translation"]
        and "600000" in wrong_amount_check["extra_in_translation"],
    )

    missing_24 = tamil.replace("24", "")
    missing_check = check_numbers(english, missing_24)
    _print_result(
        "SAFETY: Tamil text with a MISSING number (24 removed) is REJECTED",
        missing_check["status"] == "fail"
        and "24" in missing_check["missing_in_translation"],
    )

    extra_7 = tamil + " 7"
    extra_check = check_numbers(english, extra_7)
    _print_result(
        "SAFETY: Tamil text with an EXTRA number (a new 7 added) is REJECTED",
        extra_check["status"] == "fail"
        and "7" in extra_check["extra_in_translation"],
    )


if __name__ == "__main__":
    main()
