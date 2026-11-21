from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.translate.number_check import check_numbers


ENGLISH_SUMMARY = (
    "QuickCash Capital Finance Private Limited lends to Mr. Arjun Kumar Ramasamy [p.3]. "
    "The principal amount sanctioned is Rs. 5,00,000 [p.3]. "
    "The nominal interest rate is 8.00% per month (96.00% per annum), compounded daily "
    "on reducing and non-reducing balances at the Lender's option [p.2]. "
    "The loan tenure is 24 months (Lender may recall on demand at any time) [p.2]. "
    "The borrower shall repay the loan in 24 monthly instalments of Rs. 47,489 "
    "(approximately) each, payable on the 1st day of every month commencing "
    "1 December 2026 [p.6]. Security includes residential property title deeds, "
    "motor vehicle RC/keys/transfer form, 150 grams gold ornaments, all present and "
    "future bank accounts, salary/receivables, post-dated cheques, and blank signed "
    "promissory notes [p.7]."
)

HINDI_SUMMARY = (
    "क्विककैश कैपिटल फाइनेंस प्राइवेट लिमिटेड श्री अर्जुन कुमार रामासामी को ऋण देता है [p.3]। "
    "स्वीकृत मूलधन राशि 5,00,000 रुपये है [p.3]। नाममात्र ब्याज दर 8.00% प्रति माह "
    "(96.00% प्रति वर्ष) है [p.2]। ऋण की अवधि 24 महीने है [p.2]। उधारकर्ता "
    "47,489 रुपये की 24 मासिक किस्तों में ऋण चुकाएगा, जो 1 दिसंबर 2026 से शुरू होती हैं "
    "और प्रत्येक महीने के 1st दिन देय हैं [p.6]। प्रतिभूति में 150 ग्राम सोने के आभूषण "
    "और अन्य संपत्तियां शामिल हैं [p.7]।"
)

# Tamil expresses the English ordinal "1st" as a separate numeral and suffix.
TAMIL_SUMMARY = (
    "குவிக் கேஷ் கேபிடல் பைனான்ஸ் நிறுவனம் அர்ஜுன் குமார் ராமசாமிக்கு கடன் வழங்குகிறது [p.3]. "
    "அனுமதிக்கப்பட்ட அசல் தொகை ரூ. 5,00,000 [p.3]. பெயரளவிலான வட்டி விகிதம் மாதத்திற்கு "
    "8.00% (ஆண்டுக்கு 96.00%) [p.2]. கடன் காலம் 24 மாதங்கள் [p.2]. கடன் வாங்குபவர் "
    "ரூ. 47,489 வீதம் 24 மாதாந்திர தவணைகளில் திருப்பிச் செலுத்த வேண்டும்; "
    "2026 டிசம்பர் 1 ஆம் தேதி முதல் ஒவ்வொரு மாதமும் 1 ஆம் தேதி செலுத்த வேண்டும் [p.6]. "
    "பாதுகாப்பில் 150 கிராம் தங்க நகைகள் மற்றும் பிற சொத்துக்கள் அடங்கும் [p.7]."
)


def main() -> None:
    hindi = check_numbers(ENGLISH_SUMMARY, HINDI_SUMMARY)
    tamil = check_numbers(ENGLISH_SUMMARY, TAMIL_SUMMARY)

    print(f"{'PASS' if hindi['status'] == 'pass' else 'FAIL'}: Hindi numbers match English")
    print(f"{'PASS' if tamil['status'] == 'pass' else 'FAIL'}: Tamil numbers match English")
    print(
        "Tamil mismatch list: "
        f"missing in Tamil={tamil['missing_in_translation']}, "
        f"extra in Tamil={tamil['extra_in_translation']}"
    )


if __name__ == "__main__":
    main()
