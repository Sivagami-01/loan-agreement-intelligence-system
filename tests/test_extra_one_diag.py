from __future__ import annotations

import json
import re
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


SUMMARY_PATH = (
    ROOT
    / "data"
    / "processed"
    / "uploads"
    / "473af600944f"
    / "results"
    / "summary.json"
)

TAMIL_SUMMARY = (
    "குவிக் கேஷ் கேபிடல் பைனான்ஸ் நிறுவனம் அர்ஜுன் குமார் ராமசாமிக்கு கடன் வழங்குகிறது [p.3]. "
    "அனுமதிக்கப்பட்ட அசல் தொகை ரூ. 5,00,000 [p.3]. பெயரளவிலான வட்டி விகிதம் மாதத்திற்கு "
    "8.00% (ஆண்டுக்கு 96.00%) [p.2]. கடன் காலம் 24 மாதங்கள் [p.2]. கடன் வாங்குபவர் "
    "ரூ. 47,489 வீதம் 24 மாதாந்திர தவணைகளில் திருப்பிச் செலுத்த வேண்டும்; "
    "2026 டிசம்பர் 1 ஆம் தேதி முதல் ஒவ்வொரு மாதமும் 1 ஆம் தேதி செலுத்த வேண்டும் [p.6]. "
    "பாதுகாப்பில் 150 கிராம் தங்க நகைகள் மற்றும் பிற சொத்துக்கள் அடங்கும் [p.7]."
)


def one_contexts(text: str) -> list[str]:
    normalized = normalize_script_digits(text)
    contexts = []
    for match in re.finditer(r"(?<!\w)1(?!\w)", normalized):
        start = max(0, match.start() - 25)
        end = min(len(text), match.end() + 25)
        contexts.append(text[start:end])
    return contexts


def main() -> None:
    english = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))["result"]["short"]
    tamil = TAMIL_SUMMARY

    english_contexts = one_contexts(english)
    tamil_contexts = one_contexts(tamil)
    comparison = check_numbers(english, tamil)

    print("English standalone '1' contexts:")
    for context in english_contexts:
        print(f"  English: ...{context}...")
    print("Tamil standalone '1' contexts:")
    for context in tamil_contexts:
        print(f"  Tamil: ...{context}...")
    print(
        "Extractor count of '1': "
        f"English={extract_numeric_tokens(english).count('1')}, "
        f"Tamil={extract_numeric_tokens(tamil).count('1')}"
    )

    ordinal_match = (
        comparison["status"] == "pass"
        and not comparison["missing_in_translation"]
        and not comparison["extra_in_translation"]
        and extract_numeric_tokens(english).count("1")
        == extract_numeric_tokens(tamil).count("1")
    )
    print(
        f"{'PASS' if ordinal_match else 'FAIL'}: "
        "Tamil ordinal '1' is normalized to match English"
    )

    english_ordinal = extract_numeric_tokens("1st")
    tamil_attached_ordinal = extract_numeric_tokens("1ஆம்")
    print(f"Extractor cases: 1st={extract_numeric_tokens('1st')}")
    print(f"Extractor cases: 1 December={extract_numeric_tokens('1 December')}")
    print(f"Extractor cases: 1ஆம்={tamil_attached_ordinal}")
    print(f"Extractor cases: [p.1]={extract_numeric_tokens('[p.1]')}")
    print(
        f"{'PASS' if english_ordinal == tamil_attached_ordinal else 'FAIL'}: "
        'English "1st" and Tamil "1ஆம்" give the SAME extracted number'
    )
    print(
        "Tamil mismatch list: "
        f"missing in Tamil={comparison['missing_in_translation']}, "
        f"extra in Tamil={comparison['extra_in_translation']}"
    )


if __name__ == "__main__":
    main()
